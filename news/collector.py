"""
财经资讯聚合模块
数据来源: AKShare (财联社、华尔街见闻、东方财富)
支持: 新闻快讯、公告摘要、研报摘要、舆情分析
"""

import os
import sys
import re
import time
import random
import sqlite3
import warnings
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
import pandas as pd

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 数据模型 ─────────────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    """单条资讯"""
    id: str
    title: str
    content: str
    source: str          # cls / wallstreetcn / eastmoney / sina
    category: str        # market / industry / stock / macro / announcement
    ts_code: Optional[str]  # 关联股票代码 (如有)
    publish_time: str
    sentiment: float    # -1 到 1, 负=利空, 正=利好
    sentiment_label: str #利好 / 利空 / 中性
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class NewsDatabase:
    """SQLite 本地资讯库"""

    def __init__(self, db_path: str = "./data/news.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                source TEXT,
                category TEXT,
                ts_code TEXT,
                publish_time TEXT,
                sentiment REAL,
                sentiment_label TEXT,
                url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_time ON news(publish_time DESC)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_code ON news(ts_code)
        """)
        self.conn.commit()

    def insert(self, item: NewsItem):
        self.conn.execute(
            "INSERT OR REPLACE INTO news VALUES (?,?,?,?,?,?,?,?,?,?)",
            (item.id, item.title, item.content, item.source, item.category,
             item.ts_code, item.publish_time, item.sentiment, item.sentiment_label, item.url)
        )
        self.conn.commit()

    def insert_batch(self, items: list[NewsItem]):
        data = [(i.id, i.title, i.content, i.source, i.category,
                 i.ts_code, i.publish_time, i.sentiment, i.sentiment_label, i.url)
                for i in items]
        self.conn.executemany(
            "INSERT OR REPLACE INTO news VALUES (?,?,?,?,?,?,?,?,?,?)", data
        )
        self.conn.commit()

    def query(
        self,
        ts_code: Optional[str] = None,
        category: Optional[str] = None,
        days: int = 7,
        limit: int = 50,
    ) -> list[dict]:
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        sql = "SELECT * FROM news WHERE publish_time >= ?"
        params: list = [since]

        if ts_code:
            sql += " AND ts_code = ?"
            params.append(ts_code)
        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY publish_time DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        cols = [d[0] for d in self.conn.execute("PRAGMA table_info(news)").fetchall()]
        return [dict(zip(cols, r)) for r in rows]

    def get_market_summary(self, days: int = 1) -> dict:
        """获取近期舆情统计"""
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        row = self.conn.execute(
            "SELECT COUNT(*), AVG(sentiment), "
            "SUM(CASE WHEN sentiment > 0.2 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN sentiment < -0.2 THEN 1 ELSE 0 END) "
            "FROM news WHERE publish_time >= ?",
            (since,)
        ).fetchone()
        return {
            "total_news": row[0] or 0,
            "avg_sentiment": round(row[1] or 0, 3),
            "positive_count": row[2] or 0,
            "negative_count": row[3] or 0,
            "bullish_ratio": round(row[2] / max(row[0], 1) * 100, 1),
        }

    def close(self):
        self.conn.close()


# ── 资讯采集器 ────────────────────────────────────────────────────────────────

class NewsCollector:
    """
    多源财经资讯采集
    数据源优先级: AKShare > 新浪财经 > 腾讯财经
    """

    def __init__(self, db: Optional[NewsDatabase] = None):
        self.db = db or NewsDatabase()

    def _safe_request(self, func, *args, retries: int = 3, **kwargs):
        """带重试的安全 HTTP 请求"""
        import requests
        for i in range(retries):
            try:
                time.sleep(random.uniform(0.5, 1.5))
                return func(*args, **kwargs)
            except Exception:
                if i == retries - 1:
                    return None

    def collect_all(self, force: bool = False) -> int:
        """采集所有来源，返回新增条目数"""
        total = 0
        for source_fn in [
            self._collect_akshare_news,
            self._collect_sina_news,
            self._collect_eastmoney_news,
        ]:
            try:
                count = source_fn()
                total += count
                print(f"[{source_fn.__name__}] 采集 {count} 条")
            except Exception as e:
                print(f"[{source_fn.__name__}] 失败: {e}")
        return total

    def _collect_akshare_news(self) -> int:
        """AKShare 财经新闻 (最全)"""
        import akshare as ak

        os.environ['NO_PROXY'] = '*'
        items: list[NewsItem] = []

        # 快讯
        try:
            df = ak.stock_telegraph_cls()
            for _, row in df.iterrows():
                title = str(row.get('标题', ''))
                content = str(row.get('内容', ''))
                pub_time = str(row.get('发布时间', datetime.now().strftime('%Y-%m-%d %H:%M')))
                sentiment = self._analyze_sentiment(title + content)
                items.append(NewsItem(
                    id=f"cls_{hash(title)}",
                    title=title[:200],
                    content=content[:500],
                    source="cls",
                    category=self._categorize(title + content),
                    ts_code=self._extract_stock_code(title + content),
                    publish_time=pub_time,
                    sentiment=sentiment,
                    sentiment_label=self._sentiment_label(sentiment),
                ))
        except Exception as e:
            print(f"[AKShare 快讯] 失败: {e}")

        # 财经要闻
        try:
            df2 = ak.stock_telegraph_xpaper()
            for _, row in df2.iterrows():
                title = str(row.get('标题', ''))
                content = str(row.get('内容', ''))
                pub_time = str(row.get('发布时间', datetime.now().strftime('%Y-%m-%d %H:%M')))
                sentiment = self._analyze_sentiment(title + content)
                items.append(NewsItem(
                    id=f"xpaper_{hash(title)}",
                    title=title[:200],
                    content=content[:500],
                    source="xpaper",
                    category=self._categorize(title + content),
                    ts_code=self._extract_stock_code(title + content),
                    publish_time=pub_time,
                    sentiment=sentiment,
                    sentiment_label=self._sentiment_label(sentiment),
                ))
        except Exception as e:
            print(f"[AKShare 要闻] 失败: {e}")

        if items:
            self.db.insert_batch(items)
        return len(items)

    def _collect_sina_news(self) -> int:
        """新浪财经快讯"""
        items: list[NewsItem] = []
        try:
            url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=20&versionNumber=1.2.4&page=1"
            import requests
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            for item in data.get('result', {}).get('data', []):
                title = item.get('title', '')
                ctime = item.get('ctime', '')
                sentiment = self._analyze_sentiment(title)
                items.append(NewsItem(
                    id=f"sina_{hash(title)}",
                    title=title[:200],
                    content=title[:200],
                    source="sina",
                    category=self._categorize(title),
                    ts_code=self._extract_stock_code(title),
                    publish_time=ctime,
                    sentiment=sentiment,
                    sentiment_label=self._sentiment_label(sentiment),
                    url=item.get('url', ''),
                ))
        except Exception as e:
            print(f"[新浪快讯] 失败: {e}")

        if items:
            self.db.insert_batch(items)
        return len(items)

    def _collect_eastmoney_news(self) -> int:
        """东方财富个股资讯"""
        items: list[NewsItem] = []
        try:
            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
            params = {
                "sr": "-1", "page_size": 20, "page_index": 1,
                "ann_type": "ALL", "client_source": "web",
            }
            import requests
            r = requests.get(url, params=params, timeout=10)
            r.encoding = 'utf-8'
            data = r.json()
            for item in data.get('data', {}).get('list', []):
                title = item.get('title', '')
                pub_time = item.get('notice_date', '')[:16]
                sentiment = self._analyze_sentiment(title)
                items.append(NewsItem(
                    id=f"em_{item.get("id", hash(title))}",
                    title=title[:200],
                    content=title[:200],
                    source="eastmoney",
                    category="announcement",
                    ts_code=item.get('secu_code', ''),
                    publish_time=pub_time,
                    sentiment=sentiment,
                    sentiment_label=self._sentiment_label(sentiment),
                ))
        except Exception as e:
            print(f"[东方财富] 失败: {e}")

        if items:
            self.db.insert_batch(items)
        return len(items)

    # ── 辅助函数 ──────────────────────────────────────────────────────────────

    def _analyze_sentiment(self, text: str) -> float:
        """基于关键词的情感分析 (简化版，不依赖外部模型)"""
        text = text.lower()
        bullish = sum([
            text.count(k) for k in [
                '涨停', '大涨', '暴涨', '创新高', '突破', '增长', '超预期',
                '增持', '买入', '推荐', '看好', '业绩', '盈利', '净利',
                '增长', '景气', '布局', '低估', '拐点', '反弹', '多头',
            ]
        ])
        bearish = sum([
            text.count(k) for k in [
                '跌停', '大跌', '暴跌', '亏损', '减持', '卖出', '风险',
                '暴雷', '预警', '诉讼', '调查', '违约', '降级', '警告',
                '业绩下滑', '不及预期', '商誉', '债务', '造假', 'ST',
            ]
        ])
        total = bullish + bearish
        if total == 0:
            return 0.0
        return round((bullish - bearish) / total, 2)

    def _sentiment_label(self, s: float) -> str:
        if s > 0.2: return "利好"
        if s < -0.2: return "利空"
        return "中性"

    def _categorize(self, text: str) -> str:
        """简单分类"""
        if any(k in text for k in ['公告', '年报', '季报', '半年报', '分红', '增发']):
            return "announcement"
        if any(k in text for k in ['行业', '板块', '产业', '赛道']):
            return "industry"
        if re.search(r'\d{6}', text):
            return "stock"
        return "market"

    def _extract_stock_code(self, text: str) -> Optional[str]:
        """提取股票代码"""
        match = re.search(r'(\d{6})', text)
        if match:
            code = match.group(1)
            if code.startswith(('6', '5', '9')):
                return f"{code}.SH"
            elif code.startswith(('0', '3')):
                return f"{code}.SZ"
        return None


# ── 舆情分析 ─────────────────────────────────────────────────────────────────

class SentimentAnalyzer:
    """
    基于 SnowNLP 的中文舆情分析
    也支持关键词规则兜底 (SnowNLP 不可用时)
    """

    def __init__(self):
        self._snownlp = None
        self._try_load_snownlp()

    def _try_load_snownlp(self):
        try:
            from snownlp import SnowNLP
            self._snownlp = SnowNLP
        except ImportError:
            print("[Sentiment] SnowNLP 未安装，使用关键词规则兜底")

    def analyze(self, text: str) -> float:
        """返回 -1 到 1 的情感得分"""
        if not text:
            return 0.0

        if self._snownlp:
            try:
                s = self._snownlp(text)
                return round(s.sentiments * 2 - 1, 3)  # 转换到 [-1, 1]
            except Exception:
                pass

        # 兜底: 关键词打分
        return self._keyword_score(text)

    def _keyword_score(self, text: str) -> float:
        positive = ['涨', '增', '好', '盈', '利', '升', '高', '优', '新', '突破']
        negative = ['跌', '减', '亏', '损', '降', '低', '劣', '危', '风', '亏']
        pos = sum(min(text.count(c), 3) for c in positive)
        neg = sum(min(text.count(c), 3) for c in negative)
        total = pos + neg
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 2)

    def get_stock_sentiment(self, db: NewsDatabase, ts_code: str, days: int = 7) -> dict:
        """获取个股舆情概况"""
        news = db.query(ts_code=ts_code, days=days, limit=100)
        if not news:
            return {"sentiment": 0, "label": "中性", "news_count": 0}

        sentiments = [n['sentiment'] for n in news if n.get('sentiment') is not None]
        avg = sum(sentiments) / len(sentiments) if sentiments else 0
        return {
            "sentiment": round(avg, 3),
            "label": "利好" if avg > 0.2 else "利空" if avg < -0.2 else "中性",
            "news_count": len(news),
            "positive_count": sum(1 for s in sentiments if s > 0.2),
            "negative_count": sum(1 for s in sentiments if s < -0.2),
        }


if __name__ == "__main__":
    print("=== 财经资讯采集测试 ===")
    collector = NewsCollector()
    count = collector.collect_all()
    print(f"本次采集 {count} 条资讯")

    summary = collector.db.get_market_summary()
    print(f"舆情概况: {summary}")

    analyzer = SentimentAnalyzer()
    sent = analyzer.analyze("贵州茅台业绩大增50%，股价涨停创新高")
    print(f"情感分析: {sent} ({'利好' if sent > 0 else '利空' if sent < 0 else '中性'})")
