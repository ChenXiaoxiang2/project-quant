"""
每日自动化工作流
整合: 资讯采集 → 舆情分析 → 智能选股 → 策略信号 → 告警监控 → 报告生成
支持: 邮件推送 / 钉钉推送
"""

import os
import sys
import smtplib
import ssl
import yaml
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news.collector import NewsCollector, SentimentAnalyzer, NewsDatabase
from screener.factor_engine import StockScreener, FactorConfig
from strategies.signal_generator import SignalAggregator
from monitor.alerts import StockWatcher, AlertPusher, AlertDatabase


class DailyWorkflow:
    """
    每日量化工作流

    执行顺序:
    1. 采集财经资讯 (财联社 + 新浪 + 东方财富)
    2. 生成舆情报告
    3. 执行智能选股
    4. 生成策略信号
    5. 整合所有报告
    6. 发送邮件/钉钉推送
    """

    def __init__(self, config_path: str = "./config/settings.yaml"):
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {}

    def run(self, dry_run: bool = False):
        """执行完整工作流"""
        print("=" * 60)
        print(f"每日量化工作流 启动  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        steps = [
            ("1. 采集财经资讯", self._step_news),
            ("2. 舆情分析", self._step_sentiment),
            ("3. 智能选股", self._step_screening),
            ("4. 生成策略信号", self._step_signals),
            ("5. 整合报告", self._step_report),
            ("6. 推送通知", self._step_push),
        ]

        results = {}
        for name, fn in steps:
            print(f"\n>>> {name}...")
            try:
                results[name] = fn(dry_run=dry_run)
                print(f"    ✓ 完成")
            except Exception as e:
                print(f"    ✗ 失败: {e}")
                results[name] = {"error": str(e)}

        print("\n" + "=" * 60)
        print(f"工作流结束  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        return results

    def _step_news(self, dry_run: bool = False) -> dict:
        """采集财经资讯"""
        collector = NewsCollector()
        count = collector.collect_all()
        summary = collector.db.get_market_summary()
        return {"count": count, "summary": summary}

    def _step_sentiment(self, dry_run: bool = False) -> dict:
        """舆情分析"""
        analyzer = SentimentAnalyzer()
        news_db = NewsDatabase()
        # 分析市场整体情绪（ts_code=None 表示全市场）
        sentiment = analyzer.get_market_sentiment_summary(news_db, days=1)
        return sentiment

    def _step_screening(self, dry_run: bool = False) -> dict:
        """智能选股"""
        screener = StockScreener(FactorConfig(top_n=50))
        results = screener.screen(dry_run=dry_run)
        report = screener.generate_report(results)
        return {"count": len(results), "top5": results[:5], "report": report}

    def _step_signals(self, dry_run: bool = False) -> dict:
        """生成策略信号 (对选出的股票)"""
        from data.data_loader import StockDataLoader, BaostockDataLoader
        loader = StockDataLoader()
        baostock = BaostockDataLoader()
        agg = SignalAggregator()

        # 取沪深300成分股代表性标的作为示例
        test_codes = ["600519.SH", "000001.SZ", "600036.SH", "300750.SZ"]
        signals = []

        for code in test_codes:
            try:
                normalized = code
                hist = baostock.fetch_historical(normalized,
                    (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d'))
                if not hist.empty:
                    result = agg.get_signal(hist)
                    qt_code = ("sh" if ".SH" in code else "sz") + code.split('.')[0]
                    quote = loader._tencent.fetch_realtime([qt_code])
                    name = quote.iloc[0]['name'] if not quote.empty else code
                    signals.append({
                        "code": code,
                        "name": name,
                        "action": result['final_action'],
                        "confidence": result['confidence'],
                        "votes": result['votes'],
                    })
            except Exception:
                continue

        return {"signals": signals}

    def _step_report(self, dry_run: bool = False) -> dict:
        """整合完整日报（使用各步骤真实数据）"""
        date_str = datetime.now().strftime("%Y%m%d")
        report_path = f"./reports/daily_{date_str}.md"

        # 收集各步骤数据
        sentiment_data = self._step_sentiment(dry_run=dry_run)
        screening_data = self._step_screening(dry_run=dry_run)
        signals_data = self._step_signals(dry_run=dry_run)

        # 舆情摘要
        sent = sentiment_data
        sent_text = f"今日共采集 {sent.get('total_news', 0)} 条资讯，"
        sent_text += f"平均情绪 {sent.get('avg_sentiment', 0):.2f}，"
        sent_text += f"看多比例 {sent.get('bullish_ratio', 0)}%，"
        sent_text += f"利好 {sent.get('positive_count', 0)} 条，利空 {sent.get('negative_count', 0)} 条"

        # 选股结果
        top_stocks = screening_data.get('top5', [])
        screener_lines = []
        for s in top_stocks:
            screener_lines.append(f"- **{s.get('code', '')}** {s.get('name', '')} | "
                                  f"综合评分 {s.get('score', 0):.1f} | "
                                  f"PE {s.get('pe', 'N/A')} | "
                                  f"ROE {s.get('roe', 'N/A')}%")

        # 策略信号
        signal_lines = []
        for sig in signals_data.get('signals', []):
            action_emoji = "🟢 买入" if sig['action'] == 'BUY' else "🔴 卖出" if sig['action'] == 'SELL' else "⚪ 观望"
            signal_lines.append(f"- **{sig['name']}** ({sig['code']}) | {action_emoji} "
                                f"| 置信度 {sig['confidence']:.0%} | 投票 {sig['votes']}")

        lines = [
            f"# 每日量化报告  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "\n---\n",
            "## 一、市场舆情\n",
            f"> {sent_text}\n",
            "\n## 二、智能选股（多因子筛选 TOP 5）\n",
            "> ROE>10% · 净利润增速>10% · 资产负债率<60% · 股价站上20日均线\n",
        ]
        if screener_lines:
            lines.extend(screener_lines)
        else:
            lines.append("> 暂无满足条件的股票\n")

        lines.extend([
            "\n## 三、策略信号（多策略聚合）\n",
            "> 双均线 / 布林带 / RSI / 海龟 / MACD 投票\n",
        ])
        if signal_lines:
            lines.extend(signal_lines)
        else:
            lines.append("> 暂无策略信号\n")

        # 综合建议
        buy_signals = sum(1 for s in signals_data.get('signals', []) if s['action'] == 'BUY')
        if buy_signals >= 2 and sent.get('avg_sentiment', 0) > 0.1:
            advice = "**综合建议：谨慎买入** — 策略出现买入信号且市场情绪偏多，但需严格设置止损。"
        elif buy_signals >= 1:
            advice = "**综合建议：观望为主** — 少数策略出现信号，建议等待确认后再操作。"
        elif sent.get('avg_sentiment', 0) < -0.1:
            advice = "**综合建议：减仓回避** — 市场情绪偏空，控制风险为主。"
        else:
            advice = "**综合建议：中性** — 市场方向不明，保持现有仓位，耐心等待。"

        lines.extend([
            "\n## 四、投资建议\n",
            f"> {advice}\n",
            "\n---\n",
            f"> ⚠️ 仅供参考，不构成投资建议 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        ])

        content = '\n'.join(lines)
        os.makedirs("./reports", exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {"path": report_path, "content": content, "sentiment": sent_text}

    def _step_push(self, dry_run: bool = False) -> dict:
        """推送报告"""
        if dry_run:
            print("  [干跑模式] 跳过推送")
            return {"pushed": False, "reason": "dry_run"}

        email_cfg = self.config.get('email', {})
        if not email_cfg:
            return {"pushed": False, "reason": "no_email_config"}

        password = os.environ.get("SMTP_PASSWORD")
        if not password:
            return {"pushed": False, "reason": "no_smtp_password"}

        date_str = datetime.now().strftime("%Y%m%d")
        report_path = f"./reports/daily_{date_str}.md"

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            content = f"每日量化报告 {date_str}"

        msg = MIMEMultipart()
        msg['From'] = email_cfg.get('sender_email', '')
        msg['To'] = email_cfg.get('recipient_email', '')
        msg['Subject'] = f"每日量化报告 {date_str}"
        msg.attach(MIMEText(content, 'plain', 'utf-8'))

        try:
            with smtplib.SMTP_SSL(
                email_cfg['smtp_server'],
                email_cfg['smtp_port'],
                context=ssl.create_default_context()
            ) as server:
                server.login(msg['From'], password)
                server.send_message(msg)
            print(f"  邮件推送成功: {msg['To']}")
            email_ok = True
        except Exception as e:
            print(f"  邮件推送失败: {e}")
            email_ok = False

        # 钉钉推送
        dingtalk_cfg = self.config.get('dingtalk', {})
        dingtalk_ok = False
        if dingtalk_cfg.get('enabled') and dingtalk_cfg.get('webhook'):
            try:
                import requests
                short_content = content[:800] if len(content) > 800 else content
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": f"【每日量化报告 {date_str}】\n\n{short_content}\n\n---\n⚠️ 仅供参考，不构成投资建议"
                    }
                }
                r = requests.post(dingtalk_cfg['webhook'], json=data, timeout=10)
                dingtalk_ok = r.json().get('errcode', -1) == 0
                print(f"  钉钉推送{'成功' if dingtalk_ok else '失败'}")
            except Exception as e:
                print(f"  钉钉推送异常: {e}")

        if email_ok or dingtalk_ok:
            return {"pushed": True, "email": email_ok, "dingtalk": dingtalk_ok}
        return {"pushed": False, "email": email_ok, "dingtalk": dingtalk_ok}


def run():
    """入口函数"""
    import argparse
    parser = argparse.ArgumentParser(description="每日量化工作流")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式，不发邮件")
    args = parser.parse_args()

    workflow = DailyWorkflow()
    workflow.run(dry_run=args.dry_run)


if __name__ == "__main__":
    run()
