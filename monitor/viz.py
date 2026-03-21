from pyecharts import options as opts
from pyecharts.charts import Line, Kline
import os

def render_interactive_chart(df, output_path="./monitor/trend_plot.html"):
    """使用 pyecharts 渲染交互式图表"""
    # 确保监控目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 基础线图
    line = (
        Line(init_opts=opts.InitOpts(width="1000px", height="500px", page_title="量化交易策略视图"))
        .add_xaxis(df.index.strftime('%Y-%m-%d').tolist())
        .add_yaxis("收盘价", df['close'].tolist(), is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="趋势交易策略 - 股价走势"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(name="日期"),
            yaxis_opts=opts.AxisOpts(name="价格"),
        )
    )
    
    # 标记买卖点示例 (可以在 dataframe 中增加 signal 列)
    if 'signal' in df.columns:
        line.add_yaxis("交易信号", df['signal'].tolist(), symbol="pin", symbol_size=20)

    line.render(output_path)
    print(f"交互式图表已生成: {os.path.abspath(output_path)}")
