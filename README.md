# 量化投资决策与复盘系统

这是一个为 A 股市场设计的量化分析与自动化复盘系统。

## 功能概述
- **数据接入**: 自动获取 A 股全市场行情（通过 AKShare 接口）。
- **趋势分析**: 采用 MA/MACD/ADX 多指标趋势跟踪策略。
- **风控体系**: 集成 5 层防御模型（仓位、ATR、回撤熔断）。
- **自动化复盘**: 每日收盘后生成 Markdown 报告，支持邮件自动化推送。
- **Web 可视化**: 基于 Streamlit 的交互式 Web 控制台。

## 目录结构
- `/config`: 核心配置 YAML。
- `/data`: 数据加载与清洗模块。
- `/strategies`: 核心量化策略 (趋势跟踪、因子分析)。
- `/trading`: 风控与仓位管理。
- `/tasks`: 每日自动化任务脚本。
- `/web`: API 后端与前端仪表盘。
- `/reports`: 历史复盘报告存储。

## 快速使用说明

1. **环境初始化**:
   ```bash
   pip install -r requirements.txt
   ```

2. **环境变量设置** (Windows):
   ```cmd
   setx SMTP_PASSWORD "你的邮箱授权码"
   ```

3. **运行交互控制台**:
   - 启动后端: `python web/api_server.py`
   - 启动前端: `streamlit run web/app.py`

4. **自动化每日任务**:
   每日 15:35 定时执行 `run_daily_review.bat`。

---
*注：本项目支持“生产/模拟”双模式，修改 `tasks/daily_review.py` 中的 `mock_mode` 参数即可切换。*
