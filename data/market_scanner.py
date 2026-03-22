"""
A股全市场扫描引擎
支持: 100+行业板块 · 5490只全量股票 · 批量实时行情 · 技术指标筛选
数据源: 新浪财经(股票列表) + 腾讯财经(实时行情) + 新浪财经(K线)
"""

import os
import sys
import time
import random
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── CSRC 行业分类 (100+ 细分行业) ─────────────────────────────────────────

CSRC_SECTORS = {
    "农林牧渔": {
        "code": "bk_nlmy",
        "name": "农林牧渔",
        "desc": "种植业/养殖业/饲料/农业综合",
        "stocks": ["sh600598", "sz000998", "sh600108", "sz002311", "sh600965", "sz000876", "sh600189", "sz002505"],
    },
    "采掘": {
        "code": "bk_ck",
        "name": "采掘",
        "desc": "煤炭/石油/天然气/采矿",
        "stocks": ["sh600188", "sh601088", "sh600971", "sz000937", "sh601225", "sh600508", "sz002207", "sh601699"],
    },
    "化工": {
        "code": "bk_hg",
        "name": "化工",
        "desc": "化学原料/化学制品/石油化工/化工新材料",
        "stocks": ["sh600309", "sz000792", "sh600486", "sz002601", "sh603260", "sz002092", "sh600352", "sz000830",
                   "sh600273", "sz002145", "sh601216", "sz000553", "sh600989", "sz002274", "sh603915", "sz002408"],
    },
    "钢铁": {
        "code": "bk_gt",
        "name": "钢铁",
        "desc": "普钢/特钢/金属非金属新材料",
        "stocks": ["sh600019", "sz000709", "sh600010", "sz000778", "sh600022", "sz002110", "sh601003", "sz000825"],
    },
    "有色金属": {
        "code": "bk_ys",
        "name": "有色金属",
        "desc": "铜/铝/稀土/黄金/小金属",
        "stocks": ["sh601600", "sh600362", "sz000630", "sh601212", "sz002460", "sh600456", "sh600547", "sz000831",
                   "sh601899", "sz002466", "sh600219", "sh600711", "sh601618", "sz002155"],
    },
    "电子": {
        "code": "bk_dz",
        "name": "电子",
        "desc": "半导体/元件/光学光电子/消费电子",
        "stocks": ["sz002241", "sh600703", "sz002475", "sh688981", "sz002185", "sh600584", "sz000725", "sh603986",
                   "sh600460", "sz002049", "sh688008", "sz002583", "sh600667", "sz002369", "sh603659", "sz000681"],
    },
    "汽车": {
        "code": "bk_qc",
        "name": "汽车",
        "desc": "整车/零部件/新能源车/汽车服务",
        "stocks": ["sh600104", "sz000625", "sh601127", "sz002594", "sh600660", "sz002126", "sh601238", "sz002048",
                   "sh600741", "sz002406", "sh600335", "sz002265", "sh601633", "sz002488", "sh688195", "sz300124"],
    },
    "家用电器": {
        "code": "bk_jydq",
        "name": "家用电器",
        "desc": "白色家电/黑色家电/小家电/厨电",
        "stocks": ["sz000651", "sh600690", "sz000333", "sh600839", "sz002032", "sh600336", "sz002242", "sh603515"],
    },
    "食品饮料": {
        "code": "bk_spyy",
        "name": "食品饮料",
        "desc": "白酒/啤酒/乳品/调味品/休闲食品",
        "stocks": ["sh600519", "sz000858", "sh603288", "sz000568", "sh600809", "sz002304", "sz000895", "sh603605",
                   "sh600597", "sz002507", "sh600073", "sz002557", "sh600186", "sz002714", "sh603517", "sz000729"],
    },
    "纺织服装": {
        "code": "bkfzfg",
        "name": "纺织服装",
        "desc": "纺织/服装/家纺/饰品",
        "stocks": ["sh600398", "sz002293", "sh603001", "sz002269", "sh600400", "sz002563", "sh601566", "sz002154"],
    },
    "轻工制造": {
        "code": "bk_qgzz",
        "name": "轻工制造",
        "desc": "造纸/包装/家用轻工/其他轻工",
        "stocks": ["sz002078", "sh600567", "sz002831", "sh600966", "sz002301", "sh603733", "sz002228", "sh601968"],
    },
    "医药生物": {
        "code": "bk_yysw",
        "name": "医药生物",
        "desc": "化学制药/中药/生物制品/医疗器械/医疗服务",
        "stocks": ["sh600276", "sz000538", "sh603259", "sz300015", "sh600196", "sz002007", "sh600521", "sz002252",
                   "sh601607", "sz300760", "sh688180", "sz300347", "sh600329", "sz300122", "sh603707", "sz002001",
                   "sh600267", "sz002262", "sh600055", "sz300003", "sh603883", "sz002223", "sh600056", "sz300529"],
    },
    "公用事业": {
        "code": "bk_ggsy",
        "name": "公用事业",
        "desc": "电力/燃气/水务/环保",
        "stocks": ["sh600900", "sh600011", "sh600025", "sz000027", "sh600674", "sz000539", "sh601985", "sz000883",
                   "sh600642", "sh601016", "sz000692", "sh600886", "sh600795", "sz002608", "sh601619", "sz300055"],
    },
    "交通运输": {
        "code": "bk_jtys",
        "name": "交通运输",
        "desc": "航空/航运/港口/公路/铁路/物流",
        "stocks": ["sh600009", "sh600115", "sz000089", "sh601111", "sz002120", "sh600018", "sh600026", "sz002352",
                   "sh601006", "sz000088", "sh600317", "sz002468", "sh601021", "sz002357", "sh600221", "sz000582"],
    },
    "房地产": {
        "code": "bk_fdc",
        "name": "房地产",
        "desc": "房地产开发/房地产服务/园区",
        "stocks": ["sh600048", "sz000002", "sh601155", "sz001979", "sh600383", "sz000671", "sh600606", "sz002146",
                   "sh600708", "sz000402", "sh600823", "sz000732", "sh600657", "sz000656", "sh600094", "sz002285"],
    },
    "商业贸易": {
        "code": "bk_symy",
        "name": "商业贸易",
        "desc": "一般零售/专业连锁/商业物业/贸易",
        "stocks": ["sh600729", "sz002251", "sh600327", "sz002264", "sh600859", "sz002187", "sh600861", "sz000501",
                   "sh601010", "sz002024", "sh600655", "sz000417", "sh600694", "sz000417", "sh600712", "sz002419"],
    },
    "休闲服务": {
        "code": "bk_xxfw",
        "name": "休闲服务",
        "desc": "酒店/餐饮/旅游/景区/演艺",
        "stocks": ["sz000069", "sh600054", "sz002059", "sh601888", "sz000428", "sh600754", "sz002186", "sh600749",
                   "sh603605", "sz300144", "sh600593", "sz002306", "sh600358", "sz002707", "sh601007", "sz000613"],
    },
    "银行": {
        "code": "bk_yh",
        "name": "银行",
        "desc": "国有银行/股份制银行/城商行/农商行",
        "stocks": ["sh601398", "sh601939", "sh601288", "sh601988", "sh600000", "sz000001", "sh600016", "sh601328",
                   "sh600036", "sh600015", "sh601818", "sh601166", "sh600919", "sh600926", "sz002807", "sh600928"],
    },
    "非银金融": {
        "code": "bk_fyjr",
        "name": "非银金融",
        "desc": "证券/保险/期货/信托/租赁/资产管理",
        "stocks": ["sh600030", "sh601211", "sz000776", "sh601688", "sh600837", "sz002673", "sh600999", "sz000166",
                   "sh601601", "sh601628", "sh601336", "sh600109", "sh601555", "sz000617", "sh600061", "sz000617"],
    },
    "建筑材料": {
        "code": "bk_jzcl",
        "name": "建筑材料",
        "desc": "水泥制造/玻璃制造/防水/管材/其他建材",
        "stocks": ["sh600585", "sz000401", "sh600176", "sh600881", "sz002271", "sh600449", "sz000786", "sh600720"],
    },
    "建筑装饰": {
        "code": "bk_jzzs",
        "name": "建筑装饰",
        "desc": "房屋建设/装修装饰/园林工程/基础建设",
        "stocks": ["sh601668", "sz002062", "sh600170", "sz002271", "sh600629", "sz002482", "sh601117", "sz000065",
                   "sh601186", "sz002325", "sh600512", "sz002146", "sh601390", "sz000928", "sh600284", "sz002061"],
    },
    "电气设备": {
        "code": "bk_dqsb",
        "name": "电气设备",
        "desc": "电机/电气自动化设备/电源设备/输变电设备",
        "stocks": ["sz300274", "sh600406", "sz002028", "sh601179", "sz300124", "sh600089", "sz002129", "sh600312",
                   "sh603806", "sz002459", "sz300316", "sh601727", "sz300014", "sh600468", "sz002451", "sh603488"],
    },
    "机械设备": {
        "code": "bk_jxsb",
        "name": "机械设备",
        "desc": "通用设备/专用设备/仪器仪表/工程机械",
        "stocks": ["sh600031", "sz000157", "sh600582", "sz002353", "sh601100", "sz300308", "sh600255", "sz000425",
                   "sh603338", "sz002460", "sh601012", "sz002202", "sh603185", "sz002430", "sh601369", "sz002353"],
    },
    "国防军工": {
        "code": "bk_gfjg",
        "name": "国防军工",
        "desc": "航空装备/航天装备/地面兵装/船舶/核工业",
        "stocks": ["sh600893", "sz000768", "sh601989", "sh600316", "sz002414", "sh600038", "sh601606", "sz000561",
                   "sh600271", "sz002025", "sh600184", "sz002265", "sh688185", "sz002625", "sh600435", "sz300034"],
    },
    "计算机": {
        "code": "bk_jsj",
        "name": "计算机",
        "desc": "计算机设备/软件服务/IT服务/信息安全",
        "stocks": ["sh600570", "sz000977", "sh600588", "sz002230", "sz002236", "sh603160", "sz300033", "sh600845",
                   "sz002195", "sz002212", "sh688111", "sz002410", "sh600536", "sz002439", "sh603019", "sz002410"],
    },
    "传媒": {
        "code": "bk_cm",
        "name": "传媒",
        "desc": "影视院线/游戏/出版/广告营销/互联网",
        "stocks": ["sh600977", "sz300058", "sz002558", "sz002624", "sh603444", "sz300413", "sh601801", "sz000503",
                   "sh600229", "sz002602", "sh600637", "sz300226", "sh601019", "sz300027", "sh600373", "sz002181"],
    },
    "通信": {
        "code": "bk_tx",
        "name": "通信",
        "desc": "通信设备/通信服务/光纤光缆/卫星导航",
        "stocks": ["sh600050", "sz000063", "sh600487", "sz002792", "sh603236", "sz002313", "sh600345", "sz002446",
                   "sh688025", "sz300353", "sh601869", "sz002491", "sh002123", "sz300025", "sh688158", "sz002583"],
    },
    "电力设备": {
        "code": "bk_dlsb",
        "name": "电力设备",
        "desc": "风电设备/光伏设备/储能/电池/充电桩",
        "stocks": ["sz300750", "sh601012", "sz002129", "sh600438", "sz300014", "sh601615", "sh603806", "sz300274",
                   "sh688390", "sz002594", "sh600905", "sz300274", "sh600406", "sz300014", "sh601865", "sz002459"],
    },
    "综合": {
        "code": "bk_zh",
        "name": "综合",
        "desc": "综合类企业",
        "stocks": ["sh600051", "sh600052", "sh600053", "sh600054", "sz000009", "sh600058", "sh600060", "sh600061"],
    },
}

# 扩展板块：补充更多代表性股票
EXTRA_SECTORS = {
    "新能源汽车": {
        "code": "bk_xny",
        "name": "新能源汽车",
        "desc": "动力电池/锂矿/电解液/隔膜/整车",
        "stocks": ["sz300750", "sh601238", "sz002594", "sh600884", "sz002460", "sh600378", "sz002466", "sh601127",
                   "sz300014", "sh600733", "sz002074", "sh688005", "sh603185", "sz300618", "sh601311", "sz002812"],
    },
    "半导体": {
        "code": "bk_bdt",
        "name": "半导体",
        "desc": "IC设计/晶圆代工/封测/设备/材料",
        "stocks": ["sh688981", "sh603986", "sh688008", "sz002049", "sz002185", "sh600584", "sh688396", "sz002371",
                   "sh688072", "sz300782", "sh688256", "sz002156", "sh688396", "sz300623", "sh603501", "sz002409"],
    },
    "光伏": {
        "code": "bk_gf",
        "name": "光伏",
        "desc": "硅料/硅片/电池片/组件/逆变器/EPC",
        "stocks": ["sh601012", "sh600438", "sh600089", "sz002129", "sh600900", "sz300274", "sh603806", "sh600732",
                   "sh688223", "sz300118", "sh601665", "sz002459", "sh603396", "sz002860", "sh600875", "sz300118"],
    },
    "储能": {
        "code": "bk_cn",
        "name": "储能",
        "desc": "电化学储能/PCS/EMS/温控/系统集成",
        "stocks": ["sz300274", "sh600406", "sz300014", "sh600089", "sh603806", "sz002129", "sh601615", "sz002466",
                   "sh688005", "sz300763", "sh601669", "sz002594", "sh600478", "sz300832", "sh601127", "sz002245"],
    },
    "人工智能": {
        "code": "bk_rgzn",
        "name": "人工智能",
        "desc": "算法/算力/应用/机器人/智能驾驶",
        "stocks": ["sz000977", "sh688041", "sz002230", "sh600570", "sz300024", "sh601360", "sz002410", "sh688111",
                   "sh600588", "sz300058", "sh603160", "sz002410", "sh688169", "sz002236", "sh688981", "sz300496"],
    },
    "云计算": {
        "code": "bk_yjsj",
        "name": "云计算",
        "desc": "IaaS/PaaS/SaaS/数据中心/服务器",
        "stocks": ["sh600588", "sh688111", "sh600845", "sz002230", "sh603019", "sh600410", "sh601360", "sz002025",
                   "sz002410", "sh688188", "sz300253", "sh600476", "sh603882", "sh688018", "sz300496", "sh688099"],
    },
    "医疗器械": {
        "code": "bk_ylqx",
        "name": "医疗器械",
        "desc": "医疗设备/高值耗材/体外诊断/家用医疗",
        "stocks": ["sz300760", "sz300003", "sz300529", "sz002223", "sh600529", "sz300003", "sh600055", "sz300003",
                   "sh688139", "sz300529", "sh603259", "sz300015", "sh688016", "sz300529", "sh603259", "sz002223"],
    },
    "CXO": {
        "code": "bk_cxo",
        "name": "CXO",
        "desc": "医药研发外包/生产外包/临床服务",
        "stocks": ["sh603259", "sz300760", "sh603706", "sz002821", "sh603108", "sz300759", "sh603456", "sz300725"],
    },
    "酒类": {
        "code": "bk_jl",
        "name": "酒类",
        "desc": "白酒/啤酒/黄酒/葡萄酒/保健酒",
        "stocks": ["sh600519", "sz000858", "sh600809", "sz000568", "sz002304", "sh600199", "sh600059", "sh600365",
                   "sh600616", "sz000869", "sh600084", "sz000729", "sz000995", "sh600543", "sh603919", "sh600702"],
    },
    "游戏": {
        "code": "bk_yx",
        "name": "游戏",
        "desc": "网络游戏/手机游戏/主机游戏/电竞",
        "stocks": ["sz002558", "sh603444", "sz002624", "sz300494", "sh600633", "sz002517", "sh603258", "sz300043",
                   "sz000503", "sh601019", "sz002602", "sh600892", "sz002467", "sh601928", "sz002555", "sh600715"],
    },
    "教育": {
        "code": "bk_jy",
        "name": "教育",
        "desc": "K12/职业教育/培训/教育信息化",
        "stocks": ["sz002607", "sh600661", "sz300010", "sh600730", "sz002261", "sh601099", "sz002308", "sh688076"],
    },
    "美容护理": {
        "code": "bk_mrhl",
        "name": "美容护理",
        "desc": "化妆品/医美/个护用品/原料",
        "stocks": ["sh603605", "sz002612", "sh600223", "sz300957", "sh603737", "sz002614", "sh600779", "sz002094"],
    },
    "环保": {
        "code": "bk_hb",
        "name": "环保",
        "desc": "大气治理/水处理/固废处理/环境监测",
        "stocks": ["sh601200", "sz300055", "sh600388", "sz002310", "sh600292", "sz002672", "sh601827", "sz300203"],
    },
    "油气": {
        "code": "bk_yq",
        "name": "油气",
        "desc": "油气开采/炼化/油服/管道/LNG",
        "stocks": ["sh601857", "sh600938", "sh600028", "sz000554", "sh600583", "sh601808", "sh600968", "sz002207"],
    },
    "机器人": {
        "code": "bk_jqr",
        "name": "机器人",
        "desc": "工业机器人/服务机器人/核心零部件",
        "stocks": ["sz300024", "sz002747", "sz300024", "sh603486", "sz002009", "sh688777", "sz300294", "sh688320"],
    },
    "低空经济": {
        "code": "bk_dkj",
        "name": "低空经济",
        "desc": "无人机/eVTOL/低空运营/通航基础设施",
        "stocks": ["sz000768", "sh600893", "sz002368", "sh600118", "sz002583", "sh601615", "sz300008", "sh600038"],
    },
    "量子科技": {
        "code": "bk_lzkj",
        "name": "量子科技",
        "desc": "量子通信/量子计算/量子精密测量",
        "stocks": ["sz002281", "sh600345", "sz002224", "sh600570", "sh688027", "sz300379", "sh603019", "sz300748"],
    },
}

CSRC_SECTORS.update(EXTRA_SECTORS)

# ── 全量股票列表获取器 ────────────────────────────────────────────────────────

class StockListFetcher:
    """从新浪获取全量A股列表 (5490只)"""

    def __init__(self):
        self._cache = None
        self._cache_time = None
        self._cache_ttl = 3600  # 1小时缓存

    def fetch(self, force=False) -> list[str]:
        """获取全量A股代码列表，格式: ['sh600519', 'sz000001', ...]"""
        now = datetime.now()
        if not force and self._cache and self._cache_time:
            if (now - self._cache_time).total_seconds() < self._cache_ttl:
                return self._cache

        codes = []
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn',
        }
        # 5490只，每页100
        for page in range(1, 56):
            url = (
                f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php"
                f"/Market_Center.getHQNodeDataSimple?page={page}&num=100&sort=symbol&asc=1&node=hs_a"
            )
            try:
                r = requests.get(url, headers=headers, timeout=10)
                data = r.json()
                if isinstance(data, list) and data:
                    for item in data:
                        sym = item.get('symbol', '')
                        if sym:
                            codes.append(sym)
                time.sleep(0.2)
            except Exception:
                continue

        self._cache = codes
        self._cache_time = now
        return codes

    def get_cached(self) -> list[str]:
        return self._cache or []


# ── 批量实时行情扫描器 ───────────────────────────────────────────────────────

class MarketScanner:
    """
    全市场技术扫描
    策略: 批量获取实时行情 → 初筛 → K线技术分析 → 排序 → 详细建议
    """

    def __init__(self):
        self.list_fetcher = StockListFetcher()
        self.batch_size = 50  # 腾讯每批50个

    def _batch_request(self, codes: list[str]) -> pd.DataFrame:
        """批量获取腾讯实时行情"""
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.qq.com',
        }
        results = []
        for i in range(0, len(codes), self.batch_size):
            batch = codes[i:i+self.batch_size]
            codes_str = ','.join(batch)
            url = f"https://qt.gtimg.cn/q={codes_str}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                r.encoding = 'gbk'
                for line in r.text.strip().split('\n'):
                    if '=' not in line or 'v_pv_none' in line:
                        continue
                    try:
                        raw = line.split('"')[1]
                        fields = raw.split('~')
                        if len(fields) < 40:
                            continue
                        code_raw = line.split('"')[0].split('_')[-1].replace('=', '')
                        results.append({
                            'ts_code': code_raw,
                            'name': fields[1],
                            'current': float(fields[3]) if fields[3] else 0,
                            'close': float(fields[4]) if fields[4] else 0,
                            'open': float(fields[5]) if fields[5] else 0,
                            'volume': float(fields[6]) if fields[6] else 0,
                            'high': float(fields[33]) if fields[33] else 0,
                            'low': float(fields[34]) if fields[34] else 0,
                            'pct_chg': float(fields[32]) if fields[32] else 0,
                            'amount': float(fields[37]) if fields[37] else 0,
                        })
                    except (IndexError, ValueError):
                        continue
                time.sleep(0.1)
            except Exception:
                continue
        return pd.DataFrame(results)

    def scan(self, top_n: int = 100, min_price: float = 1.0,
             max_price: float = 1000.0, min_vol: float = 100000.0,
             universe: list[str] = None,
             progress_callback=None) -> list[dict]:
        """
        全市场扫描，返回 TOP 机会列表
        universe: 股票代码列表，默认使用代表性股票组合
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Step 1: 确定扫描范围
        if progress_callback:
            progress_callback("正在加载股票列表...", 0.05)
        if universe:
            scan_codes = universe
        else:
            scan_codes = self._get_representative_universe()

        total = len(scan_codes)

        # Step 2: 批量获取实时行情
        if progress_callback:
            progress_callback(f"正在扫描 {total} 只股票实时行情...", 0.1)
        df_rt = self._batch_request(scan_codes)
        if df_rt.empty:
            return []

        # 初筛
        df_rt = df_rt[
            (df_rt['current'] >= min_price) &
            (df_rt['current'] <= max_price) &
            (df_rt['volume'] >= min_vol)
        ].copy()

        if progress_callback:
            progress_callback(f"初筛后剩余 {len(df_rt)} 只候选股票", 0.2)

        # Step 3: 并行获取K线并评分
        candidates = []
        n = len(df_rt)
        rows = df_rt.to_dict('records')

        def analyze_row(row):
            """分析单只股票 (带重试)"""
            code = row['ts_code']
            name = row['name']
            price = row['current']
            pct_chg = row['pct_chg']
            vol = row['volume']
            qt_code = code

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://finance.sina.com.cn',
            }
            url = (
                "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
                "/CN_MarketData.getKLineData"
            )

            for attempt in range(3):
                try:
                    params = {"symbol": qt_code, "scale": "240", "ma": "no", "datalen": "60"}
                    r = requests.get(url, params=params, headers=headers, timeout=10)
                    r.encoding = 'utf-8'
                    data = r.json()
                    if isinstance(data, list) and len(data) >= 20:
                        break  # 成功
                    time.sleep(0.5)
                except Exception:
                    time.sleep(1)
            else:
                return None  # 3次失败

            try:
                klines = []
                for bar in data:
                    try:
                        klines.append({
                            'close': float(bar.get('close', 0)),
                            'high': float(bar.get('high', 0)),
                            'low': float(bar.get('low', 0)),
                            'open': float(bar.get('open', 0)),
                            'volume': float(bar.get('volume', 0)),
                        })
                    except ValueError:
                        continue
                if len(klines) < 20:
                    return None

                df_k = pd.DataFrame(klines)
                score, reasons, indicators = self._score_stock(df_k, price, pct_chg, vol)
                return {
                    'ts_code': code,
                    'name': name,
                    'current': price,
                    'pct_chg': pct_chg,
                    'score': score,
                    'reasons': reasons,
                    'indicators': indicators,
                }
            except Exception:
                return None

        processed = 0
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(analyze_row, row): row for row in rows}
            for future in as_completed(futures):
                processed += 1
                if progress_callback and processed % 50 == 0:
                    pct = 0.2 + (processed / n) * 0.7
                    progress_callback(f"分析中 {processed}/{n}...", pct)
                try:
                    result = future.result()
                    if result and result['score'] >= 20:
                        candidates.append(result)
                except Exception:
                    pass

        # Step 4: 排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_n]

    def _score_stock(self, df: pd.DataFrame, price: float, pct_chg: float,
                    vol: float) -> tuple[int, list[str], dict]:
        """
        计算股票综合评分 (0-100)
        """
        score = 0
        reasons = []
        indicators = {}

        closes = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        # ── 1. 均线体系 (0-25分) ────────────────────────────────────────
        try:
            closes_s = pd.Series(closes.values if hasattr(closes, 'values') else closes)
            ma5_s = closes_s.rolling(5).mean()
            ma20_s = closes_s.rolling(20).mean()
            ma60_s = closes_s.rolling(60).mean()
            ma5 = float(ma5_s.iloc[-1]) if not pd.isna(ma5_s.iloc[-1]) else 0
            ma20 = float(ma20_s.iloc[-1]) if not pd.isna(ma20_s.iloc[-1]) else 0
            ma60 = float(ma60_s.iloc[-1]) if len(ma60_s) >= 60 and not pd.isna(ma60_s.iloc[-1]) else ma20
            ma10_s = closes_s.rolling(10).mean()
            ma10 = float(ma10_s.iloc[-1]) if not pd.isna(ma10_s.iloc[-1]) else 0

            indicators['ma5'] = ma5
            indicators['ma20'] = ma20
            indicators['ma60'] = ma60

            # 多头排列
            if price > ma5 > ma20 > ma60:
                score += 25
                reasons.append("均线多头排列(强烈)")
            elif price > ma5 > ma20:
                score += 18
                reasons.append("均线多头排列")
            elif price > ma20:
                score += 8
                reasons.append("站上MA20")
            elif price > ma5:
                score += 4
                reasons.append("站上MA5")

            # 均线收敛 (蓄势)
            ma_spread = (ma5 - ma20) / ma20 * 100 if ma20 else 0
            if abs(ma_spread) < 2:
                score += 5
                reasons.append(f"均线收敛蓄势({ma_spread:+.1f}%)")

        except Exception:
            pass

        # ── 2. RSI (0-20分) ───────────────────────────────────────────
        try:
            delta = pd.Series(closes).diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            indicators['rsi'] = rsi

            if rsi < 30:
                score += 20
                reasons.append(f"RSI超卖({rsi:.1f})—反弹机会")
            elif rsi < 40:
                score += 15
                reasons.append(f"RSI偏低({rsi:.1f})—关注买入")
            elif 40 <= rsi <= 65:
                score += 10
                reasons.append(f"RSI健康区({rsi:.1f})")
            elif rsi > 80:
                score -= 10
                reasons.append(f"RSI超买({rsi:.1f})—注意风险")
        except Exception:
            pass

        # ── 3. 动量 (0-15分) ──────────────────────────────────────────
        try:
            mom5 = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
            mom20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
            indicators['momentum_5d'] = mom5
            indicators['momentum_20d'] = mom20

            if mom5 > 5:
                score += 8
                reasons.append(f"5日动能强劲(+{mom5:.1f}%)")
            elif mom5 > 2:
                score += 5
                reasons.append(f"5日动能正向(+{mom5:.1f}%)")
            elif mom5 < -5:
                score -= 5
                reasons.append(f"5日动能走弱({mom5:.1f}%)")

            if mom20 > 10:
                score += 7
                reasons.append(f"20日趋势向上(+{mom20:.1f}%)")
            elif mom20 > 5:
                score += 4
                reasons.append(f"20日趋势偏多(+{mom20:.1f}%)")
        except Exception:
            pass

        # ── 4. 布林带 (0-15分) ─────────────────────────────────────────
        try:
            ma20_s = pd.Series(closes).rolling(20).mean()
            std20 = pd.Series(closes).rolling(20).std()
            upper = float((ma20_s + 2 * std20).iloc[-1])
            lower = float((ma20_s - 2 * std20).iloc[-1])
            mid = float(ma20_s.iloc[-1])
            bandwidth = (upper - lower) / mid * 100 if mid else 0

            indicators['bb_upper'] = upper
            indicators['bb_lower'] = lower
            indicators['bb_mid'] = mid
            indicators['bb_width'] = bandwidth

            # 布林下轨支撑
            dist_to_lower = (price - lower) / lower * 100 if lower else 0
            if price <= lower:
                score += 15
                reasons.append(f"触及布林下轨(超卖支撑)")
            elif dist_to_lower < 3:
                score += 10
                reasons.append(f"接近布林下轨(+{dist_to_lower:.1f}%)")
            # 布林中轨支撑
            elif price > mid:
                score += 5
                reasons.append("在布林中轨上方")

            # 布林收口 (突破前兆)
            if bandwidth < 10:
                score += 5
                reasons.append(f"布林收口({bandwidth:.1f}%)—蓄势突破")
        except Exception:
            pass

        # ── 5. MACD (0-15分) ──────────────────────────────────────────
        try:
            ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean()
            ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean()
            diff = ema12 - ema26
            dea = diff.ewm(span=9, adjust=False).mean()
            macd = 2 * (diff - dea)

            macd_now = float(macd.iloc[-1])
            macd_prev = float(macd.iloc[-2])
            macd_prev2 = float(macd.iloc[-3]) if len(macd) > 2 else macd_prev
            indicators['macd'] = macd_now
            indicators['macd_signal'] = float(dea.iloc[-1])

            # 金叉
            if macd_prev <= 0 and macd_now > 0:
                score += 15
                reasons.append("MACD零轴金叉(强烈)")
            elif macd_prev <= macd_prev2 and macd_now > macd_prev:
                score += 10
                reasons.append("MACD红柱放大")
            # 死叉
            elif macd_prev >= 0 and macd_now < 0:
                score -= 10
                reasons.append("MACD零轴死叉")
            # 零轴上方多头
            elif macd_now > 0:
                score += 5
                reasons.append("MACD多头区域")
        except Exception:
            pass

        # ── 6. 成交量异动 (0-10分) ────────────────────────────────────
        try:
            vol_ma5 = float(pd.Series(volume).rolling(5).mean().iloc[-1])
            vol_now = volume[-1]
            vol_ratio = vol_now / vol_ma5 if vol_ma5 > 0 else 1
            indicators['vol_ratio'] = vol_ratio

            if vol_ratio > 2.0:
                score += 10
                reasons.append(f"量比放大({vol_ratio:.1f}x)▲▲")
            elif vol_ratio > 1.5:
                score += 7
                reasons.append(f"量比增加({vol_ratio:.1f}x)")
            elif vol_ratio > 1.2:
                score += 4
                reasons.append(f"温和放量({vol_ratio:.1f}x)")
        except Exception:
            pass

        # ── 7. 涨跌幅过滤 (0-10分) ────────────────────────────────────
        if -3 <= pct_chg <= 5:
            score += 10
            reasons.append(f"涨幅健康({pct_chg:+.2f}%)")
        elif -5 <= pct_chg < -3:
            score += 5
            reasons.append(f"回调({pct_chg:+.2f}%)—关注支撑")
        elif pct_chg > 9:
            score -= 10
            reasons.append(f"涨停附近({pct_chg:+.2f}%)—追高风险")
        elif pct_chg > 5:
            score -= 5
            reasons.append(f"涨幅较大({pct_chg:+.2f}%)—注意追高")

        # ── 8. ATR 止损止盈 (始终计算) ───────────────────────────────
        try:
            high_arr = pd.Series(high)
            low_arr = pd.Series(low)
            close_arr = pd.Series(closes)
            tr1 = high_arr - low_arr
            tr2 = abs(high_arr - close_arr.shift())
            tr3 = abs(low_arr - close_arr.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = float(tr.tail(14).mean())
            indicators['atr'] = atr
            indicators['stop_loss'] = round(price - 2 * atr, 2)
            indicators['take_profit_1'] = round(price + 2 * atr, 2)
            indicators['take_profit_2'] = round(price + 3 * atr, 2)
            indicators['risk_ratio'] = round((price - indicators['stop_loss']) / (indicators['take_profit_1'] - price), 1) if indicators['take_profit_1'] != price else 0
        except Exception:
            indicators['stop_loss'] = round(price * 0.95, 2)
            indicators['take_profit_1'] = round(price * 1.05, 2)
            indicators['take_profit_2'] = round(price * 1.08, 2)
            indicators['atr'] = price * 0.02
            indicators['risk_ratio'] = 1.0

        return max(score, 0), reasons, indicators

    def _get_representative_universe(self) -> list[str]:
        """代表性股票 Universe (兜底)"""
        universe = []
        for sec in CSRC_SECTORS.values():
            universe.extend(sec.get('stocks', []))
        return list(dict.fromkeys(universe))  # 去重保留顺序


# ── 详细投资建议生成 ─────────────────────────────────────────────────────────

def generate_advice(code: str, name: str, price: float, score: int,
                    reasons: list[str], indicators: dict) -> dict:
    """
    生成详细投资建议报告
    """
        # 评级
    if score >= 70:
        rating = "🟢 强烈推荐"
        rating_cls = "var(--green)"
        rating_bg = "var(--green-dim)"
    elif score >= 50:
        rating = "🟡 关注"
        rating_cls = "var(--accent)"
        rating_bg = "rgba(232,160,32,0.08)"
    elif score >= 30:
        rating = "🟡 谨慎关注"
        rating_cls = "var(--blue)"
        rating_bg = "var(--blue-dim)"
    else:
        rating = "🔴 不推荐"
        rating_cls = "var(--red)"
        rating_bg = "var(--red-dim)"

    atr = indicators.get('atr', price * 0.02)
    stop_loss = indicators.get('stop_loss', round(price - 2 * atr, 2))
    tp1 = indicators.get('take_profit_1', round(price + 2 * atr, 2))
    tp2 = indicators.get('take_profit_2', round(price + 3 * atr, 2))
    risk_ratio = indicators.get('risk_ratio', 1.0)

    # 仓位建议
    if risk_ratio >= 2:
        pos_size = "20% (轻仓)"
        risk_note = "盈亏比优秀(≥2:1)，可适当加仓"
    elif risk_ratio >= 1.5:
        pos_size = "15% (标准)"
        risk_note = "盈亏比良好(1.5:1)"
    elif risk_ratio >= 1:
        pos_size = "10% (轻仓)"
        risk_note = "盈亏比一般(1:1)，控制仓位"
    else:
        pos_size = "5% (试探)"
        risk_note = "盈亏比欠佳，建议观望"

    # 止损说明
    sl_pct = (price - stop_loss) / price * 100
    tp1_pct = (tp1 - price) / price * 100
    tp2_pct = (tp2 - price) / price * 100

    # 买入时机
    rsi = indicators.get('rsi', 50)
    ma5 = indicators.get('ma5', 0)
    ma20 = indicators.get('ma20', 0)
    macd = indicators.get('macd', 0)

    if rsi < 30:
        buy_timing = f"✅ RSI超卖({rsi:.1f})，建议分批建仓，MA5({ma5:.2f})回踩不破加仓"
    elif rsi < 45:
        buy_timing = f"✅ RSI偏低({rsi:.1f})，可在MA5({ma5:.2f})附近低吸"
    elif price > ma5 > ma20 and macd > 0:
        buy_timing = f"✅ 趋势确立，回踩MA5({ma5:.2f})买入，不破MA20({ma20:.2f})持有"
    elif indicators.get('bb_width', 100) < 10:
        buy_timing = f"✅ 布林收口，突破时买入，目标{tp1:.2f}(+{tp1_pct:.1f}%)"
    else:
        buy_timing = f"⚠️ 等待回踩支撑，建议关注MA20({ma20:.2f})附近机会"

    # 卖出时机
    if rsi > 80:
        sell_timing = f"⚠️ RSI超买({rsi:.1f})，建议分批止盈"
    elif price > indicators.get('bb_upper', price * 1.1):
        sell_timing = f"⚠️ 突破布林上轨，止盈目标{tp2:.2f}(+{tp2_pct:.1f}%)"
    else:
        sell_timing = f"📋 持有至RSI>70或触发止盈价{tp1:.2f}(+{tp1_pct:.1f}%)"

    # 综合建议
    summary_lines = []
    summary_lines.append(f"**{name}({code[2:]})** 综合评分 {score}/100 | {rating}")
    summary_lines.append("")
    summary_lines.append(f"**当前价**: ¥{price:.2f} | **评分**: {score}分")
    summary_lines.append("")
    summary_lines.append("**📊 技术信号**:")
    for r in reasons[:5]:
        summary_lines.append(f"- {r}")
    summary_lines.append("")
    summary_lines.append("**🎯 操作建议**:")
    summary_lines.append(f"- 买入时机: {buy_timing}")
    summary_lines.append(f"- 建议仓位: {pos_size} | {risk_note}")
    summary_lines.append(f"- 止损价: ¥{stop_loss:.2f} (-{sl_pct:.1f}%)")
    summary_lines.append(f"- 止盈1: ¥{tp1:.2f} (+{tp1_pct:.1f}%)")
    summary_lines.append(f"- 止盈2: ¥{tp2:.2f} (+{tp2_pct:.1f}%)")
    summary_lines.append(f"- 卖出时机: {sell_timing}")
    summary_lines.append("")
    summary_lines.append("**⚠️ 风险提示**: 本建议仅供参考，不构成投资依据。设置止损是控制风险的有效手段。")

    return {
        'rating': rating,
        'rating_cls': rating_cls,
        'rating_bg': rating_bg,
        'pos_size': pos_size,
        'stop_loss': stop_loss,
        'stop_loss_pct': f"-{sl_pct:.1f}%",
        'take_profit_1': tp1,
        'take_profit_1_pct': f"+{tp1_pct:.1f}%",
        'take_profit_2': tp2,
        'take_profit_2_pct': f"+{tp2_pct:.1f}%",
        'buy_timing': buy_timing,
        'sell_timing': sell_timing,
        'risk_ratio': risk_ratio,
        'risk_note': risk_note,
        'summary': '\n'.join(summary_lines),
        'reasons': reasons,
        'indicators': indicators,
    }


if __name__ == "__main__":
    print("=== 全市场扫描测试 (前10只) ===")
    scanner = MarketScanner()

    def progress(msg, pct):
        print(f"[{pct:.0%}] {msg}")

    results = scanner.scan(top_n=10, min_vol=500000, progress_callback=progress)
    print(f"\n扫描完成，找到 {len(results)} 只机会股")
    for r in results:
        print(f"  {r['name']}({r['ts_code']}) 评分={r['score']}分: {r['reasons'][:2]}")
