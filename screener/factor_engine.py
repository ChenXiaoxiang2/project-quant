"""
智能选股引擎
支持多因子筛选 + 技术形态筛选 + 行业轮动
"""

import os
import sys
import time
import random
import warnings
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.data_loader import StockDataLoader
from strategies.alpha_factors import AlphaFactors
from strategies.trend_strategy import TrendStrategy


# ── 配置模型 ─────────────────────────────────────────────────────────────────

@dataclass
class FactorConfig:
    """因子配置"""
    # 基本面因子
    pe_max: Optional[float] = 30.0          # 市盈率上限
    pb_max: Optional[float] = 5.0           # 市净率上限
    roe_min: Optional[float] = 10.0         # 净资产收益率下限 (%)
    gross_margin_min: Optional[float] = 20.0 # 毛利率下限 (%)
    debt_ratio_max: Optional[float] = 60.0  # 资产负债率上限 (%)
    profit_growth_min: Optional[float] = 0.0 # 净利润增速下限 (%)
    revenue_growth_min: Optional[float] = 0.0 # 营收增速下限 (%)

    # 技术因子
    volume_boost_min: Optional[float] = 1.5  # 量比下限 (今日成交量/5日均量)
    price_change_min: Optional[float] = 0.0 # 涨幅下限 (%)
    price_change_max: Optional[float] = 9.0  # 涨幅上限 (避免涨停)
    rsi_max: Optional[float] = 70.0          # RSI 上限 (避免超买)
    ma20_break: bool = True                  # 是否要求站上20日均线

    # 筛选数量
    top_n: int = 50                           # 返回前 N 只


@dataclass
class ScreenResult:
    """选股结果"""
    rank: int
    ts_code: str
    name: str
    close: float
    pct_chg: float
    score: float        # 综合评分
    factors: dict        # 命中的因子
    signal: str          # BUY / HOLD
    reason: str          # 推荐理由


# ── 多因子选股引擎 ──────────────────────────────────────────────────────────────

class StockScreener:
    """
    智能选股引擎

    工作流程:
    1. 获取全市场实时行情
    2. 应用基本面因子过滤 (从 AKShare 获取财务数据)
    3. 应用技术因子过滤
    4. 计算综合评分
    5. 生成选股报告
    """

    def __init__(self, config: Optional[FactorConfig] = None):
        self.config = config or FactorConfig()
        self.loader = StockDataLoader()
        self.alpha = AlphaFactors()
        self.trend = TrendStrategy()

    def screen(self, dry_run: bool = False) -> list[ScreenResult]:
        """
        执行选股，返回符合条件的股票列表
        dry_run: True 时跳过 AKShare 财务数据 (网络不稳定时)
        """
        print(f"[选股引擎] 开始选股，配置: {self.config}")
        results: list[ScreenResult] = []

        # 1. 获取全市场实时行情
        try:
            market_df = self.loader.get_stock_list()
        except Exception as e:
            print(f"[选股] 全市场行情获取失败: {e}，使用模拟数据")
            market_df = self._mock_market_data()

        if market_df.empty:
            print("[选股] 市场数据为空")
            return []

        # 2. 基础过滤: 排除 ST、涨跌停、退市
        market_df = self._pre_filter(market_df)
        print(f"[选股] 预过滤后剩余: {len(market_df)} 只")

        # 3. 对每只股票进行因子评分
        scored: list[dict] = []
        codes = market_df['ts_code'].dropna().unique()[:200]  # 限制计算量

        for code in codes:
            try:
                score_info = self._score_stock(code, dry_run=dry_run)
                if score_info:
                    scored.append(score_info)
            except Exception:
                continue

        if not scored:
            return []

        # 4. 按评分排序，取 top_n
        scored_df = pd.DataFrame(scored).sort_values('score', ascending=False)
        scored_df = scored_df.head(self.config.top_n)

        # 5. 转换为结果对象
        for rank, (_, row) in enumerate(scored_df.iterrows(), 1):
            ts_code = str(row.get('ts_code', ''))
            results.append(ScreenResult(
                rank=rank,
                ts_code=ts_code,
                name=str(row.get('name', ts_code)),
                close=float(row.get('close') or 0),
                pct_chg=float(row.get('pct_chg') or 0),
                score=float(row.get('score') or 0),
                factors=dict(row.get('factors') or {}),
                signal=str(row.get('signal') or 'HOLD'),
                reason=str(row.get('reason') or ''),
            ))

        return results

    def _pre_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """预过滤: ST、涨跌停、退市股"""
        # 排除ST
        if 'name' in df.columns:
            df = df[~df['name'].str.contains('ST|退市|N ', na=False)]

        # 涨幅过滤
        pct_col = 'pct_chg' if 'pct_chg' in df.columns else None
        if pct_col:
            df[pct_col] = pd.to_numeric(df[pct_col], errors='coerce')
            df = df[(df[pct_col] >= -9.9) & (df[pct_col] <= 9.9)]

        return df

    def _score_stock(self, ts_code: str, dry_run: bool = False) -> Optional[dict]:
        """对单只股票评分"""
        cfg = self.config
        factors = {}
        score = 0.0

        # 获取实时数据
        try:
            qt_code = self._to_qt_code(ts_code)
            quote_df = self.loader._tencent.fetch_realtime([qt_code])
            if quote_df.empty:
                return None
            quote = quote_df.iloc[0]
            close = float(quote.get('current', 0) or quote.get('close', 0))
            pct_chg = float(quote.get('pct_chg', 0) or 0)
            name = quote.get('name', ts_code)
        except Exception:
            return None

        if close <= 0:
            return None

        # ── 技术因子评分 ──────────────────────────────────────────────────────

        # 涨幅过滤
        if cfg.price_change_min is not None and pct_chg < cfg.price_change_min:
            return None
        if cfg.price_change_max is not None and pct_chg > cfg.price_change_max:
            return None

        # 获取历史K线 (使用新浪财经)
        normalized = self._normalize_code(ts_code)
        try:
            end_d = datetime.now().strftime('%Y-%m-%d')
            start_d = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            hist = self.loader.get_historical(normalized, start_d, end_d)
        except Exception:
            return None

        if hist.empty or len(hist) < 30:
            return None

        hist = hist.dropna(subset=['close']).tail(60)

        # RSI
        rsi = self.alpha.calculate_rsi(hist).iloc[-1]
        if pd.isna(rsi):
            rsi = 50
        rsi = float(rsi)

        if cfg.rsi_max and rsi > cfg.rsi_max:
            return None  # 超买过滤

        # 均线多头
        ma5 = hist['close'].rolling(5).mean().iloc[-1]
        ma20 = hist['close'].rolling(20).mean().iloc[-1]
        ma60 = hist['close'].rolling(60).mean().iloc[-1]

        above_ma20 = close > ma20
        above_ma60 = close > ma60

        # 动量
        momentum = float(self.alpha.calculate_momentum(hist).iloc[-1])
        if pd.isna(momentum):
            momentum = 0

        # 量比
        vol_today = float(hist['volume'].iloc[-1])
        vol_ma5 = float(hist['volume'].tail(5).mean())
        vol_ratio = vol_today / vol_ma5 if vol_ma5 > 0 else 1

        if cfg.volume_boost_min and vol_ratio < cfg.volume_boost_min:
            pass  # 量比不足扣分但不剔除

        # ── 基本面评分 (dry_run 时跳过) ───────────────────────────────────────
        financial_score = 0
        if not dry_run:
            try:
                symbol = ts_code.split('.')[0].replace('sh', '').replace('sz', '')
                fin_df = self._fetch_financial(symbol)
                if fin_df is not None and not fin_df.empty:
                    latest = fin_df.iloc[0]
                    roe = self._safe(latest, '净资产收益率(%)')
                    gross_margin = self._safe(latest, '销售毛利率(%)')
                    debt = self._safe(latest, '资产负债率(%)')

                    if roe and cfg.roe_min and roe >= cfg.roe_min:
                        financial_score += 20
                        factors['ROE达标'] = round(roe, 1)

                    if gross_margin and cfg.gross_margin_min and gross_margin >= cfg.gross_margin_min:
                        financial_score += 10
                        factors['毛利率达标'] = round(gross_margin, 1)

                    if debt and cfg.debt_ratio_max and debt <= cfg.debt_ratio_max:
                        financial_score += 10
                        factors['资产负债率达标'] = round(debt, 1)
            except Exception:
                pass

        # ── 综合评分 ──────────────────────────────────────────────────────────

        # 技术分
        tech_score = 0
        if above_ma20: tech_score += 15
        if above_ma60: tech_score += 10
        if 40 <= rsi <= 60: tech_score += 10  # RSI 适中区
        if vol_ratio is not None and cfg.volume_boost_min and vol_ratio >= cfg.volume_boost_min: tech_score += 10
        if momentum > 0: tech_score += 10

        score = tech_score + financial_score

        # 趋势信号
        try:
            indicators = self.trend.calculate_indicators(hist.copy())
            signal = self.trend.generate_signal(indicators)
        except Exception:
            signal = 'HOLD'

        # 生成理由
        reasons = []
        if above_ma20: reasons.append("站上20日均线")
        if above_ma60: reasons.append("站上60日均线")
        if vol_ratio >= 1.5: reasons.append(f"量比放大({vol_ratio:.1f}x)")
        if momentum > 0: reasons.append("动能向上")
        if above_ma20 and above_ma60: reasons.append("均线多头排列")

        return {
            'ts_code': ts_code,
            'name': name,
            'close': close,
            'pct_chg': pct_chg,
            'score': score,
            'factors': factors,
            'signal': signal if signal == 'BUY' else ('BUY' if score >= 45 else 'HOLD'),
            'reason': '; '.join(reasons[:3]),
        }

    def _fetch_financial(self, symbol: str) -> Optional[pd.DataFrame]:
        """获取财务指标"""
        try:
            import akshare as ak
            os.environ['NO_PROXY'] = '*'
            year = datetime.now().year
            return ak.stock_financial_analysis_indicator(
                symbol=symbol, start_year=str(year - 1)
            )
        except Exception:
            return None

    def _safe(self, row, col, default=None):
        try:
            v = row.get(col)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return default
            return float(v)
        except Exception:
            return default

    def _normalize_code(self, code: str) -> str:
        code = code.upper().replace('SH', '').replace('SZ', '')
        if code.startswith(('6', '5', '9')):
            return f"{code}.SH"
        return f"{code}.SZ"

    def _to_qt_code(self, code: str) -> str:
        code = code.lower()
        if code.startswith('sh') or '.SH' in code:
            return code.replace('.SH', '').replace('sh', 'sh')
        return code.replace('.SZ', '').replace('sz', 'sz')

    def _mock_market_data(self) -> pd.DataFrame:
        """网络故障时的模拟数据"""
        return pd.DataFrame({
            'ts_code': [f'{i:06d}.{"SH" if i < 300 else "SZ"}' for i in range(600000, 600200)],
            'name': [f'测试{i}' for i in range(200)],
            'close': np.random.uniform(10, 200, 200),
            'pct_chg': np.random.uniform(-5, 5, 200),
        })

    # ── 报告生成 ──────────────────────────────────────────────────────────────

    def generate_report(self, results: list[ScreenResult]) -> str:
        """生成选股报告 Markdown"""
        if not results:
            return "## 今日无符合条件股票\n\n请适当放宽筛选条件。\n"

        lines = [
            f"# 智能选股报告 ({datetime.now().strftime('%Y-%m-%d')})\n",
            f"\n> 筛选条件: ROE>{self.config.roe_min}%, 量比>{self.config.volume_boost_min}x, 站上MA20\n",
            f"> 共筛选出 **{len(results)}** 只符合条件的股票\n",
            "\n## TOP 10 推荐\n\n",
            "| 排名 | 代码 | 名称 | 现价 | 涨幅 | 评分 | 信号 | 推荐理由 |",
            "|------|------|------|------|------|------|------|----------|",
        ]

        for r in results[:10]:
            signal_emoji = "🟢" if r.signal == 'BUY' else "🟡"
            lines.append(
                f"| {r.rank} | {r.ts_code} | {r.name} | {r.close:.2f} | "
                f"{r.pct_chg:+.2f}% | {r.score:.0f} | {signal_emoji}{r.signal} | {r.reason} |"
            )

        lines.extend([
            "\n\n---\n",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "> ⚠️ 仅供参考，不构成投资建议。\n",
        ])
        return '\n'.join(lines)


# ── 快捷函数 ──────────────────────────────────────────────────────────────────

def quick_screen(
    roe_min: float = 10,
    volume_boost: float = 1.5,
    ma20_break: bool = True,
    top_n: int = 30,
) -> list[ScreenResult]:
    """一行执行选股: quick_screen(roe_min=15, top_n=20)"""
    config = FactorConfig(
        roe_min=roe_min,
        volume_boost_min=volume_boost,
        ma20_break=ma20_break,
        top_n=top_n,
    )
    screener = StockScreener(config)
    return screener.screen()


if __name__ == "__main__":
    print("=== 智能选股测试 (干跑模式) ===")
    screener = StockScreener(FactorConfig(top_n=30))
    results = screener.screen(dry_run=True)
    print(f"\n筛选出 {len(results)} 只股票:")
    for r in results[:5]:
        print(f"  {r.rank}. {r.name}({r.ts_code}) 现价={r.close} 涨幅={r.pct_chg:+.2f}% 评分={r.score:.0f} {r.signal} | {r.reason}")

    report = screener.generate_report(results)
    print("\n报告预览:")
    print(report[:500])
