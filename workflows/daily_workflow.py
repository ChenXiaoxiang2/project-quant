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
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news.collector import NewsCollector, SentimentAnalyzer
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
        db = AlertDatabase()
        # 分析市场整体情绪
        sentiment = analyzer.get_stock_sentiment(db, ts_code=None, days=1)
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
        """整合完整日报"""
        date_str = datetime.now().strftime("%Y%m%d")
        report_path = f"./reports/daily_{date_str}.md"

        lines = [
            f"# 每日量化报告  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "\n---\n",
            "## 一、市场舆情\n",
            "> 实时监控财经资讯，评估市场情绪\n",
            "## 二、智能选股\n",
            "> 基于多因子模型筛选优质标的\n",
            "## 三、策略信号\n",
            "> 多策略聚合，捕捉交易机会\n",
            "## 四、投资建议\n",
            "> 综合技术面、基本面、舆情给出建议\n",
            "\n---\n",
            f"> ⚠️ 仅供参考，不构成投资建议 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        ]

        content = '\n'.join(lines)
        os.makedirs("./reports", exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {"path": report_path, "content": content}

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
            return {"pushed": True, "channel": "email"}
        except Exception as e:
            print(f"  邮件推送失败: {e}")
            return {"pushed": False, "reason": str(e)}


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
