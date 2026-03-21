import streamlit as st
import requests
import pandas as pd
import sys
import os

API_URL = "http://localhost:8000"

st.set_page_config(page_title="量化交易系统", layout="wide")

# 添加项目路径以便直接导入分析器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

st.title("量化交易系统控制台")

# Sidebar - 导航
page = st.sidebar.selectbox(
    "选择功能",
    ["每日摘要", "个股查询", "交易下单", "系统状态", "个股分析报告"],
    index=4
)

# ─────────────────────────────────────────────
# 页面 1: 每日摘要
# ─────────────────────────────────────────────
if page == "每日摘要":
    st.header("今日股市复盘")
    if st.button("获取最新报告"):
        with st.spinner("正在获取报告..."):
            try:
                response = requests.get(f"{API_URL}/reports/latest", timeout=10)
                data = response.json()
                st.markdown(data['content'])
            except Exception as e:
                st.error(f"无法获取报告: {e}")

# ─────────────────────────────────────────────
# 页面 2: 个股查询
# ─────────────────────────────────────────────
elif page == "个股查询":
    st.header("个股详情查询")
    stock_code = st.text_input("请输入股票代码 (如 600519)")
    if st.button("查询"):
        with st.spinner("查询中..."):
            try:
                response = requests.get(f"{API_URL}/stocks/query/{stock_code}", timeout=10)
                data = response.json()
                st.write(pd.DataFrame([data]))
            except Exception as e:
                st.error(f"查询失败: {e}")

# ─────────────────────────────────────────────
# 页面 3: 交易下单
# ─────────────────────────────────────────────
elif page == "交易下单":
    st.header("模拟交易下单")
    with st.form("trade_form"):
        stock_code = st.text_input("股票代码 (如 600519)")
        price = st.number_input("价格", value=10.0, min_value=0.01, step=0.01)
        side = st.selectbox("方向", ["BUY", "SELL"])
        submit = st.form_submit_button("下单")

        if submit:
            with st.spinner("下单中..."):
                try:
                    response = requests.post(
                        f"{API_URL}/api/trade",
                        json={"ts_code": stock_code, "side": side, "price": price},
                        timeout=10
                    )
                    if response.status_code == 200:
                        st.success(f"下单成功: {response.json()['message']}, 规模: {response.json()['size']}")
                    else:
                        st.error(f"下单失败: {response.json().get('detail', '未知错误')}")
                except Exception as e:
                    st.error(f"连接失败: {e}")

# ─────────────────────────────────────────────
# 页面 4: 系统状态
# ─────────────────────────────────────────────
elif page == "系统状态":
    st.header("API 状态检查")
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        st.success(f"✅ 后端连接正常: {response.json()['message']}")
    except Exception as e:
        st.error(f"❌ 后端连接异常: {e}")

    st.markdown("### 数据源状态")
    st.markdown("- 🔗 腾讯财经直调: 实时行情 (已验证可用)")
    st.markdown("- 🔗 Baostock: 历史K线 (已验证可用)")
    st.markdown("- 🔗 AKShare: 财务指标 (需网络直连)")

# ─────────────────────────────────────────────
# 页面 5: 个股分析报告 (核心新增)
# ─────────────────────────────────────────────
elif page == "个股分析报告":
    st.header("📊 个股综合分析报告")
    st.markdown("输入股票代码，自动生成 **实时行情 + 技术分析 + 财务指标 + 投资建议** 报告")

    # 常用股票快捷按钮
    st.markdown("**快速查询:**")
    quick_btns = st.columns(5)
    quick_codes = [("贵州茅台", "600519"), ("平安银行", "000001"), ("宁德时代", "300750"), ("招商银行", "600036"), ("比亚迪", "002594")]
    for i, (name, code) in enumerate(quick_codes):
        if quick_btns[i].button(f"{name}\n({code})"):
            st.session_state['analyze_code'] = code

    stock_code_input = st.text_input(
        "📌 输入股票代码",
        value=st.session_state.get('analyze_code', ''),
        placeholder="例如: 600519 或 000001",
        help="支持6位代码，自动识别沪/深市场"
    )
    stock_code = (stock_code_input or '').strip()

    if st.button("🔍 生成分析报告", type="primary"):
        if not stock_code:
            st.warning("请输入股票代码")
        else:
            with st.spinner(f"正在分析 {stock_code}，请稍候..."):
                try:
                    # 直接调用分析器（绕过API避免网络问题）
                    from tasks.stock_analyzer import StockAnalyzer
                    analyzer = StockAnalyzer()
                    result = analyzer.analyze(stock_code)

                    rt = result.get('realtime', {})
                    tech = result.get('technical', {})
                    fin = result.get('financial', {})

                    # ── 实时行情卡片 ──────────────────────
                    st.markdown("---")
                    st.subheader("📈 实时行情")
                    name = rt.get('name', stock_code)
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("股票名称", name)
                    col2.metric("当前价", f"{rt.get('current', 'N/A')}")
                    pct = rt.get('pct_chg', 0)
                    delta_color = "normal" if pct >= 0 else "inverse"
                    col3.metric("涨跌幅", f"{pct}%", delta=f"{pct}%", delta_color=delta_color)
                    col4.metric("成交额", analyzer._fmt_amount(rt.get('amount')))

                    # ── 技术分析 ──────────────────────────
                    st.markdown("---")
                    st.subheader("📉 技术分析")
                    if 'error' not in tech:
                        tcol1, tcol2, tcol3, tcol4, tcol5 = st.columns(5)
                        tcol1.metric("MA5", f"{tech.get('ma5', 'N/A')}")
                        tcol2.metric("MA20", f"{tech.get('ma20', 'N/A')}")
                        tcol3.metric("MA60", f"{tech.get('ma60', 'N/A')}")
                        rsi = tech.get('rsi')
                        rsi_color = "🔴" if (rsi and rsi > 70) else "🟢" if (rsi and rsi < 30) else "🟡"
                        tcol4.metric(f"{rsi_color}RSI(14)", f"{rsi}")
                        tcol5.metric("趋势信号", tech.get('signal', 'N/A'))

                        # 均线排列可视化
                        price = tech.get('price', 0)
                        ma5 = tech.get('ma5', 0)
                        ma20 = tech.get('ma20', 0)
                        ma60 = tech.get('ma60', 0)
                        alignment = []
                        if price > ma5: alignment.append("MA5✅")
                        if price > ma20: alignment.append("MA20✅")
                        if price > ma60: alignment.append("MA60✅")
                        if len(alignment) >= 3:
                            st.success(f"均线多头排列: {' > '.join(alignment)}")
                        elif len(alignment) >= 1:
                            st.info(f"部分均线排列: {', '.join(alignment)}")
                        else:
                            st.warning("均线空头排列")
                    else:
                        st.warning(f"技术数据获取失败: {tech.get('error')}")

                    # ── 财务指标 ──────────────────────────
                    st.markdown("---")
                    st.subheader("💰 财务指标")
                    if 'error' not in fin and fin:
                        fcol1, fcol2, fcol3 = st.columns(3)
                        fcol1.metric("ROE (净资产收益率)", f"{fin.get('roe', 'N/A')}%", 
                                     delta="优秀" if fin.get('roe', 0) > 15 else "良好" if fin.get('roe', 0) > 8 else "偏弱")
                        fcol2.metric("资产负债率", f"{fin.get('debt_ratio', 'N/A')}%",
                                     delta="优秀" if fin.get('debt_ratio', 99) < 50 else "良好" if fin.get('debt_ratio', 99) < 70 else "偏高")
                        fcol3.metric("数据截止", fin.get('report_date', 'N/A'))
                        st.markdown(f"📋 基本每股收益 EPS: **{fin.get('eps', 'N/A')}** 元")
                    else:
                        st.info("财务数据获取失败（网络限制），可参考实时行情和技术分析")

                    # ── 综合建议 ──────────────────────────
                    st.markdown("---")
                    st.subheader("🎯 综合投资建议")
                    advice = result.get('advice', '数据不足，无法生成建议')
                    if '强烈推荐买入' in advice:
                        st.success(advice)
                    elif '建议关注' in advice:
                        st.info(advice)
                    elif '谨慎观望' in advice:
                        st.warning(advice)
                    else:
                        st.error(advice)

                    # ── 完整 Markdown 报告 ───────────────
                    with st.expander("📄 查看完整 Markdown 报告"):
                        md = analyzer.format_markdown(result)
                        st.markdown(md)

                    # ── 风险提示 ──────────────────────────
                    st.caption("⚠️ 免责声明: 本报告仅供参考，不构成投资建议。股市有风险，入市需谨慎。")

                except Exception as e:
                    st.error(f"分析失败: {e}")
