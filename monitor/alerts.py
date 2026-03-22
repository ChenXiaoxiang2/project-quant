"""
实时监控与告警模块
支持: 价格异动 / 成交量突变 / 技术指标报警 / 策略信号触发
推送渠道: 邮件 / 钉钉机器人
"""

import os
import sys
import time
import json
import sqlite3
import threading
import smtplib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.data_loader import StockDataLoader
from strategies.signal_generator import SignalAggregator, asdict


# ── 告警规则模型 ─────────────────────────────────────────────────────────────

@dataclass
class AlertRule:
    """告警规则"""
    id: str
    ts_code: str
    name: str
    alert_type: str   # price_up / price_down / volume_surge / signal_buy / signal_sell / rsi_overbought / rsi_oversold
    threshold: float
    enabled: bool = True
    cooldown_min: int = 60  # 告警冷却期 (分钟)


@dataclass
class Alert:
    """触发告警"""
    id: str
    rule_id: str
    ts_code: str
    name: str
    alert_type: str
    current_value: float
    threshold: float
    message: str
    timestamp: str
    pushed: bool = False


# ── 告警数据库 ───────────────────────────────────────────────────────────────

class AlertDatabase:
    """告警规则和历史存储"""

    def __init__(self, db_path: str = "./data/alerts.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id TEXT PRIMARY KEY,
                ts_code TEXT NOT NULL,
                name TEXT,
                alert_type TEXT,
                threshold REAL,
                enabled INTEGER DEFAULT 1,
                cooldown_min INTEGER DEFAULT 60
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id TEXT PRIMARY KEY,
                rule_id TEXT,
                ts_code TEXT,
                name TEXT,
                alert_type TEXT,
                current_value REAL,
                threshold REAL,
                message TEXT,
                timestamp TEXT,
                pushed INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def add_rule(self, rule: AlertRule):
        self.conn.execute(
            "INSERT OR REPLACE INTO alert_rules VALUES (?,?,?,?,?,?,?)",
            (rule.id, rule.ts_code, rule.name, rule.alert_type,
             rule.threshold, 1 if rule.enabled else 0, rule.cooldown_min)
        )
        self.conn.commit()

    def get_active_rules(self) -> list[AlertRule]:
        rows = self.conn.execute(
            "SELECT * FROM alert_rules WHERE enabled=1"
        ).fetchall()
        return [
            AlertRule(id=r[0], ts_code=r[1], name=r[2], alert_type=r[3],
                      threshold=r[4], enabled=bool(r[5]), cooldown_min=r[6])
            for r in rows
        ]

    def add_alert(self, alert: Alert):
        self.conn.execute(
            "INSERT INTO alert_history VALUES (?,?,?,?,?,?,?,?,?,?)",
            (alert.id, alert.rule_id, alert.ts_code, alert.name, alert.alert_type,
             alert.current_value, alert.threshold, alert.message,
             alert.timestamp, 1 if alert.pushed else 0)
        )
        self.conn.commit()

    def recent_alert_count(self, rule_id: str, minutes: int = 60) -> int:
        since = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
        row = self.conn.execute(
            "SELECT COUNT(*) FROM alert_history WHERE rule_id=? AND timestamp >= ?",
            (rule_id, since)
        ).fetchone()
        return row[0] if row else 0

    def close(self):
        self.conn.close()


# ── 告警推送器 ───────────────────────────────────────────────────────────────

class AlertPusher:
    """告警推送 (邮件 + 钉钉)"""

    def __init__(self, config: dict = None):
        self.config = config or {}

    def push(self, alert: Alert) -> bool:
        """推送告警，返回是否成功"""
        success = True
        if self.config.get("email"):
            success = success and self._push_email(alert)
        if self.config.get("dingtalk"):
            success = success and self._push_dingtalk(alert)
        return success

    def _push_email(self, alert: Alert) -> bool:
        import yaml
        try:
            with open("./config/settings.yaml", 'r', encoding='utf-8') as f:
                email_cfg = yaml.safe_load(f)['email']
        except Exception:
            return False

        password = os.environ.get("SMTP_PASSWORD")
        if not password:
            print(f"[告警] SMTP_PASSWORD 未设置，跳过邮件推送")
            return False

        try:
            import ssl
            msg = f"股票告警: {alert.name}\n\n{alert.message}\n\n时间: {alert.timestamp}"
            email_msg = f"Subject: {alert.alert_type}告警: {alert.name}\n\n{msg}"
            with smtplib.SMTP_SSL(email_cfg['smtp_server'], email_cfg['smtp_port'],
                                  context=ssl.create_default_context()) as server:
                server.login(email_cfg['sender_email'], password)
                server.sendmail(email_cfg['sender_email'],
                                email_cfg['recipient_email'],
                                email_msg)
            print(f"[告警] 邮件发送成功: {alert.name} - {alert.alert_type}")
            return True
        except Exception as e:
            print(f"[告警] 邮件发送失败: {e}")
            return False

    def _push_dingtalk(self, alert: Alert) -> bool:
        webhook = self.config.get("dingtalk_webhook")
        if not webhook:
            return False

        try:
            import requests
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"【股票告警】\n股票: {alert.name}({alert.ts_code})\n类型: {alert.alert_type}\n当前值: {alert.current_value:.2f}\n阈值: {alert.threshold:.2f}\n{alert.message}\n时间: {alert.timestamp}"
                }
            }
            r = requests.post(webhook, json=data, timeout=10)
            result = r.json().get('errcode', -1) == 0
            print(f"[告警] 钉钉推送{'成功' if result else '失败'}: {alert.name}")
            return result
        except Exception as e:
            print(f"[告警] 钉钉推送异常: {e}")
            return False


# ── 实时监控器 ───────────────────────────────────────────────────────────────

class StockWatcher:
    """
    股票实时监控器
    工作模式: 轮询 (可升级为 WebSocket)
    """

    def __init__(
        self,
        db: Optional[AlertDatabase] = None,
        pusher: Optional[AlertPusher] = None,
        poll_interval: int = 30,
    ):
        self.db = db or AlertDatabase()
        self.pusher = pusher or AlertPusher()
        self.poll_interval = poll_interval
        self.loader = StockDataLoader()
        self.signal_agg = SignalAggregator()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_alert(self, ts_code: str, name: str, alert_type: str, threshold: float):
        """快捷添加告警规则"""
        import hashlib
        rule_id = hashlib.md5(f"{ts_code}_{alert_type}".encode()).hexdigest()[:8]
        rule = AlertRule(
            id=rule_id,
            ts_code=ts_code,
            name=name,
            alert_type=alert_type,
            threshold=threshold,
        )
        self.db.add_rule(rule)
        print(f"[Watcher] 添加告警: {name}({ts_code}) {alert_type} {threshold}")
        return rule_id

    def start(self):
        """后台启动监控线程"""
        if self._running:
            print("[Watcher] 已在运行中")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[Watcher] 监控已启动，轮询间隔 {self.poll_interval}秒")

    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[Watcher] 监控已停止")

    def _loop(self):
        """监控循环"""
        while self._running:
            try:
                self._check_all()
            except Exception as e:
                print(f"[Watcher] 轮询异常: {e}")
            time.sleep(self.poll_interval)

    def _check_all(self):
        """检查所有规则"""
        rules = self.db.get_active_rules()
        if not rules:
            return

        # 按代码分组获取实时数据
        codes = list(set(r.ts_code for r in rules))
        qt_codes = [self._to_qt_code(c) for c in codes]

        try:
            quotes = self.loader._tencent.fetch_realtime(qt_codes)
        except Exception as e:
            print(f"[Watcher] 获取行情失败: {e}")
            return

        for rule in rules:
            self._check_rule(rule, quotes)

    def _check_rule(self, rule: AlertRule, quotes: pd.DataFrame):
        """检查单条规则"""
        # 检查冷却期
        recent = self.db.recent_alert_count(rule.id, rule.cooldown_min)
        if recent > 0:
            return

        # 找到对应股票行情
        match = quotes[quotes['ts_code'].str.contains(
            rule.ts_code.split('.')[0], na=False)]
        if match.empty:
            return

        row = match.iloc[0]
        price = float(row.get('current', 0) or row.get('close', 0))
        pct_chg = float(row.get('pct_chg', 0) or 0)
        vol = float(row.get('volume', 0) or 0)

        triggered = False
        current_val = 0.0
        msg = ""

        if rule.alert_type == "price_up" and price >= rule.threshold:
            triggered = True
            current_val = price
            msg = f"股价({price:.2f})达到或超过阈值({rule.threshold:.2f})，涨幅{pct_chg:+.2f}%"

        elif rule.alert_type == "price_down" and price <= rule.threshold:
            triggered = True
            current_val = price
            msg = f"股价({price:.2f})跌破阈值({rule.threshold:.2f})，跌幅{pct_chg:+.2f}%"

        elif rule.alert_type == "pct_chg":
            if abs(pct_chg) >= rule.threshold:
                triggered = True
                current_val = pct_chg
                msg = f"涨跌幅({pct_chg:+.2f}%)触发阈值({rule.threshold:.0f}%)"

        elif rule.alert_type in ("signal_buy", "signal_sell"):
            # 策略信号监控
            try:
                normalized = self._normalize_code(rule.ts_code)
                hist = self.loader.get_historical(normalized,
                    (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d'))
                result = self.signal_agg.get_signal(hist)
                expected_action = "BUY" if rule.alert_type == "signal_buy" else "SELL"
                if result['final_action'] == expected_action:
                    triggered = True
                    current_val = result['votes'][expected_action]
                    msg = f"策略信号触发: {expected_action}, 置信度{result['confidence']}, 得票率{current_val:.1%}"
            except Exception:
                pass

        if triggered:
            alert = Alert(
                id=f"{rule.id}_{int(time.time())}",
                rule_id=rule.id,
                ts_code=rule.ts_code,
                name=rule.name,
                alert_type=rule.alert_type,
                current_value=current_val,
                threshold=rule.threshold,
                message=msg,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
            self.db.add_alert(alert)
            self.pusher.push(alert)
            print(f"[Watcher] 🚨 告警触发: {alert.name} - {msg}")

    def _to_qt_code(self, ts_code: str) -> str:
        code = ts_code.upper().replace('.SH', '').replace('.SZ', '')
        return ('sh' if code.startswith(('6', '5', '9')) else 'sz') + code

    def _normalize_code(self, ts_code: str) -> str:
        code = ts_code.upper().replace('.SH', '').replace('.SZ', '')
        return (f"{code}.SH" if code.startswith(('6', '5', '9')) else f"{code}.SZ")


# ── 快捷函数 ─────────────────────────────────────────────────────────────────

def quick_watch(ts_codes: list[str], names: list[str], price_alert: float = None,
                pct_alert: float = 9.0, dingtalk_webhook: str = None):
    """一行启动监控"""
    pusher = AlertPusher({"dingtalk_webhook": dingtalk_webhook}) if dingtalk_webhook else AlertPusher()
    watcher = StockWatcher(pusher=pusher)

    for code, name in zip(ts_codes, names):
        if price_alert:
            watcher.add_alert(code, name, "price_up", price_alert)
            watcher.add_alert(code, name, "price_down", price_alert * 0.95)
        watcher.add_alert(code, name, "pct_chg", pct_alert)

    watcher.start()
    return watcher


if __name__ == "__main__":
    print("=== 股票监控测试 ===")
    watcher = StockWatcher(poll_interval=60)

    # 添加测试告警
    watcher.add_alert("600519.SH", "贵州茅台", "pct_chg", 5.0)
    watcher.add_alert("600519.SH", "贵州茅台", "signal_buy", 0.5)
    watcher.add_alert("000001.SZ", "平安银行", "pct_chg", 5.0)

    # 单次检查 (不启动后台线程)
    print("\n执行单次告警检查...")
    try:
        quotes = watcher.loader._tencent.fetch_realtime(['sh600519', 'sz000001'])
        for rule in watcher.db.get_active_rules():
            watcher._check_rule(rule, quotes)
    except Exception as e:
        print(f"检查失败: {e}")

    print("\n告警检查完成")
