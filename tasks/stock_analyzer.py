"""
个股综合分析引擎
输入股票代码 → 输出实时行情 + 财务指标 + 技术分析 + 投资建议
"""

import os
import sys
import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import StockDataLoader, BaostockDataLoader
from strategies.alpha_factors import AlphaFactors
from strategies.trend_strategy import TrendStrategy


class StockAnalyzer:
    """个股综合分析器"""

    def __init__(self):
        self.loader = StockDataLoader()
        self.baostock = BaostockDataLoader()
        self.alpha = AlphaFactors()
        self.trend = TrendStrategy()

    def _normalize_code(self, code: str) -> tuple[str, str, str]:
        """返回 (qt_code, ts_code, bs_code)"""
        code = code.strip().upper()
        if '.' in code:
            symbol, market = code.split('.')
        elif code.startswith(('6', '5', '9')):
            symbol, market = code, 'SH'
        else:
            symbol, market = code, 'SZ'

        market_lower = market.lower()
        qt = f"{market_lower}{symbol}"
        ts = f"{symbol}.{market}"
        bs_market = 'sh' if market == 'SH' else 'sz'
        bs = f"{bs_market}.{symbol}"
        return qt, ts, bs

    def analyze(self, stock_code: str) -> dict:
        """
        综合分析一只股票，返回完整报告字典
        """
        qt_code, ts_code, bs_code = self._normalize_code(stock_code)
        result = {
            'stock_code': stock_code,
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'realtime': {},
            'technical': {},
            'financial': {},
            'signal': {},
            'advice': '',
        }

        # 1. 实时行情
        try:
            quote = self.loader.get_single_quote(ts_code)
            result['realtime'] = {
                'name': quote.get('name', ''),
                'current': quote.get('current'),
                'close': quote.get('close'),
                'open': quote.get('open'),
                'high': quote.get('high'),
                'low': quote.get('low'),
                'pct_chg': quote.get('pct_chg'),
                'amount': quote.get('amount'),
                'volume': quote.get('volume'),
            }
        except Exception as e:
            result['realtime'] = {'error': str(e)}

        # 2. 历史K线 (最近250个交易日，用于技术分析)
        try:
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
            # 优先使用新浪财经K线
            hist = self.loader.get_historical(ts_code, start, end)
            if hist.empty:
                # fallback: 腾讯K线
                hist = self.loader._tencent.fetch_historical(qt_code, 'day', 250)
        except Exception:
            try:
                hist = self.loader._tencent.fetch_historical(qt_code, 'day', 250)
            except Exception as e:
                result['technical'] = {'error': f'无法获取K线数据: {e}'}
                hist = pd.DataFrame()

        # 3. 技术分析
        if not hist.empty and 'close' in hist.columns:
            try:
                df = hist.copy()
                df = df.dropna(subset=['close'])

                # RSI
                rsi = self.alpha.calculate_rsi(df).iloc[-1]
                # 动量
                momentum = self.alpha.calculate_momentum(df).iloc[-1]
                # 均线
                ma5 = df['close'].rolling(5).mean().iloc[-1]
                ma20 = df['close'].rolling(20).mean().iloc[-1]
                ma60 = df['close'].rolling(60).mean().iloc[-1]
                current_price = df['close'].iloc[-1]

                # 趋势信号
                signal = self.trend.generate_signal(self.trend.calculate_indicators(df.copy()))

                result['technical'] = {
                    'price': round(float(current_price), 2),
                    'ma5': round(float(ma5), 2),
                    'ma20': round(float(ma20), 2),
                    'ma60': round(float(ma60), 2),
                    'rsi': round(float(rsi), 1) if not np.isnan(rsi) else None,
                    'momentum': round(float(momentum) * 100, 2) if not np.isnan(momentum) else 0,
                    'signal': signal,
                }
            except Exception as e:
                result['technical'] = {'error': str(e)}

        # 4. 财务指标 (AKShare)
        try:
            symbol = stock_code.strip().upper().replace('.SH', '').replace('.SZ', '').replace('SH', '').replace('SZ', '')
            fin_df = self._fetch_financial_indicator(symbol)
            if fin_df is not None and not fin_df.empty:
                latest = fin_df.iloc[0]
                result['financial'] = {
                    'report_date': str(latest.get('日期', '')),
                    'roe': self._safe_float(latest, '净资产收益率(%)'),
                    'gross_margin': self._safe_float(latest, '销售毛利率(%)'),
                    'debt_ratio': self._safe_float(latest, '资产负债率(%)'),
                    'eps': self._safe_float(latest, '基本每股收益(元)'),
                    'bvps': self._safe_float(latest, '每股净资产(元)'),
                    'operating_cf': self._safe_float(latest, '经营活动产生的现金流量净额(元)'),
                    'revenue_growth': self._safe_float(latest, '营业收入同比增长率(%)'),
                    'profit_growth': self._safe_float(latest, '净利润同比增长率(%)'),
                }
        except Exception as e:
            result['financial'] = {'error': str(e)}

        # 5. 综合评分与建议
        result['advice'] = self._generate_advice(result)

        return result

    def _fetch_financial_indicator(self, symbol: str) -> pd.DataFrame:
        """获取财务指标 (AKShare)，支持被代理阻断"""
        try:
            import akshare as ak
            os.environ['NO_PROXY'] = '*'
            os.environ['no_proxy'] = '*'
            year = datetime.now().year
            df = ak.stock_financial_analysis_indicator(
                symbol=symbol,
                start_year=str(year - 1)
            )
            return df
        except Exception:
            return None

    def _safe_float(self, row, col, default=None):
        try:
            val = row.get(col)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            return round(float(val), 4)
        except Exception:
            return default

    def _generate_advice(self, result: dict) -> str:
        """基于各项指标生成投资建议"""
        tech = result.get('technical', {})
        fin = result.get('financial', {})
        rt = result.get('realtime', {})
        signal = tech.get('signal', 'HOLD')
        rsi = tech.get('rsi')
        pct_chg = rt.get('pct_chg')
        roe = fin.get('roe')
        debt = fin.get('debt_ratio')
        momentum = tech.get('momentum', 0)

        parts = []

        # 1. 趋势判断
        if signal == 'BUY':
            parts.append("📈 **趋势向上**: 均线多头排列，ADX强势，适合顺势做多")
        else:
            parts.append("⚖️ **趋势中性**: 暂无明确趋势信号，建议观望")

        # 2. RSI 判断
        if rsi is not None:
            if rsi > 75:
                parts.append(f"⚠️ **RSI={rsi:.1f}**: 处于超买区域，追高风险大")
            elif rsi < 30:
                parts.append(f"🟢 **RSI={rsi:.1f}**: 处于超卖区域，存在反弹机会")
            else:
                parts.append(f"✅ **RSI={rsi:.1f}**: 处于正常区间")

        # 3. 今日涨跌幅
        if pct_chg is not None:
            if pct_chg > 5:
                parts.append(f"🔥 今日涨幅 {pct_chg:.2f}%，注意追高风险")
            elif pct_chg < -5:
                parts.append(f"💎 今日跌幅 {pct_chg:.2f}%，关注支撑位是否企稳")
            elif pct_chg > 0:
                parts.append(f"📊 今日小涨 {pct_chg:.2f}%，走势平稳")
            else:
                parts.append(f"📉 今日下跌 {pct_chg:.2f}%，注意止损")

        # 4. 基本面
        if roe is not None:
            if roe > 15:
                parts.append(f"💰 净资产收益率 ROE={roe:.2f}%，盈利能力优秀")
            elif roe > 8:
                parts.append(f"📋 ROE={roe:.2f}%，盈利能力良好")
            else:
                parts.append(f"⚠️ ROE={roe:.2f}%，盈利能力偏弱")

        if debt is not None:
            if debt > 70:
                parts.append(f"⚠️ 资产负债率={debt:.2f}%，债务风险较高")
            elif debt < 50:
                parts.append(f"✅ 资产负债率={debt:.2f}%，财务结构稳健")

        # 5. 动量
        if momentum is not None:
            if momentum > 5:
                parts.append(f"🚀 短期动能强劲 (+{momentum:.2f}%)")
            elif momentum < -5:
                parts.append(f"📉 短期动能走弱 ({momentum:.2f}%)")

        # 6. 综合结论
        buy_signals = sum([
            signal == 'BUY',
            (rsi is not None and 40 < rsi < 65),
            (pct_chg is not None and -3 < pct_chg < 3),
            (roe is not None and roe > 10),
            (debt is not None and debt < 60),
        ])

        if buy_signals >= 4:
            parts.append("\n🏆 **综合评级: 强烈推荐买入**")
        elif buy_signals >= 3:
            parts.append("\n👍 **综合评级: 建议关注**")
        elif buy_signals >= 2:
            parts.append("\n👀 **综合评级: 谨慎观望**")
        else:
            parts.append("\n🚫 **综合评级: 暂不推荐**")

        return '\n'.join(parts)

    def format_markdown(self, result: dict) -> str:
        """将分析结果格式化为 Markdown 报告"""
        rt = result.get('realtime', {})
        tech = result.get('technical', {})
        fin = result.get('financial', {})
        name = rt.get('name', result['stock_code'])
        code = result['stock_code']
        time_str = result['report_time']

        lines = [
            f"# 📊 个股分析报告: {name} ({code})",
            f"\n> 生成时间: {time_str}  |  数据来源: 腾讯财经 / Baostock / AKShare",
            "\n---\n",
            "## 一、实时行情",
            f"\n| 指标 | 数值 |",
            f"|------|------|",
            f"| 当前价 | **{rt.get('current', 'N/A')}** |",
            f"| 昨收价 | {rt.get('close', 'N/A')} |",
            f"| 今日涨跌幅 | {rt.get('pct_chg', 'N/A')}% |",
            f"| 今日最高 | {rt.get('high', 'N/A')} |",
            f"| 今日最低 | {rt.get('low', 'N/A')} |",
            f"| 成交额 | {self._fmt_amount(rt.get('amount'))} |",
            "\n---\n",
            "## 二、技术分析",
        ]

        if 'error' in tech:
            lines.append(f"\n*技术数据获取失败: {tech['error']}*")
        else:
            lines.extend([
                f"\n| 指标 | 数值 | 信号 |",
                f"|------|------|------|",
                f"| 当前价 | {tech.get('price', 'N/A')} | — |",
                f"| MA5 | {tech.get('ma5', 'N/A')} | {'✅ 站上' if (tech.get('price') or 0) > (tech.get('ma5') or 0) else '❌ 跌破'} |",
                f"| MA20 | {tech.get('ma20', 'N/A')} | {'✅ 站上' if (tech.get('price') or 0) > (tech.get('ma20') or 0) else '❌ 跌破'} |",
                f"| MA60 | {tech.get('ma60', 'N/A')} | {'✅ 站上' if (tech.get('price') or 0) > (tech.get('ma60') or 0) else '❌ 跌破'} |",
                f"| RSI(14) | {tech.get('rsi', 'N/A')} | {'超买⚠️' if (tech.get('rsi') or 0) > 70 else '超卖🟢' if (tech.get('rsi') or 0) < 30 else '正常✅'} |",
                f"| 5日动能 | {tech.get('momentum', 'N/A')}% | {'强📈' if (tech.get('momentum') or 0) > 3 else '弱📉'} |",
                f"| 趋势信号 | {tech.get('signal', 'N/A')} | — |",
            ])

        lines.extend([
            "\n---\n",
            "## 三、财务指标",
        ])

        if 'error' in fin:
            lines.append(f"\n*财务数据获取失败: {fin['error']}*")
        elif fin:
            fin_date = fin.get('report_date', 'N/A')
            lines.extend([
                f"\n> 数据截止: {fin_date}",
                f"\n| 指标 | 数值 | 参考值 | 评价 |",
                f"|------|------|--------|------|",
                self._fin_row('净资产收益率 (ROE)', fin.get('roe'), '>15%', self._eval_roe),
                self._fin_row('销售毛利率', fin.get('gross_margin'), '>30%', self._eval_margin),
                self._fin_row('资产负债率', fin.get('debt_ratio'), '<60%', self._eval_debt),
                self._fin_row('基本每股收益 (EPS)', fin.get('eps'), '越高越好', self._eval_generic),
                self._fin_row('每股净资产 (BVPS)', fin.get('bvps'), '>5元', self._eval_generic),
                self._fin_row('营收同比增长率', fin.get('revenue_growth'), '>10%', self._eval_growth),
                self._fin_row('净利润同比增长率', fin.get('profit_growth'), '>10%', self._eval_growth),
            ])
        else:
            lines.append("\n*暂无财务数据*")

        lines.extend([
            "\n---\n",
            "## 四、综合投资建议",
            f"\n{result.get('advice', '数据不足，无法生成建议')}",
            "\n---\n",
            "> ⚠️ **免责声明**: 本报告仅供参考，不构成投资建议。股市有风险，入市需谨慎。",
        ])

        return '\n'.join(lines)

    def _fin_row(self, label, value, ref, eval_fn):
        val_str = f"{value:.2f}" if value is not None else "N/A"
        eval_str = eval_fn(value) if value is not None else "—"
        return f"| {label} | {val_str} | {ref} | {eval_str} |"

    def _eval_roe(self, v): return '优秀💰' if v > 15 else '良好📋' if v > 8 else '偏弱⚠️'
    def _eval_margin(self, v): return '优秀💰' if v > 30 else '良好📋' if v > 15 else '偏低⚠️'
    def _eval_debt(self, v): return '优秀✅' if v < 50 else '良好📋' if v < 70 else '过高⚠️'
    def _eval_growth(self, v): return '增长强劲🚀' if v > 15 else '增长平稳📊' if v > 0 else '下滑⚠️'
    def _eval_generic(self, v): return '良好✅' if v is not None else '—'

    def _fmt_amount(self, val):
        if val is None: return 'N/A'
        if val > 1e8: return f"{val/1e8:.2f}亿"
        if val > 1e4: return f"{val/1e4:.2f}万"
        return str(val)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    analyzer = StockAnalyzer()
    result = analyzer.analyze('600519')
    md = analyzer.format_markdown(result)
    with open('analyzer_output.md', 'w', encoding='utf-8') as f:
        f.write(md)
    print("报告已生成: analyzer_output.md")
