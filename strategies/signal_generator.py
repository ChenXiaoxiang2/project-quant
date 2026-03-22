"""
增强策略库 + 实时信号生成器
支持: 双均线 / 布林带 / RSI超卖 / 海龟交易 / MACD金叉
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── 信号模型 ─────────────────────────────────────────────────────────────────

@dataclass
class TradeSignal:
    """交易信号"""
    ts_code: str
    strategy: str
    action: str          # BUY / SELL / HOLD
    strength: float      # 信号强度 0-1
    price: float
    stop_loss: float
    take_profit: float
    confidence: str     # HIGH / MEDIUM / LOW
    reason: str
    timestamp: str = ""


# ── 策略基类 ─────────────────────────────────────────────────────────────────

class BaseStrategy:
    """策略基类"""

    def __init__(self, name: str):
        self.name = name

    def generate(self, df: pd.DataFrame) -> TradeSignal:
        raise NotImplementedError

    def _atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return float(tr.tail(period).mean())


# ── 策略 1: 双均线交叉 ────────────────────────────────────────────────────────

class DualMAStrategy(BaseStrategy):
    """双均线交叉策略 (MA5 + MA20)"""

    def __init__(self, fast: int = 5, slow: int = 20):
        super().__init__(f"dual_ma_{fast}_{slow}")
        self.fast = fast
        self.slow = slow

    def generate(self, df: pd.DataFrame) -> TradeSignal:
        df = df.dropna(subset=['close']).tail(30)
        ma_fast = df['close'].rolling(self.fast).mean()
        ma_slow = df['close'].rolling(self.slow).mean()

        current = float(df['close'].iloc[-1])
        ma_f = float(ma_fast.iloc[-1])
        ma_s = float(ma_slow.iloc[-1])
        ma_f_prev = float(ma_fast.iloc[-2])
        ma_s_prev = float(ma_slow.iloc[-2])

        atr = self._atr(df)

        # 金叉: 快线上穿慢线
        golden_cross = ma_f_prev <= ma_s_prev and ma_f > ma_s
        # 死叉: 快线下穿慢线
        death_cross = ma_f_prev >= ma_s_prev and ma_f < ma_s

        if golden_cross:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="BUY",
                strength=min((ma_f - ma_s) / ma_s * 2, 1.0),
                price=current,
                stop_loss=round(current - 2 * atr, 2),
                take_profit=round(current + 3 * atr, 2),
                confidence="HIGH" if abs(ma_f - ma_s) / ma_s > 0.01 else "MEDIUM",
                reason=f"MA{self.fast}上穿MA{self.slow}，趋势转多",
            )
        elif death_cross:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="SELL",
                strength=min((ma_s - ma_f) / ma_s * 2, 1.0),
                price=current,
                stop_loss=round(current + 2 * atr, 2),
                take_profit=round(current - 3 * atr, 2),
                confidence="MEDIUM",
                reason=f"MA{self.fast}下穿MA{self.slow}，趋势转空",
            )

        return TradeSignal(
            ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
            strategy=self.name,
            action="HOLD",
            strength=0.0,
            price=current,
            stop_loss=round(current - 2 * atr, 2),
            take_profit=round(current + 3 * atr, 2),
            confidence="LOW",
            reason=f"均线无交叉信号，MA{self.fast}={ma_f:.2f}, MA{self.slow}={ma_s:.2f}",
        )


# ── 策略 2: 布林带突破 ────────────────────────────────────────────────────────

class BollingerStrategy(BaseStrategy):
    """布林带突破策略"""

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(f"bollinger_{period}_{std_dev}")
        self.period = period
        self.std_dev = std_dev

    def generate(self, df: pd.DataFrame) -> TradeSignal:
        df = df.dropna(subset=['close']).tail(30)
        ma = df['close'].rolling(self.period).mean()
        std = df['close'].rolling(self.period).std()

        current = float(df['close'].iloc[-1])
        upper = float((ma + self.std_dev * std).iloc[-1])
        lower = float((ma - self.std_dev * std).iloc[-1])
        prev_close = float(df['close'].iloc[-2])

        atr = self._atr(df)

        # 上轨突破
        if prev_close < upper and current >= upper:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="BUY",
                strength=min((current - upper) / upper * 5, 1.0),
                price=current,
                stop_loss=round(lower, 2),
                take_profit=round(current + 2 * (upper - lower), 2),
                confidence="HIGH",
                reason=f"突破布林带上轨({upper:.2f})，动能强劲",
            )
        # 下轨支撑 (超卖反弹)
        if prev_close > lower and current <= lower:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="BUY",
                strength=0.6,
                price=current,
                stop_loss=round(current - 1.5 * atr, 2),
                take_profit=round(ma.iloc[-1], 2),
                confidence="MEDIUM",
                reason=f"触及布林带下轨({lower:.2f})，超卖反弹信号",
            )
        # 跌破中轨
        if current < float(ma.iloc[-1]):
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="SELL",
                strength=0.5,
                price=current,
                stop_loss=round(current + 2 * atr, 2),
                take_profit=round(lower, 2),
                confidence="LOW",
                reason="跌破布林带中轨，建议减仓",
            )

        return TradeSignal(
            ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
            strategy=self.name,
            action="HOLD",
            strength=0.0,
            price=current,
            stop_loss=round(current - 2 * atr, 2),
            take_profit=round(upper, 2),
            confidence="LOW",
            reason="价格在布林带内运行，无明确信号",
        )


# ── 策略 3: RSI 超买超卖 ─────────────────────────────────────────────────────

class RSIStrategy(BaseStrategy):
    """RSI 超买超卖策略"""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__(f"rsi_{period}")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate(self, df: pd.DataFrame) -> TradeSignal:
        df = df.dropna(subset=['close']).tail(30)

        # RSI 计算
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
        rs = gain / loss
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])

        current = float(df['close'].iloc[-1])
        atr = self._atr(df)

        if rsi < self.oversold:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="BUY",
                strength=min((self.oversold - rsi) / self.oversold, 1.0),
                price=current,
                stop_loss=round(current - 2 * atr, 2),
                take_profit=round(current + 4 * atr, 2),
                confidence="HIGH",
                reason=f"RSI超卖({rsi:.1f})，存在反弹机会",
            )
        elif rsi > self.overbought:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="SELL",
                strength=min((rsi - self.overbought) / self.overbought, 1.0),
                price=current,
                stop_loss=round(current + 2 * atr, 2),
                take_profit=round(current - 3 * atr, 2),
                confidence="MEDIUM",
                reason=f"RSI超买({rsi:.1f})，注意回调风险",
            )

        return TradeSignal(
            ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
            strategy=self.name,
            action="HOLD",
            strength=0.0,
            price=current,
            stop_loss=round(current - 2 * atr, 2),
            take_profit=round(current + 3 * atr, 2),
            confidence="LOW",
            reason=f"RSI={rsi:.1f}，处于正常区间",
        )


# ── 策略 4: 海龟交易 ─────────────────────────────────────────────────────────

class TurtleStrategy(BaseStrategy):
    """海龟交易策略 (唐安琪)"""

    def __init__(self, entry_period: int = 20, exit_period: int = 10):
        super().__init__(f"turtle_{entry_period}_{exit_period}")
        self.entry = entry_period
        self.exit = exit_period

    def generate(self, df: pd.DataFrame) -> TradeSignal:
        df = df.dropna(subset=['close']).tail(60)
        current = float(df['close'].iloc[-1])
        atr = self._atr(df)

        entry_high = float(df['high'].rolling(self.entry).max().iloc[-1])
        entry_low = float(df['low'].rolling(self.entry).min().iloc[-1])
        exit_high = float(df['high'].rolling(self.exit).max().iloc[-1])
        exit_low = float(df['low'].rolling(self.exit).min().iloc[-1])

        # 入场信号
        if current > entry_high:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="BUY",
                strength=0.8,
                price=current,
                stop_loss=round(current - 2 * atr, 2),
                take_profit=round(current + 5 * atr, 2),
                confidence="HIGH",
                reason=f"突破{self.entry}日高点({entry_high:.2f})，趋势确认",
            )

        # 出场信号
        if current < exit_low:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="SELL",
                strength=0.7,
                price=current,
                stop_loss=round(current + 2 * atr, 2),
                take_profit=round(current - 4 * atr, 2),
                confidence="MEDIUM",
                reason=f"跌破{self.exit}日低点({exit_low:.2f})，趋势破坏",
            )

        return TradeSignal(
            ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
            strategy=self.name,
            action="HOLD",
            strength=0.0,
            price=current,
            stop_loss=round(current - 2 * atr, 2),
            take_profit=round(current + 5 * atr, 2),
            confidence="LOW",
            reason=f"未突破{self.entry}日区间，观望",
        )


# ── 策略 5: MACD 金叉死叉 ──────────────────────────────────────────────────

class MACDStrategy(BaseStrategy):
    """MACD 金叉死叉策略"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(f"macd_{fast}_{slow}_{signal}")
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate(self, df: pd.DataFrame) -> TradeSignal:
        df = df.dropna(subset=['close']).tail(60)
        ema12 = df['close'].ewm(span=self.fast, adjust=False).mean()
        ema26 = df['close'].ewm(span=self.slow, adjust=False).mean()
        diff = ema12 - ema26
        dea = diff.ewm(span=self.signal, adjust=False).mean()
        macd = 2 * (diff - dea)

        current = float(df['close'].iloc[-1])
        atr = self._atr(df)

        d_now = float(diff.iloc[-1])
        d_prev = float(diff.iloc[-2])
        dea_now = float(dea.iloc[-1])
        dea_prev = float(dea.iloc[-2])
        macd_now = float(macd.iloc[-1])

        # MACD 金叉 (DIF 上穿 DEA，且 MACD 柱由负转正)
        if d_prev <= dea_prev and d_now > dea_now and macd_now > 0:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="BUY",
                strength=min(abs(macd_now) / current * 10, 1.0),
                price=current,
                stop_loss=round(current - 2 * atr, 2),
                take_profit=round(current + 4 * atr, 2),
                confidence="HIGH",
                reason="MACD 金叉， DIF 上穿 DEA，多头信号",
            )

        # MACD 死叉
        if d_prev >= dea_prev and d_now < dea_now and macd_now < 0:
            return TradeSignal(
                ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
                strategy=self.name,
                action="SELL",
                strength=min(abs(macd_now) / current * 10, 1.0),
                price=current,
                stop_loss=round(current + 2 * atr, 2),
                take_profit=round(current - 3 * atr, 2),
                confidence="MEDIUM",
                reason="MACD 死叉， DIF 下穿 DEA，空头信号",
            )

        return TradeSignal(
            ts_code=str(df.get('ts_code', ['Unknown'])[-1]),
            strategy=self.name,
            action="HOLD",
            strength=0.0,
            price=current,
            stop_loss=round(current - 2 * atr, 2),
            take_profit=round(current + 3 * atr, 2),
            confidence="LOW",
            reason=f"MACD 柱={macd_now:.4f}，无交叉信号",
        )


# ── 多策略信号聚合器 ─────────────────────────────────────────────────────────

class SignalAggregator:
    """
    多策略信号聚合器
    汇总所有策略信号，生成综合评分
    """

    def __init__(self):
        self.strategies = [
            DualMAStrategy(fast=5, slow=20),
            BollingerStrategy(period=20, std_dev=2.0),
            RSIStrategy(period=14, oversold=30, overbought=70),
            TurtleStrategy(entry_period=20, exit_period=10),
            MACDStrategy(fast=12, slow=26, signal=9),
        ]

    def get_signal(self, df: pd.DataFrame) -> dict:
        """对单只股票获取所有策略信号"""
        signals = {}
        for strat in self.strategies:
            sig = strat.generate(df)
            signals[strat.name] = sig

        # 统计 BUY / SELL / HOLD
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for sig in signals.values():
            votes[sig.action] += sig.strength

        total = sum(votes.values()) or 1
        buy_ratio = votes["BUY"] / total
        sell_ratio = votes["SELL"] / total

        # 综合决策
        if buy_ratio >= 0.5:
            final_action = "BUY"
        elif sell_ratio >= 0.5:
            final_action = "SELL"
        else:
            final_action = "HOLD"

        return {
            "signals": {k: asdict(v) for k, v in signals.items()},
            "votes": votes,
            "final_action": final_action,
            "confidence": "HIGH" if max(buy_ratio, sell_ratio) >= 0.7 else "MEDIUM" if max(buy_ratio, sell_ratio) >= 0.5 else "LOW",
        }


def asdict(obj):
    """ dataclass -> dict (递归) """
    import dataclasses
    if dataclasses.is_dataclass(obj):
        result = {}
        for k, v in dataclasses.asdict(obj).items():
            result[k] = asdict(v) if dataclasses.is_dataclass(v) else v
        return result
    return obj


if __name__ == "__main__":
    print("=== 策略信号生成测试 ===")
    # 模拟数据
    dates = pd.date_range(end=datetime.now(), periods=60)
    np.random.seed(42)
    base = 100
    prices = base + np.cumsum(np.random.randn(60) * 2)

    df = pd.DataFrame({
        'date': dates,
        'open': prices + np.random.randn(60) * 0.5,
        'high': prices + np.abs(np.random.randn(60)) * 1.5,
        'low': prices - np.abs(np.random.randn(60)) * 1.5,
        'close': prices,
        'volume': np.random.randint(1e6, 5e6, 60),
    })

    agg = SignalAggregator()
    result = agg.get_signal(df)
    print(f"综合信号: {result['final_action']} (置信度: {result['confidence']})")
    print(f"投票: {result['votes']}")
    for name, sig in result['signals'].items():
        print(f"  {name}: {sig['action']} ({sig['confidence']}) | {sig['reason']}")
