"""
多源股票数据加载器
支持 3 层 fallback: AKShare(实时) → 腾讯/新浪直调 → Baostock(历史)
"""

import time
import random
import os
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------------------------
# 源 1: 腾讯财经直调 (最稳定，延迟 ~3s)
# ------------------------------------------------------------------------------


class TencentDataLoader:
    """腾讯财经直调 — 实时行情 + 历史K线，最稳定"""

    def fetch_realtime(self, codes: list[str]) -> pd.DataFrame:
        """
        获取多只股票实时行情
        codes 格式: ['sh600519', 'sz000001']  (sh=上交所, sz=深交所)
        """
        codes_str = ','.join(codes)
        url = f"https://qt.gtimg.cn/q={codes_str}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.qq.com',
        }
        import requests
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        rows = []
        for line in r.text.strip().split('\n'):
            if '=' not in line:
                continue
            raw = line.split('"')[1]
            fields = raw.split('~')
            if len(fields) < 40:
                continue
            code_raw = line.split('"')[0].split('_')[-1].replace('=', '')
            rows.append({
                'ts_code': code_raw,
                'name': fields[1],
                'current': float(fields[3]) if fields[3] else None,
                'close': float(fields[4]) if fields[4] else None,
                'open': float(fields[5]) if fields[5] else None,
                'volume': float(fields[6]) if fields[6] else None,
                'high': float(fields[33]) if fields[33] else None,
                'low': float(fields[34]) if fields[34] else None,
                'pct_chg': float(fields[32]) if fields[32] else None,
                'amount': float(fields[37]) if fields[37] else None,
            })
        return pd.DataFrame(rows)

    def fetch_historical(self, code: str, period: str = 'day', count: int = 300) -> pd.DataFrame:
        """
        获取历史K线
        code 格式: 'sh600519' 或 'sz000001'
        period: day/week/month
        """
        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {'param': f'{code},{period},,{count},qfq'}
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.qq.com',
        }
        import requests
        r = requests.get(url, params=params, headers=headers, timeout=10)
        resp = r.json()

        # data 可能是 dict{'qfqday': [...]} 或 list
        raw_data = resp.get('data', {})
        if isinstance(raw_data, list):
            # 按年份分段的 list，取第一段
            raw_data = raw_data[0] if raw_data else {}

        klines = (raw_data.get('qfqday') or raw_data.get('day') or [])
        if not klines:
            return pd.DataFrame(columns=['date', 'open', 'close', 'high', 'low', 'volume'])

        df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        return df


# ------------------------------------------------------------------------------
# 源 2: 新浪财经直调 (备用实时源)
# ------------------------------------------------------------------------------


class SinaDataLoader:
    """新浪财经直调 — 实时行情"""

    def fetch_realtime(self, codes: list[str]) -> pd.DataFrame:
        """
        codes 格式: ['sh600519', 'sz000001']
        """
        codes_str = ','.join(codes)
        url = f"http://hq.sinajs.cn/list={codes_str}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'http://finance.sina.com.cn',
        }
        import requests
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        rows = []
        for line in r.text.strip().split('\n'):
            if '=' not in line:
                continue
            raw = line.split('"')[1]
            fields = raw.split(',')
            if len(fields) < 10:
                continue
            code_raw = line.split('"')[0].split('_')[-1]
            rows.append({
                'ts_code': code_raw,
                'name': fields[0],
                'current': float(fields[3]),
                'close': float(fields[2]),
                'open': float(fields[1]),
                'high': float(fields[4]),
                'low': float(fields[5]),
                'volume': float(fields[8]),
                'amount': float(fields[9]),
                'pct_chg': None,
            })
        return pd.DataFrame(rows)


# ------------------------------------------------------------------------------
# 源 3: AKShare (实时行情 + 历史日线)
# ------------------------------------------------------------------------------


class AKShareDataLoader:
    """AKShare — 东方财富源，无需Token"""

    def fetch_daily_all(self) -> pd.DataFrame:
        """全市场实时行情"""
        os.environ['NO_PROXY'] = '*'
        os.environ['no_proxy'] = '*'
        df = ak.stock_zh_a_spot_em()
        rename_map = {
            '代码': 'ts_code',
            '名称': 'name',
            '最新价': 'close',
            '涨跌幅': 'pct_chg',
            '成交量': 'vol',
            '成交额': 'amount',
        }
        return df.rename(columns=rename_map)

    def fetch_historical(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """个股历史日线"""
        symbol = ts_code.split('.')[0]
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"
        )
        rename_map = {
            '日期': 'trade_date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'vol',
        }
        return df.rename(columns=rename_map)


# ------------------------------------------------------------------------------
# 源 4: Baostock (历史数据最可靠，适合回测)
# ------------------------------------------------------------------------------


class BaostockDataLoader:
    """Baostock — 历史K线最可靠，无需注册"""

    def fetch_historical(self, ts_code: str, start_date: str, end_date: str,
                         adjustflag: str = '2') -> pd.DataFrame:
        """
        获取历史日K线 (前复权)
        ts_code 格式: 'sh.600519' 或 'sz.000001'
        adjustflag: '1'=后复权, '2'=前复权, '3'=不复权
        """
        import baostock as bs

        # 转换: 600519.SH -> sh.600519, 000001.SZ -> sz.000001, sh600519 -> sh.600519
        ts_upper = ts_code.upper()
        if ts_code.startswith('sh') or '.SH' in ts_code or (len(ts_code) == 9 and ts_code[0] == 's'):
            market = 'sh'
        else:
            market = 'sz'
        # 提取纯数字代码
        import re
        symbol = re.sub(r'[^0-9]', '', ts_code)
        bs_code = f"{market}.{symbol}"

        bs.login()
        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,adjustflag,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag=adjustflag
            )
            rows = []
            while rs.error_code == '0' and rs.next():
                rows.append(rs.get_row_data())
        finally:
            bs.logout()

        if not rows:
            return pd.DataFrame(columns=['trade_date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'adjustflag', 'pctChg'])

        df = pd.DataFrame(rows, columns=rs.fields)
        df['date'] = pd.to_datetime(df['date'])
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.rename(columns={'date': 'trade_date'})
        return df

    def fetch_stock_list(self) -> pd.DataFrame:
        """获取全市场股票列表"""
        import baostock as bs
        bs.login()
        try:
            rs = bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
            rows = []
            while rs.error_code == '0' and rs.next():
                rows.append(rs.get_row_data())
        finally:
            bs.logout()
        df = pd.DataFrame(rows, columns=rs.fields)
        return df


# ------------------------------------------------------------------------------
# 统一数据加载器 (多源 fallback)
# ------------------------------------------------------------------------------


class StockDataLoader:
    """
    统一数据加载器，3 层 fallback 策略:
      实时行情: Tencent → Sina → AKShare
      历史数据: Baostock → AKShare → Tencent
    """

    def __init__(self):
        self._tencent = TencentDataLoader()
        self._sina = SinaDataLoader()
        self._akshare = AKShareDataLoader()
        self._baostock = BaostockDataLoader()

    def _safe_call(self, func, *args, retries: int = 3, **kwargs):
        """带重试的安全调用"""
        import requests
        for i in range(retries):
            try:
                time.sleep(random.uniform(0.3, 1.0))
                return func(*args, **kwargs)
            except Exception as e:
                if i == retries - 1:
                    raise RuntimeError(f"数据源全部失败: {func.__class__.__name__} — {e}") from e

    # ── 实时行情 ──────────────────────────────────────────────────────────────

    def get_realtime_quotes(self, codes: list[str]) -> pd.DataFrame:
        """
        获取多只股票实时行情
        codes 格式: ['sh600519', 'sz000001']
        """
        # fallback 链: Tencent → Sina → AKShare
        for source_name, loader, method in [
            ('Tencent', self._tencent, self._tencent.fetch_realtime),
            ('Sina', self._sina, self._sina.fetch_realtime),
        ]:
            try:
                df = self._safe_call(method, codes)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                print(f"[{source_name}] 失败，切换下一源: {e}")
                continue

        # 最后 fallback: AKShare
        try:
            df = self._akshare.fetch_daily_all()
            if not df.empty:
                return df[df['ts_code'].isin([c[2:] for c in codes])]
        except Exception as e:
            print(f"[AKShare] 失败: {e}")

        raise RuntimeError("所有实时行情源均不可用")

    # ── 单股实时行情 ──────────────────────────────────────────────────────────

    def get_single_quote(self, ts_code: str) -> dict:
        """
        获取单只股票实时行情
        ts_code 格式: '000001.SZ' 或 '600519.SH'
        """
        market_map = {'SZ': 'sz', 'SH': 'sh'}
        market = market_map.get(ts_code.split('.')[-1], 'sz')
        symbol = ts_code.split('.')[0]
        qt_code = f"{market}{symbol}"

        for source_name, loader in [
            ('Tencent', self._tencent),
            ('Sina', self._sina),
        ]:
            try:
                df = self._safe_call(loader.fetch_realtime, [qt_code])
                if df is not None and not df.empty:
                    return df.iloc[0].to_dict()
            except Exception as e:
                print(f"[{source_name}] 失败: {e}")
                continue

        raise RuntimeError(f"无法获取 {ts_code} 实时行情")

    # ── 历史K线 ──────────────────────────────────────────────────────────────

    def get_historical(self, ts_code: str, start_date: str, end_date: str,
                       adjustflag: str = '2') -> pd.DataFrame:
        """
        获取历史日K线
        ts_code 格式: '000001.SZ' 或 '600519.SH'
        adjustflag: '1'=后复权, '2'=前复权, '3'=不复权
        """
        # fallback 链: Baostock → AKShare → Tencent
        for source_name, loader, method, extra_kwargs in [
            ('Baostock', self._baostock, self._baostock.fetch_historical,
             {'adjustflag': adjustflag}),
            ('AKShare', self._akshare, self._akshare.fetch_historical, {}),
        ]:
            try:
                df = self._safe_call(method, ts_code, start_date, end_date, **extra_kwargs)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                print(f"[{source_name}] 历史数据失败，切换: {e}")
                continue

        # 最后 fallback: Tencent
        try:
            market_map = {'SZ': 'sz', 'SH': 'sh'}
            market = market_map.get(ts_code.split('.')[-1], 'sz')
            qt_code = f"{market}{ts_code.split('.')[0]}"
            df = self._safe_call(self._tencent.fetch_historical, qt_code, 'day', 500)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[Tencent] 历史数据失败: {e}")

        raise RuntimeError(f"无法获取 {ts_code} 历史数据")

    # ── 全市场股票列表 ────────────────────────────────────────────────────────

    def get_stock_list(self) -> pd.DataFrame:
        """获取全市场A股列表"""
        for source_name, loader, method in [
            ('AKShare', self._akshare, self._akshare.fetch_daily_all),
            ('Baostock', self._baostock, self._baostock.fetch_stock_list),
        ]:
            try:
                df = self._safe_call(method)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                print(f"[{source_name}] 股票列表失败: {e}")
                continue
        raise RuntimeError("无法获取股票列表")

    # ── 行业板块数据 ─────────────────────────────────────────────────────────

    def get_industry_board(self) -> pd.DataFrame:
        """获取行业板块涨跌排行"""
        try:
            os.environ['NO_PROXY'] = '*'
            import akshare as ak
            return ak.stock_board_industry_name_em()
        except Exception as e:
            print(f"[AKShare] 行业板块失败: {e}")
            raise RuntimeError("无法获取行业板块数据")
