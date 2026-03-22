import streamlit as st
import requests
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

API_URL = "http://localhost:8000"

st.set_page_config(page_title="量化交易系统 v2", layout="wide")

# ── 页面导航 ──────────────────────────────────────────────────────────────

PAGES = [
    "系统状态",
    "个股分析报告",
    "智能选股",
    "策略信号",
    "财经资讯",
    "告警监控",
    "每日工作流",
]

st.title("量化交易系统 v2.0")
st.caption("资讯聚合 · 智能选股 · 策略信号 · 实时监控")

page = st.sidebar.selectbox("选择功能", PAGES, index=PAGES.index("智能选股"))


# ═══════════════════════════════════════════════════════════════════════════
# 页面 1: 系统状态
# ═══════════════════════════════════════════════════════════════════════════
if page == "系统状态":
    st.header("系统状态")

    try:
        r = requests.get(f"{API_URL}/", timeout=5)
        st.success(f"后端服务: ✅ 正常运行 ({r.json()['message']})")
    except Exception:
        st.error("后端服务: ❌ 未启动 (请先运行 `python web/api_server.py`)")

    st.markdown("""
    ### 已集成模块
    | 模块 | 状态 | 数据源 |
    |---|---|---|
    | 实时行情 | ✅ | 腾讯财经直调 |
    | 历史K线 | ✅ | Baostock |
    | 财务指标 | ✅ | AKShare |
    | 资讯聚合 | ✅ | 财联社/新浪/东财 |
    | 智能选股 | ✅ | 多因子引擎 |
    | 策略信号 | ✅ | 双均线/布林/RSI/海龟/MACD |
    | 告警监控 | ✅ | 邮件+钉钉推送 |
    | Agent 工作流 | ✅ | Librarian/Oracle/Momus/Ultrabrain |
    """)


# ═══════════════════════════════════════════════════════════════════════════
# 页面 2: 个股分析报告 (已有)
# ═══════════════════════════════════════════════════════════════════════════
elif page == "个股分析报告":
    st.header("📊 个股综合分析报告")

    quick_btns = st.columns(5)
    quick_codes = [
        ("贵州茅台", "600519"), ("平安银行", "000001"),
        ("宁德时代", "300750"), ("招商银行", "600036"), ("比亚迪", "002594"),
    ]
    for i, (name, code) in enumerate(quick_codes):
        if quick_btns[i].button(f"{name}\n({code})"):
            st.session_state['analyze_code'] = code

    stock_code_input = st.text_input(
        "📌 输入股票代码", value=st.session_state.get('analyze_code', ''),
        placeholder="例如: 600519", key="analyze_input"
    )
    stock_code = (stock_code_input or '').strip()

    if st.button("🔍 生成分析报告", type="primary"):
        if not stock_code:
            st.warning("请输入股票代码")
        else:
            with st.spinner("分析中..."):
                try:
                    from tasks.stock_analyzer import StockAnalyzer
                    analyzer = StockAnalyzer()
                    result = analyzer.analyze(stock_code)
                    rt = result.get('realtime', {})
                    tech = result.get('technical', {})
                    fin = result.get('financial', {})

                    # 实时行情
                    st.markdown("---")
                    st.subheader("📈 实时行情")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("股票", rt.get('name', stock_code))
                    c2.metric("当前价", f"{rt.get('current', 'N/A')}")
                    pct = rt.get('pct_chg', 0)
                    c3.metric("涨跌幅", f"{pct}%", delta=f"{pct}%",
                              delta_color="normal" if pct >= 0 else "inverse")
                    c4.metric("成交额", analyzer._fmt_amount(rt.get('amount')))

                    # 技术分析
                    st.markdown("---")
                    st.subheader("📉 技术分析")
                    if 'error' not in tech:
                        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
                        tc1.metric("MA5", f"{tech.get('ma5', 'N/A')}")
                        tc2.metric("MA20", f"{tech.get('ma20', 'N/A')}")
                        tc3.metric("MA60", f"{tech.get('ma60', 'N/A')}")
                        rsi = tech.get('rsi')
                        rsi_icon = "🔴" if (rsi and rsi > 70) else "🟢" if (rsi and rsi < 30) else "🟡"
                        tc4.metric(f"{rsi_icon}RSI", f"{rsi}")
                        tc5.metric("趋势", tech.get('signal', 'N/A'))

                        # 均线排列
                        price = tech.get('price', 0)
                        alignment = []
                        if price > (tech.get('ma5', 0)): alignment.append("MA5✅")
                        if price > (tech.get('ma20', 0)): alignment.append("MA20✅")
                        if price > (tech.get('ma60', 0)): alignment.append("MA60✅")
                        if len(alignment) >= 3:
                            st.success(f"均线多头排列: {' > '.join(alignment)}")
                        elif len(alignment) >= 1:
                            st.info(f"部分均线排列: {', '.join(alignment)}")
                        else:
                            st.warning("均线空头排列")
                    else:
                        st.warning(f"技术数据获取失败: {tech.get('error')}")

                    # 财务指标
                    st.markdown("---")
                    st.subheader("💰 财务指标")
                    if 'error' not in fin and fin:
                        fc1, fc2, fc3 = st.columns(3)
                        roe_val = fin.get('roe', 0)
                        debt_val = fin.get('debt_ratio', 99)
                        fc1.metric("ROE", f"{roe_val}%",
                                   delta="优秀" if roe_val > 15 else "良好" if roe_val > 8 else "偏弱")
                        fc2.metric("资产负债率", f"{debt_val}%",
                                   delta="优秀" if debt_val < 50 else "良好" if debt_val < 70 else "偏高")
                        fc3.metric("EPS", f"{fin.get('eps', 'N/A')} 元")
                    else:
                        st.info("财务数据获取失败（网络限制）")

                    # 综合建议
                    st.markdown("---")
                    st.subheader("🎯 综合建议")
                    advice = result.get('advice', '')
                    if '强烈推荐' in advice:
                        st.success(advice)
                    elif '建议关注' in advice:
                        st.info(advice)
                    elif '谨慎' in advice:
                        st.warning(advice)
                    else:
                        st.error(advice)

                    with st.expander("📄 完整 Markdown 报告"):
                        st.markdown(analyzer.format_markdown(result))

                    st.caption("⚠️ 免责声明: 仅供参考，不构成投资建议。")

                except Exception as e:
                    st.error(f"分析失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 页面 3: 智能选股
# ═══════════════════════════════════════════════════════════════════════════
elif page == "智能选股":
    st.header("🔍 智能选股引擎")

    st.markdown("""
    **多因子筛选**: ROE + 毛利率 + 资产负债率 + 量比放大 + 均线多头
    
    基于真实市场数据 (Baostock + 腾讯财经)，筛选符合趋势和技术条件的标的。
    """)

    # 选股参数配置
    with st.expander("⚙️ 筛选参数配置", expanded=True):
        col1, col2, col3 = st.columns(3)
        roe_min = col1.slider("ROE 下限 (%)", 0.0, 30.0, 10.0, 0.5)
        gross_margin_min = col2.slider("毛利率下限 (%)", 0.0, 80.0, 20.0, 1.0)
        debt_max = col3.slider("资产负债率上限 (%)", 20.0, 95.0, 60.0, 1.0)

        col4, col5, col6 = st.columns(3)
        vol_boost = col4.slider("量比下限 (x)", 1.0, 3.0, 1.5, 0.1)
        rsi_max = col5.slider("RSI 上限", 50.0, 90.0, 70.0, 1.0)
        top_n = col6.slider("返回数量", 10, 100, 30, 5)

        ma20_break = st.checkbox("要求站上 20 日均线", value=True)

    if st.button("🚀 开始选股", type="primary"):
        with st.spinner("选股中（需要30秒左右）..."):
            try:
                from screener.factor_engine import StockScreener, FactorConfig
                config = FactorConfig(
                    roe_min=roe_min,
                    gross_margin_min=gross_margin_min,
                    debt_ratio_max=debt_max,
                    volume_boost_min=vol_boost,
                    rsi_max=rsi_max,
                    ma20_break=ma20_break,
                    top_n=top_n,
                )
                screener = StockScreener(config)
                results = screener.screen(dry_run=True)  # 技术面优先

                if not results:
                    st.warning("未筛选出符合条件的股票，请放宽条件重试")
                else:
                    st.success(f"筛选出 {len(results)} 只符合条件股票")

                    # Top 10 展示
                    st.markdown("---")
                    st.subheader("🏆 TOP 10 推荐")
                    display = [{
                        "排名": r.rank,
                        "代码": r.ts_code,
                        "名称": r.name,
                        "现价": f"{r.close:.2f}",
                        "涨幅": f"{r.pct_chg:+.2f}%",
                        "评分": f"{r.score:.0f}",
                        "信号": "🟢BUY" if r.signal == "BUY" else "🟡HOLD",
                        "推荐理由": r.reason,
                    } for r in results[:10]]
                    st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)

                    # 导出
                    csv = '\n'.join([
                        f"{r.rank},{r.ts_code},{r.name},{r.close:.2f},{r.pct_chg:+.2f}%,{r.score:.0f},{r.signal},{r.reason}"
                        for r in results
                    ])
                    st.download_button(
                        "📥 导出 CSV",
                        csv.encode('utf-8'),
                        "stock_screening.csv",
                        "text/csv",
                    )

                    # 完整报告
                    with st.expander("📄 完整选股报告"):
                        st.markdown(screener.generate_report(results))

            except Exception as e:
                st.error(f"选股失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 页面 4: 策略信号
# ═══════════════════════════════════════════════════════════════════════════
elif page == "策略信号":
    st.header("📈 多策略信号聚合")

    st.markdown("""
    **5 大策略信号**: 双均线 | 布林带 | RSI 超买超卖 | 海龟交易 | MACD 金叉死叉
    
    多策略投票决策，综合置信度最高信号。
    """)

    sig_code = st.text_input("股票代码 (如 600519)", value="600519", key="sig_code").strip()

    if st.button("📊 生成信号", type="primary"):
        with st.spinner("计算信号中..."):
            try:
                from data.data_loader import BaostockDataLoader, StockDataLoader
                from strategies.signal_generator import SignalAggregator

                loader = StockDataLoader()
                baostock = BaostockDataLoader()

                # 获取历史K线
                code = sig_code.upper()
                if not code.startswith(('6', '0', '3')):
                    code = '6' + code
                normalized = (f"{code}.SH" if code.startswith(('6', '5', '9'))
                            else f"{code}.SZ")

                from datetime import datetime, timedelta
                hist = baostock.fetch_historical(
                    normalized,
                    (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d')
                )

                if hist.empty:
                    st.error("无法获取K线数据")
                else:
                    agg = SignalAggregator()
                    result = agg.get_signal(hist)

                    # 综合信号卡片
                    st.markdown("---")
                    action = result['final_action']
                    confidence = result['confidence']
                    votes = result['votes']
                    total_v = sum(votes.values()) or 1

                    col1, col2, col3 = st.columns(3)
                    if action == "BUY":
                        col1.success(f"🟢 综合信号: BUY")
                    elif action == "SELL":
                        col1.error(f"🔴 综合信号: SELL")
                    else:
                        col1.warning(f"🟡 综合信号: HOLD")
                    col2.metric("置信度", confidence)
                    col3.metric(" BUY 得票率", f"{votes['BUY']/total_v:.0%}")

                    # 各策略详情
                    st.markdown("---")
                    st.subheader("📋 各策略信号详情")
                    rows = []
                    for name, sig_dict in result['signals'].items():
                        action_icon = "🟢" if sig_dict['action'] == 'BUY' else "🔴" if sig_dict['action'] == 'SELL' else "🟡"
                        rows.append({
                            "策略": name,
                            "信号": f"{action_icon} {sig_dict['action']}",
                            "置信度": sig_dict['confidence'],
                            "建议价": f"{sig_dict['price']:.2f}",
                            "止损价": f"{sig_dict['stop_loss']:.2f}",
                            "止盈价": f"{sig_dict['take_profit']:.2f}",
                            "理由": sig_dict['reason'],
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"信号生成失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 页面 5: 财经资讯
# ═══════════════════════════════════════════════════════════════════════════
elif page == "财经资讯":
    st.header("📰 财经资讯聚合")

    tab1, tab2, tab3 = st.tabs(["采集资讯", "舆情分析", "个股舆情"])

    with tab1:
        st.subheader("采集财经快讯")
        if st.button("📥 立即采集", type="primary"):
            with st.spinner("采集中..."):
                try:
                    from news.collector import NewsCollector
                    collector = NewsCollector()
                    count = collector.collect_all()
                    summary = collector.db.get_market_summary()
                    st.success(f"采集完成: {count} 条资讯")
                    st.json(summary)
                except Exception as e:
                    st.error(f"采集失败: {e}")

        st.info("采集来源: 财联社快讯 | 新浪财经 | 东方财富个股公告")

    with tab2:
        st.subheader("市场舆情总览")
        days = st.slider("统计周期 (天)", 1, 7, 1, key="sentiment_days")
        if st.button("🔍 分析舆情", key="sentiment_btn"):
            with st.spinner("分析中..."):
                try:
                    from news.collector import NewsCollector, SentimentAnalyzer
                    collector = NewsCollector()
                    analyzer = SentimentAnalyzer()
                    summary = collector.db.get_market_summary(days=days)
                    bull_ratio = summary.get('bullish_ratio', 0)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("资讯总数", summary.get('total_news', 0))
                    c2.metric("利好数量", summary.get('positive_count', 0))
                    c3.metric("利空数量", summary.get('negative_count', 0))

                    if bull_ratio > 60:
                        st.success(f"市场情绪: 偏暖 🌤️ (看涨比 {bull_ratio}%)")
                    elif bull_ratio < 40:
                        st.error(f"市场情绪: 偏冷 🥶 (看涨比 {bull_ratio}%)")
                    else:
                        st.info(f"市场情绪: 中性 🌥️ (看涨比 {bull_ratio}%)")
                except Exception as e:
                    st.error(f"分析失败: {e}")

    with tab3:
        st.subheader("个股舆情查询")
        sent_code = st.text_input("股票代码", value="600519", key="sent_code").strip()
        sent_days = st.slider("天数", 1, 30, 7, key="sent_code_days")
        if st.button("📊 查询个股舆情", key="sent_query"):
            with st.spinner("查询中..."):
                try:
                    from news.collector import NewsCollector, SentimentAnalyzer
                    collector = NewsCollector()
                    analyzer = SentimentAnalyzer()

                    # 简单处理: 用代码数字
                    import re
                    match = re.search(r'(\d{6})', sent_code)
                    if match:
                        code_num = match.group(1)
                        code_str = f"{code_num}.SH" if code_num.startswith(('6','5','9')) else f"{code_num}.SZ"
                    else:
                        code_str = sent_code

                    result = analyzer.get_stock_sentiment(collector.db, code_str, days=sent_days)
                    sentiment = result.get('sentiment', 0)
                    label = result.get('label', '中性')
                    count = result.get('news_count', 0)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("舆情评分", f"{sentiment:+.2f}" if sentiment else "N/A")
                    if sentiment > 0.2:
                        c2.success(f"情绪: {label}")
                    elif sentiment < -0.2:
                        c2.error(f"情绪: {label}")
                    else:
                        c2.info(f"情绪: {label}")
                    c3.metric("相关资讯数", count)
                except Exception as e:
                    st.error(f"查询失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 页面 6: 告警监控
# ═══════════════════════════════════════════════════════════════════════════
elif page == "告警监控":
    st.header("🔔 股票告警监控")

    st.markdown("""
    **支持告警类型**: 价格达到阈值 | 涨跌幅触发 | 策略信号触发
    
    **推送渠道**: 邮件 (163邮箱) | 钉钉机器人 (需配置 webhook)
    """)

    # 告警规则管理
    st.subheader("添加告警规则")
    with st.form("alert_form"):
        a_col1, a_col2 = st.columns(2)
        alert_code = a_col1.text_input("股票代码", value="600519", key="alert_code")
        alert_name = a_col2.text_input("股票名称", value="贵州茅台", key="alert_name")
        a_col3, a_col4 = st.columns(2)
        alert_type = a_col3.selectbox("告警类型", [
            "price_up", "price_down", "pct_chg", "signal_buy", "signal_sell"
        ], format_func=lambda x: {
            "price_up": "价格达到",
            "price_down": "价格跌破",
            "pct_chg": "涨跌幅触发",
            "signal_buy": "策略 BUY 信号",
            "signal_sell": "策略 SELL 信号",
        }[x])
        threshold = a_col4.number_input("阈值", value=5.0, step=0.5)
        submitted = st.form_submit_button("添加规则")

        if submitted:
            try:
                from monitor.alerts import StockWatcher
                watcher = StockWatcher()
                rule_id = watcher.add_alert(alert_code, alert_name, alert_type, float(threshold))
                st.success(f"规则添加成功: {alert_name}({alert_code}) - {alert_type} {threshold}")
            except Exception as e:
                st.error(f"添加失败: {e}")

    # 告警历史
    st.subheader("最近告警记录")
    try:
        from monitor.alerts import AlertDatabase
        db = AlertDatabase()
        rules = db.get_active_rules()
        if rules:
            rule_data = [{
                "ID": r.id,
                "股票": f"{r.name}({r.ts_code})",
                "类型": r.alert_type,
                "阈值": r.threshold,
                "冷却(分)": r.cooldown_min,
            } for r in rules]
            st.dataframe(pd.DataFrame(rule_data), use_container_width=True, hide_index=True)
        else:
            st.info("暂无告警规则")
    except Exception as e:
        st.error(f"读取告警历史失败: {e}")

    st.caption("⚠️ 告警监控需要在后台运行 `python monitor/alerts.py`")


# ═══════════════════════════════════════════════════════════════════════════
# 页面 7: 每日工作流
# ═══════════════════════════════════════════════════════════════════════════
elif page == "每日工作流":
    st.header("⚙️ 每日自动化工作流")

    st.markdown("""
    一键执行完整量化流程:

    1. 采集财经资讯 (财联社 + 新浪 + 东财)
    2. 生成市场舆情报告
    3. 执行智能选股
    4. 生成多策略信号
    5. 整合完整日报
    6. 发送邮件推送
    """)

    if st.button("🚀 执行完整工作流", type="primary"):
        with st.spinner("工作流执行中，预计需要 2-5 分钟..."):
            try:
                from workflows.daily_workflow import DailyWorkflow
                workflow = DailyWorkflow()
                results = workflow.run(dry_run=False)

                for name, result in results.items():
                    st.markdown(f"**{name}**")
                    if isinstance(result, dict):
                        for k, v in result.items():
                            if k not in ('report', 'content'):
                                st.write(f"  {k}: {v}")

                st.success("✅ 工作流执行完成！")
            except Exception as e:
                st.error(f"工作流失败: {e}")

    st.info("💡 建议使用 Windows 任务计划程序定时执行: `python workflows/daily_workflow.py`")
