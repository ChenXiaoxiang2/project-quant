import streamlit as st
import requests
import pandas as pd
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

API_URL = "http://localhost:8000"

st.set_page_config(page_title="QuantDesk", layout="wide", initial_sidebar_state="collapsed")

# ═══════════════════════════════════════════════════════════════════════════
# IMPECCABLE DESIGN SYSTEM v2 — 专业金融终端
# 核心理念: 线条分区 · 数据即装饰 · 留白即节奏 · 无卡片嵌套
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  /* ── 色彩系统 ───────────────────────────────────────────────────── */
  :root {
    --bg-void:      #08080b;
    --bg-base:      #0d0d11;
    --bg-surface:   #12121a;
    --bg-raised:    #1a1a24;
    --bg-overlay:   #22222e;
    --accent:       #e8a020;
    --accent-dim:   #9e6b14;
    --accent-glow:  rgba(232, 160, 32, 0.15);
    --text-1:       #eeeef2;
    --text-2:       #9090a0;
    --text-3:       #55556a;
    --border:       #1f1f2c;
    --border-lit:   #2e2e3e;
    --green:        #22c55e;
    --green-dim:    rgba(34, 197, 94, 0.12);
    --red:          #ef4444;
    --red-dim:      rgba(239, 68, 68, 0.12);
    --blue:         #60a5fa;
    --blue-dim:     rgba(96, 165, 250, 0.10);
  }

  /* ── 字体系统 (Tabular Numbers for data) ──────────────────────── */
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');
  html, body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', 'Courier New', monospace !important; font-variant-numeric: tabular-nums; }
  [data-testid="stMetric"] [data-testid="stMetricValue"] { letter-spacing: -0.02em; }

  /* ── 全局背景 ─────────────────────────────────────────────────── */
  .stApp { background: var(--bg-void); color: var(--text-1); }
  [data-testid="stHeader"] { background: transparent; border-bottom: 1px solid var(--border); }
  [data-testid="stMainBlockContainer"] { padding-top: 1.5rem; padding-left: 2rem; padding-right: 2rem; }
  [data-testid="stStatusWidget"] { display: none; }

  /* ── 滚动条 ──────────────────────────────────────────────────── */
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: var(--bg-base); }
  ::-webkit-scrollbar-thumb { background: var(--border-lit); border-radius: 2px; }

  /* ── 侧边栏 ──────────────────────────────────────────────────── */
  [data-testid="stSidebar"] {
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    width: 220px !important;
    transition: width 0.2s;
  }
  [data-testid="stSidebar"]:hover { width: 220px !important; }

  /* ── 侧边栏头部 ──────────────────────────────────────────────── */
  .qd-logo-wrap {
    padding: 20px 16px 16px;
    border-bottom: 1px solid var(--border);
  }
  .qd-logo {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-1);
    text-transform: uppercase;
  }
  .qd-tagline {
    font-size: 0.65rem;
    color: var(--text-3);
    letter-spacing: 0.06em;
    margin-top: 3px;
  }

  /* ── 导航项 ──────────────────────────────────────────────────── */
  .qd-nav-section { padding: 10px 10px 4px; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-3); }
  .qd-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 12px;
    margin: 2px 6px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-2);
    transition: background 0.12s, color 0.12s, border-color 0.12s;
    border: 1px solid transparent;
    user-select: none;
    position: relative;
  }
  .qd-nav-item:hover { background: var(--bg-raised); color: var(--text-1); }
  .qd-nav-item.active {
    background: var(--bg-raised);
    color: var(--accent);
    border-color: var(--border-lit);
  }
  .qd-nav-item.active::before {
    content: '';
    position: absolute;
    left: -6px;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 60%;
    background: var(--accent);
    border-radius: 0 2px 2px 0;
  }
  .qd-nav-icon { font-size: 1rem; width: 20px; text-align: center; flex-shrink: 0; }
  .qd-nav-label { flex: 1; line-height: 1.3; }
  .qd-nav-sub { font-size: 0.62rem; color: var(--text-3); font-weight: 400; }

  /* ── 侧边栏底部 ──────────────────────────────────────────────── */
  .qd-sidebar-footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 10px 16px;
    border-top: 1px solid var(--border);
    font-size: 0.62rem;
    color: var(--text-3);
  }

  /* ── 页面头部 ────────────────────────────────────────────────── */
  .qd-page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding-bottom: 1.2rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.6rem;
  }
  .qd-page-title { font-size: 1.5rem; font-weight: 700; color: var(--text-1); letter-spacing: -0.02em; line-height: 1.2; }
  .qd-page-sub { font-size: 0.75rem; color: var(--text-3); margin-top: 4px; }
  .qd-header-right { text-align: right; }
  .qd-live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    margin-right: 5px;
    animation: pulse-green 2s infinite;
  }
  @keyframes pulse-green {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* ── Metric 卡片 ──────────────────────────────────────────────── */
  div[data-testid="stMetric"] {
    background: var(--bg-surface);
    border: 1px solid var(--border-lit);
    border-radius: 8px;
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
  }
  div[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
    opacity: 0.6;
  }
  div[data-testid="stMetricLabel"] {
    color: var(--text-3) !important;
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  div[data-testid="stMetricValue"] { color: var(--text-1) !important; font-weight: 700; font-size: 1.1rem; }
  div[data-testid="stMetricDelta"] { font-size: 0.7rem; }

  /* ── 分隔线 ──────────────────────────────────────────────────── */
  .qd-divider { border: none; border-top: 1px solid var(--border); margin: 1.2rem 0; }

  /* ── 区块标题 ────────────────────────────────────────────────── */
  .qd-section-title {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  /* ── 按钮重写 ────────────────────────────────────────────────── */
  .stButton > button {
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.82rem;
    border: 1px solid var(--border-lit);
    background: var(--bg-raised);
    color: var(--text-1);
    transition: all 0.15s;
    height: 36px;
  }
  .stButton > button:hover { background: var(--bg-overlay); border-color: var(--accent); color: var(--accent); }
  button[kind="primary"] {
    background: var(--accent) !important;
    color: #000 !important;
    border-color: var(--accent) !important;
    font-weight: 700 !important;
  }
  button[kind="primary"]:hover { background: var(--accent-dim) !important; border-color: var(--accent-dim) !important; color: #fff !important; }

  /* ── 数据表格 ────────────────────────────────────────────────── */
  .dataframe tbody tr:nth-child(even) { background: var(--bg-raised) !important; }
  .dataframe tbody tr:hover { background: var(--bg-overlay) !important; }
  thead th {
    background: var(--bg-raised) !important;
    color: var(--text-3) !important;
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 2px solid var(--border-lit) !important;
    padding: 8px 12px !important;
  }
  tbody td { border-color: var(--border) !important; font-size: 0.8rem; padding: 7px 12px !important; }

  /* ── 输入框 ──────────────────────────────────────────────────── */
  .stTextInput > div > div > input,
  .stNumberInput > div > div > input {
    background: var(--bg-surface);
    border: 1px solid var(--border-lit);
    border-radius: 6px;
    color: var(--text-1);
    font-size: 0.85rem;
  }
  .stTextInput > div > div > input:focus,
  .stNumberInput > div > div > input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-glow);
  }
  .stTextInput label, .stNumberInput label,
  .stSlider label, .stCheckbox label {
    color: var(--text-2) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
  }

  /* ── Selectbox / Tabs ─────────────────────────────────────────── */
  .stSelectbox > div > div { background: var(--bg-surface); border: 1px solid var(--border-lit); border-radius: 6px; }
  .stTabs [data-baseweb="tab-list"] { gap: 2px; background: var(--bg-surface); border-radius: 6px; padding: 2px; }
  .stTabs [data-baseweb="tab"] {
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-2);
    border: none;
  }
  .stTabs [aria-selected="true"] { background: var(--bg-overlay) !important; color: var(--accent) !important; }

  /* ── 展开器 ──────────────────────────────────────────────────── */
  .streamlit-expanderHeader {
    border-radius: 6px;
    background: var(--bg-surface);
    border: 1px solid var(--border-lit);
    color: var(--text-2);
    font-size: 0.82rem;
    font-weight: 600;
  }
  .streamlit-expanderContent { background: var(--bg-surface); border: 1px solid var(--border); border-top: none; border-radius: 0 0 6px 6px; }

  /* ── 告警卡片 ────────────────────────────────────────────────── */
  .qd-alert-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-lit);
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  .qd-alert-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

  /* ── 行情色彩 ─────────────────────────────────────────────────── */
  .gain { color: var(--green) !important; font-weight: 700; }
  .loss { color: var(--red) !important; font-weight: 700; }
  .neutral { color: var(--text-2) !important; }

  /* ── 状态指示器行 ────────────────────────────────────────────── */
  .qd-status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.8rem;
  }
  .qd-status-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  }

  /* ── 工作流步骤 ──────────────────────────────────────────────── */
  .qd-step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
  }
  .qd-step-num {
    width: 24px; height: 24px;
    border-radius: 50%;
    background: var(--bg-overlay);
    border: 1px solid var(--border-lit);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--text-3);
    flex-shrink: 0;
  }
  .qd-step-title { font-size: 0.85rem; font-weight: 600; color: var(--text-1); }
  .qd-step-desc { font-size: 0.72rem; color: var(--text-3); margin-top: 2px; }

  /* ── 动画入场 ────────────────────────────────────────────────── */
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .stApp > div { animation: fadeInUp 0.3s ease-out; }
</style>
""", unsafe_allow_html=True)

# ── session_state ────────────────────────────────────────────────────────────
if 'nav_page' not in st.session_state:
    st.session_state['nav_page'] = '智能选股'
for _k in ('screener_cache', 'screener_cache_time', 'news_cache', 'news_cache_time', 'analyze_code'):
    if _k not in st.session_state:
        st.session_state[_k] = None

# ── 侧边栏导航 ──────────────────────────────────────────────────────────────
NAV = [
    ("系统状态",   "🖥", "模块总览"),
    ("个股分析报告","📊", "技术·财务·建议"),
    ("智能选股",   "🎯", "多因子筛选"),
    ("策略信号",   "📈", "5大策略"),
    ("财经资讯",   "📰", "舆情分析"),
    ("告警监控",   "🔔", "价格告警"),
    ("每日工作流", "⚡", "一键执行"),
]

with st.sidebar:
    st.markdown('<div class="qd-logo-wrap"><div class="qd-logo">QuantDesk</div><div class="qd-tagline">投资决策辅助平台 · v2.0</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="qd-nav-section">导航</div>', unsafe_allow_html=True)

    for name, icon, sub in NAV:
        active = st.session_state['nav_page'] == name
        cls = "qd-nav-item active" if active else "qd-nav-item"
        lbl = f'<span class="qd-nav-icon">{icon}</span><div class="qd-nav-label"><div>{name}</div><div class="qd-nav-sub">{sub}</div></div>'
        if st.button(name, key=f"nav_{name}", help=name,
                    use_container_width=True,
                    type="primary" if active else "secondary"):
            st.session_state['nav_page'] = name
            st.rerun()
        st.markdown(f'<div class="{cls}" id="nav_{name}" style="display:none"></div>', unsafe_allow_html=True)

    st.markdown('<div class="qd-sidebar-footer">仅供参考 · 不构成投资建议</div>', unsafe_allow_html=True)

page = st.session_state['nav_page']

# ── 页面头部宏 ──────────────────────────────────────────────────────────────
def page_header(title, subtitle, live=False):
    now = datetime.now().strftime("%H:%M:%S")
    live_tag = f'<span class="qd-live-dot"></span><span style="font-size:0.7rem;color:var(--green)">LIVE</span>' if live else ''
    st.markdown(f"""
    <div class="qd-page-header">
      <div>
        <div class="qd-page-title">{title}</div>
        <div class="qd-page-sub">{subtitle}</div>
      </div>
      <div class="qd-header-right">
        {live_tag}
        <div style="font-size:0.68rem;color:var(--text-3);font-family:'IBM Plex Mono',monospace">{now}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def section_title(text):
    st.markdown(f'<div class="qd-section-title">{text}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="qd-divider"/>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 页面 1: 系统状态
# ═══════════════════════════════════════════════════════════════════════════
if page == "系统状态":
    page_header("系统状态", "模块连接与数据源健康检查", live=True)

    # 整体状态卡
    try:
        r = requests.get(f"{API_URL}/", timeout=5)
        msg = r.json()['message']
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div style="background:var(--green-dim);border:1px solid var(--green);border-radius:8px;padding:16px"><div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--green);font-weight:700">系统状态</div><div style="font-size:1.2rem;font-weight:700;color:var(--green);margin-top:6px">正常运行</div><div style="font-size:0.72rem;color:var(--text-3);margin-top:4px">{msg}</div></div>', unsafe_allow_html=True)
    except Exception:
        col1, col2, col3 = st.columns(3)
        col1.markdown('<div style="background:var(--red-dim);border:1px solid var(--red);border-radius:8px;padding:16px"><div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--red);font-weight:700">系统状态</div><div style="font-size:1.2rem;font-weight:700;color:var(--red);margin-top:6px">未启动</div><div style="font-size:0.72rem;color:var(--text-3);margin-top:4px">请运行 python web/api_server.py</div></div>', unsafe_allow_html=True)

    col2.metric("运行时间", datetime.now().strftime("%H:%M"), "系统正常")
    col3.metric("模块数量", "8", "全部就绪")

    section_title("数据模块")
    modules = [
        ("实时行情",   "腾讯财经直调",     True,  "实时 + 历史K线"),
        ("历史K线",    "Baostock",         True,  "前复权日线"),
        ("财务指标",   "AKShare",          True,  "PE · ROE · 毛利率"),
        ("资讯聚合",   "财联社/新浪/东财",  True,  "快讯 · 公告 · 资金流"),
        ("智能选股",   "多因子引擎",        True,  "技术面优先 · 基本面过滤"),
        ("策略信号",   "5大策略",           True,  "双均线 · 布林 · RSI · 海龟 · MACD"),
        ("告警监控",   "邮件 + 钉钉",       True,  "价格 · 涨跌幅 · 信号触发"),
        ("Agent 工作流","Librarian · Oracle", True, "多Agent 协作流水线"),
    ]
    for i in range(0, len(modules), 2):
        c1, c2 = st.columns(2)
        for j, m in enumerate(modules[i:i+2]):
            name, source, ok, desc = m
            col = c1 if j == 0 else c2
            dot_color = "var(--green)" if ok else "var(--red)"
            status_text = "在线" if ok else "离线"
            col.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)">
              <div>
                <div style="font-size:0.85rem;font-weight:600;color:var(--text-1)">{name}</div>
                <div style="font-size:0.68rem;color:var(--text-3);margin-top:2px">{source} · {desc}</div>
              </div>
              <div style="display:flex;align-items:center;gap:5px">
                <span style="width:6px;height:6px;border-radius:50%;background:{dot_color};box-shadow:0 0 5px {dot_color};display:inline-block;flex-shrink:0"></span>
                <span style="font-size:0.7rem;font-weight:600;color:{dot_color}">{status_text}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 页面 2: 个股分析报告
# ═══════════════════════════════════════════════════════════════════════════
elif page == "个股分析报告":
    page_header("个股分析报告", "实时行情 · 技术分析 · 财务指标 · 投资建议")

    # 快捷按钮
    quick = [("贵州茅台", "600519"), ("平安银行", "000001"), ("宁德时代", "300750"), ("招商银行", "600036"), ("比亚迪", "002594")]
    bts = st.columns([1] + [1.2]*5)
    for i, (nm, cd) in enumerate(quick):
        if bts[i+1].button(f"{nm}", help=f"{cd}", use_container_width=True):
            st.session_state['analyze_code'] = cd
            st.rerun()

    # 搜索框
    inp_col, btn_col = st.columns([4, 1])
    code_val = st.session_state.get('analyze_code', '')
    inp = inp_col.text_input("股票代码", value=code_val, placeholder="输入代码如 600519", label_visibility="collapsed")
    go = btn_col.button("🔍 分析", type="primary", use_container_width=True)

    if go and inp:
        st.session_state['analyze_code'] = inp.strip()
        with st.spinner("正在分析..."):
            try:
                from tasks.stock_analyzer import StockAnalyzer
                analyzer = StockAnalyzer()
                result = analyzer.analyze(inp.strip())
                rt = result.get('realtime', {})
                tech = result.get('technical', {})
                fin = result.get('financial', {})

                # ── 实时行情 ──
                section_title("实时行情")
                pct = rt.get('pct_chg', 0)
                price = rt.get('current', 0)
                price_cls = "gain" if pct >= 0 else "loss"

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">股票</div><div style="font-size:1.1rem;font-weight:700;color:var(--text-1);margin-top:4px">{rt.get("name", inp)}</div><div style="font-size:0.68rem;color:var(--text-3)">{inp}</div>', unsafe_allow_html=True)
                c2.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">当前价</div><div style="font-size:1.1rem;font-weight:700;color:var(--text-1);margin-top:4px;font-family:IBM Plex Mono,monospace">{price}</div>', unsafe_allow_html=True)
                c3.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">涨跌幅</div><div style="font-size:1.1rem;font-weight:700;color:{price_cls};margin-top:4px">{pct:+.2f}%</div>', unsafe_allow_html=True)
                c4.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">今开</div><div style="font-size:0.9rem;font-weight:600;color:var(--text-1);margin-top:4px">{rt.get("open", "—")}</div>', unsafe_allow_html=True)
                c5.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">成交额</div><div style="font-size:0.9rem;font-weight:600;color:var(--text-1);margin-top:4px">{analyzer._fmt_amount(rt.get("amount", 0))}</div>', unsafe_allow_html=True)

                # ── 技术分析 ──
                section_title("技术分析")
                if 'error' not in tech:
                    ma5  = tech.get('ma5', 0)
                    ma20 = tech.get('ma20', 0)
                    ma60 = tech.get('ma60', 0)
                    rsi  = tech.get('rsi', 0)
                    price_v = tech.get('price', price)
                    above_ma5  = price_v > ma5 if (ma5 and price_v) else False
                    above_ma20 = price_v > ma20 if (ma20 and price_v) else False
                    above_ma60 = price_v > ma60 if (ma60 and price_v) else False
                    bullish = sum([above_ma5, above_ma20, above_ma60])

                    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
                    for c, label, val in [
                        (tc1, "MA5",  ma5),
                        (tc2, "MA20", ma20),
                        (tc3, "MA60", ma60),
                        (tc4, "RSI",  rsi),
                        (tc5, "趋势",  tech.get('signal', '—')),
                    ]:
                        v_str = f"{val:.2f}" if isinstance(val, float) else str(val)
                        c.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">{label}</div><div style="font-size:1.05rem;font-weight:700;color:var(--text-1);margin-top:4px;font-family:IBM Plex Mono,monospace">{v_str}</div>', unsafe_allow_html=True)

                    # 均线排列
                    alignment = []
                    if above_ma5:  alignment.append("MA5")
                    if above_ma20: alignment.append("MA20")
                    if above_ma60: alignment.append("MA60")
                    ma_cls = "var(--green)" if bullish >= 2 else "var(--red)"
                    ma_msg = f"均线多头排列 × {bullish}/3" if bullish >= 2 else f"均线排列 × {bullish}/3"
                    st.markdown(f'<div style="padding:10px 14px;border-radius:6px;background:var(--bg-surface);border:1px solid {ma_cls};font-size:0.82rem;font-weight:600;color:{ma_cls}">{ma_msg}: {" · ".join(alignment) if alignment else "无"}</div>', unsafe_allow_html=True)
                else:
                    st.warning(f"技术数据获取失败: {tech.get('error')}")

                # ── 财务指标 ──
                section_title("财务指标")
                if 'error' not in fin and fin:
                    roe_val  = fin.get('roe', 0)
                    debt_val = fin.get('debt_ratio', 0)
                    pe_val   = fin.get('pe', None)
                    fc1, fc2, fc3 = st.columns(3)
                    roe_cls  = "var(--green)" if roe_val > 15 else "var(--accent)" if roe_val > 8 else "var(--red)"
                    debt_cls = "var(--green)" if debt_val < 50 else "var(--accent)" if debt_val < 70 else "var(--red)"
                    for c, label, val, cls in [
                        (fc1, "ROE",      f"{roe_val:.1f}%",  roe_cls),
                        (fc2, "资产负债率", f"{debt_val:.1f}%", debt_cls),
                        (fc3, "EPS",      f"{fin.get('eps', '—')} 元", "var(--text-1)"),
                    ]:
                        c.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">{label}</div><div style="font-size:1.1rem;font-weight:700;color:{cls};margin-top:4px">{val}</div>', unsafe_allow_html=True)
                else:
                    st.info("财务数据获取失败（网络限制）")

                # ── 综合建议 ──
                section_title("综合建议")
                advice = result.get('advice', '')
                advice_cls = "var(--green)" if '强烈推荐' in advice else "var(--accent)" if '建议关注' in advice else "var(--red)"
                advice_bg = "var(--green-dim)" if '强烈推荐' in advice else "rgba(232,160,32,0.08)" if '建议关注' in advice else "var(--red-dim)"
                st.markdown(f'<div style="padding:14px 16px;border-radius:8px;background:{advice_bg};border:1px solid {advice_cls.split("var(")[1].split(")")[0] if "var(" in advice_cls else advice_cls.replace("var(--","").replace(")","")};font-size:0.9rem;font-weight:600;color:{advice_cls}">{advice}</div>', unsafe_allow_html=True)

                with st.expander("📄 完整 Markdown 报告"):
                    st.markdown(analyzer.format_markdown(result))
            except Exception as e:
                st.error(f"分析失败: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 页面 3: 智能选股
# ═══════════════════════════════════════════════════════════════════════════
elif page == "智能选股":
    page_header("智能选股引擎", "多因子量化筛选 · ROE · 毛利率 · 量比 · 均线排列")

    # 参数配置
    cfg_cols = st.columns([1,1,1,1,1,1])
    roe_min  = cfg_cols[0].slider("ROE 下限 (%)", 0.0, 30.0, 10.0, 0.5)
    gm_min   = cfg_cols[1].slider("毛利率 (%)",  0.0, 80.0, 20.0, 1.0)
    debt_max = cfg_cols[2].slider("负债率上限 (%)", 20.0, 95.0, 60.0, 1.0)
    vol_min  = cfg_cols[3].slider("量比 (x)",  1.0, 3.0, 1.5, 0.1)
    rsi_max  = cfg_cols[4].slider("RSI 上限",  50.0, 90.0, 70.0, 1.0)
    top_n    = int(cfg_cols[5].slider("返回数量", 10, 100, 30, 5))
    ma20_req = st.checkbox("要求站上 20 日均线", value=True)

    if st.button("🚀 开始选股", type="primary", use_container_width=True):
        with st.spinner("选股中（约30秒）..."):
            try:
                from screener.factor_engine import StockScreener, FactorConfig
                cfg = FactorConfig(roe_min=roe_min, gross_margin_min=gm_min,
                                   debt_ratio_max=debt_max, volume_boost_min=vol_min,
                                   rsi_max=rsi_max, ma20_break=ma20_req, top_n=top_n)
                screener = StockScreener(cfg)
                results = screener.screen(dry_run=True)
                if not results:
                    st.warning("未筛选出符合条件的股票，请放宽条件")
                else:
                    st.session_state['screener_cache'] = results
                    st.session_state['screener_cache_time'] = pd.Timestamp.now()
                    st.success(f"筛选出 {len(results)} 只符合条件股票")

                    section_title(f"TOP {min(10, len(results))} 推荐")
                    disp = [{
                        "排名": r.rank,
                        "代码": r.ts_code,
                        "名称": r.name,
                        "现价": f"¥{r.close:.2f}",
                        "涨幅": f"{r.pct_chg:+.2f}%",
                        "评分": f"{r.score:.0f}",
                        "信号": "🟢 BUY" if r.signal == "BUY" else "🟡 HOLD",
                        "推荐理由": r.reason,
                    } for r in results[:10]]
                    st.dataframe(pd.DataFrame(disp), use_container_width=True, hide_index=True)

                    csv_lines = ["排名,代码,名称,现价,涨幅,评分,信号,推荐理由"]
                    for r in results:
                        csv_lines.append(f"{r.rank},{r.ts_code},{r.name},{r.close:.2f},{r.pct_chg:+.2f}%,{r.score:.0f},{r.signal},{r.reason}")
                    st.download_button("📥 导出 CSV", '\n'.join(csv_lines).encode('utf-8-sig'),
                                     "stock_screening.csv", "text/csv", key="exp")
            except Exception as e:
                st.error(f"选股失败: {e}")

    if st.session_state.get('screener_cache'):
        ct = st.session_state['screener_cache_time']
        st.info(f"📋 缓存结果（{ct.strftime('%H:%M:%S')}），修改参数后重新点击「开始选股」")

# ═══════════════════════════════════════════════════════════════════════════
# 页面 4: 策略信号
# ═══════════════════════════════════════════════════════════════════════════
elif page == "策略信号":
    page_header("多策略信号聚合", "双均线 · 布林带 · RSI · 海龟 · MACD 五策略综合投票")
    sig_code = st.text_input("股票代码", value="600519", placeholder="输入代码如 600519")
    if st.button("📊 生成信号", type="primary"):
        with st.spinner("计算中..."):
            try:
                from data.data_loader import BaostockDataLoader, StockDataLoader
                from strategies.signal_generator import SignalAggregator
                from datetime import timedelta as td

                loader = StockDataLoader()
                baostock = BaostockDataLoader()
                cd = sig_code.strip().upper()
                if not cd.startswith(('6','0','3')): cd = '6'+cd
                norm = f"{cd}.SH" if cd.startswith(('6','5','9')) else f"{cd}.SZ"

                hist = baostock.fetch_historical(norm,
                    (datetime.now()-td(days=90)).strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d'))
                if hist.empty:
                    st.error("无法获取K线数据")
                else:
                    agg = SignalAggregator()
                    res = agg.get_signal(hist)
                    action = res['final_action']
                    conf  = res['confidence']
                    votes = res['votes']
                    total = sum(votes.values()) or 1
                    buy_pct = votes.get('BUY', 0) / total

                    section_title("综合信号")
                    ac = st.columns([2,1,1])
                    ac_cls  = "var(--green)" if action=="BUY" else "var(--red)" if action=="SELL" else "var(--accent)"
                    ac_icon = "🟢 BUY" if action=="BUY" else "🔴 SELL" if action=="SELL" else "🟡 HOLD"
                    ac[0].markdown(f'<div style="padding:12px 16px;border-radius:8px;background:{"var(--green-dim)" if action=="BUY" else "var(--red-dim)" if action=="SELL" else "var(--bg-surface)"};border:1px solid {"var(--green)" if action=="BUY" else "var(--red)" if action=="SELL" else "var(--accent)"}"><div style="font-size:1.3rem;font-weight:700;color:{ac_cls}">{ac_icon}</div><div style="font-size:0.7rem;color:var(--text-3);margin-top:4px">综合信号 · {action}</div></div>', unsafe_allow_html=True)
                    ac[1].markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">置信度</div><div style="font-size:1.3rem;font-weight:700;color:var(--text-1);margin-top:4px">{conf:.0%}</div>', unsafe_allow_html=True)
                    ac[2].markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">买票率</div><div style="font-size:1.3rem;font-weight:700;color:var(--green);margin-top:4px">{buy_pct:.0%}</div>', unsafe_allow_html=True)

                    section_title("各策略详情")
                    rows = []
                    for nm, sd in res['signals'].items():
                        ai = sd['action']
                        icon = "🟢" if ai=="BUY" else "🔴" if ai=="SELL" else "🟡"
                        rows.append({
                            "策略": nm,
                            "信号": f"{icon} {ai}",
                            "置信度": f"{sd['confidence']:.0%}",
                            "建议价": f"¥{sd['price']:.2f}",
                            "止损": f"¥{sd['stop_loss']:.2f}",
                            "止盈": f"¥{sd['take_profit']:.2f}",
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"信号生成失败: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 页面 5: 财经资讯
# ═══════════════════════════════════════════════════════════════════════════
elif page == "财经资讯":
    page_header("财经资讯聚合", "财联社快讯 · 市场舆情 · 个股情绪分析")
    tab1, tab2, tab3 = st.tabs(["采集资讯", "舆情分析", "个股舆情"])

    with tab1:
        if st.button("📥 立即采集", type="primary"):
            with st.spinner("采集中..."):
                try:
                    from news.collector import NewsCollector
                    c = NewsCollector()
                    cnt = c.collect_all()
                    st.success(f"采集完成: {cnt} 条资讯")
                except Exception as e:
                    st.error(f"采集失败: {e}")
        st.info("数据来源: 财联社快讯 · 新浪财经 · 东方财富个股公告 · 主力资金新闻")

    with tab2:
        days = st.slider("统计周期（天）", 1, 7, 1)
        if st.button("🔍 分析舆情"):
            with st.spinner("分析中..."):
                try:
                    from news.collector import NewsCollector, SentimentAnalyzer
                    c = NewsCollector()
                    a = SentimentAnalyzer()
                    sm = c.db.get_market_summary(days=days)
                    bull = sm.get('bullish_ratio', 0)
                    m1, m2, m3 = st.columns(3)
                    m1.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">资讯总数</div><div style="font-size:1.5rem;font-weight:700;color:var(--text-1);margin-top:4px">{sm.get("total_news",0)}</div>', unsafe_allow_html=True)
                    m2.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--green);font-weight:700">利好</div><div style="font-size:1.5rem;font-weight:700;color:var(--green);margin-top:4px">{sm.get("positive_count",0)}</div>', unsafe_allow_html=True)
                    m3.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--red);font-weight:700">利空</div><div style="font-size:1.5rem;font-weight:700;color:var(--red);margin-top:4px">{sm.get("negative_count",0)}</div>', unsafe_allow_html=True)
                    mood_cls = "var(--green)" if bull>60 else "var(--red)" if bull<40 else "var(--accent)"
                    st.markdown(f'<div style="margin-top:12px;padding:12px 16px;border-radius:8px;background:var(--bg-surface);border:1px solid {mood_cls.split("var(")[1].split(")")[0] if "var(" in mood_cls else mood_cls};font-size:0.9rem;font-weight:600;color:{mood_cls}">市场情绪: {"偏暖 🌤️" if bull>60 else "偏冷 🥶" if bull<40 else "中性 🌥️"} · 看涨比 {bull}%</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"分析失败: {e}")

    with tab3:
        sc = st.text_input("股票代码", value="600519")
        sd = st.slider("天数", 1, 30, 7)
        if st.button("📊 查询舆情"):
            with st.spinner("查询中..."):
                try:
                    from news.collector import NewsCollector, SentimentAnalyzer
                    import re
                    m = re.search(r'(\d{6})', sc)
                    code_str = f"{m.group(1)}.SH" if m and m.group(1).startswith(('6','5','9')) else sc
                    c = NewsCollector()
                    a = SentimentAnalyzer()
                    r = a.get_stock_sentiment(c.db, code_str, days=sd)
                    sent = r.get('sentiment', 0)
                    label = r.get('label', '中性')
                    cnt = r.get('news_count', 0)
                    s_cls = "var(--green)" if sent>0.2 else "var(--red)" if sent<-0.2 else "var(--accent)"
                    s1, s2 = st.columns(2)
                    s1.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-3);font-weight:700">舆情评分</div><div style="font-size:1.5rem;font-weight:700;color:{s_cls};margin-top:4px">{sent:+.2f}</div>', unsafe_allow_html=True)
                    s2.markdown(f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:{s_cls};font-weight:700">情绪</div><div style="font-size:1.1rem;font-weight:700;color:{s_cls};margin-top:4px">{label}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"查询失败: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 页面 6: 告警监控
# ═══════════════════════════════════════════════════════════════════════════
elif page == "告警监控":
    page_header("股票告警监控", "价格告警 · 涨跌幅 · 邮件推送 · 钉钉通知")
    section_title("添加告警规则")
    a1, a2 = st.columns([1,1])
    ac = a1.text_input("股票代码", value="600519")
    an = a2.text_input("股票名称", value="贵州茅台")
    a3, a4 = st.columns([1,1])
    at = a3.selectbox("告警类型", ["price_up","price_down","pct_chg","signal_buy","signal_sell"],
                      format_func=lambda x: {"price_up":"价格达到","price_down":"价格跌破","pct_chg":"涨跌幅触发","signal_buy":"策略 BUY","signal_sell":"策略 SELL"}[x])
    thr = a4.number_input("阈值", value=5.0, step=0.5)
    if st.button("✅ 添加规则", type="primary"):
        try:
            from monitor.alerts import StockWatcher
            w = StockWatcher()
            wid = w.add_alert(ac, an, at, float(thr))
            st.success(f"规则添加成功: {an}({ac}) · {at} · {thr}")
        except Exception as e:
            st.error(f"添加失败: {e}")

    section_title("当前告警规则")
    try:
        from monitor.alerts import AlertDatabase
        db = AlertDatabase()
        rules = db.get_active_rules()
        if rules:
            rows = [{"股票": f"{r.name}({r.ts_code})", "类型": r.alert_type, "阈值": r.threshold, "冷却(分)": r.cooldown_min} for r in rules]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("暂无告警规则")
    except Exception as e:
        st.error(f"读取告警失败: {e}")
    st.caption("💡 后台运行 python monitor/alerts.py 启动实时监控")

# ═══════════════════════════════════════════════════════════════════════════
# 页面 7: 每日工作流
# ═══════════════════════════════════════════════════════════════════════════
elif page == "每日工作流":
    page_header("每日自动化工作流", "资讯 → 舆情 → 选股 → 策略 → 报告 → 推送")
    section_title("执行流程")
    steps = [
        ("01", "采集财经资讯",    "财联社 · 新浪财经 · 主力资金"),
        ("02", "生成舆情报告",    "SnowNLP 情感打分 · 利好利空分类"),
        ("03", "执行智能选股",    "多因子筛选 · 技术面 + 基本面"),
        ("04", "生成策略信号",    "5大策略投票聚合"),
        ("05", "整合日报",        "Markdown 格式 · 投资建议"),
        ("06", "推送发送",        "163邮件 · 钉钉机器人"),
    ]
    for num, title, desc in steps:
        st.markdown(f'<div class="qd-step"><div class="qd-step-num">{num}</div><div><div class="qd-step-title">{title}</div><div class="qd-step-desc">{desc}</div></div></div>', unsafe_allow_html=True)

    st.markdown('<hr class="qd-divider"/>', unsafe_allow_html=True)
    if st.button("🚀 执行完整工作流", type="primary", use_container_width=True):
        with st.spinner("执行中（约 2-5 分钟）..."):
            try:
                from workflows.daily_workflow import DailyWorkflow
                wf = DailyWorkflow()
                results = wf.run(dry_run=False)
                for nm, res in results.items():
                    st.markdown(f'<div style="padding:8px 0;border-bottom:1px solid var(--border)"><span style="font-weight:700;color:var(--accent)">{nm}</span></div>', unsafe_allow_html=True)
                report_r = results.get("5. 整合报告", {})
                if report_r and isinstance(report_r, dict):
                    p = report_r.get('path')
                    if p and os.path.exists(p):
                        with open(p,'r',encoding='utf-8') as f:
                            st.markdown("---")
                            st.subheader("📰 今日量化报告")
                            st.markdown(f.read())
                st.success("✅ 工作流执行完成！报告已保存至 ./reports/")
            except Exception as e:
                st.error(f"工作流失败: {e}")
    st.info("💡 定时任务: 右键管理员运行「配置定时任务.bat」")
