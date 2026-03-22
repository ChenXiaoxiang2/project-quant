"""
多 Agent 协作框架 - Manager
基于 OpenCode 原生 Agent 能力，构建软件开发全生命周期协作流水线。

Agent 角色定义:
  - Librarian  → Research Agent    (调研外部资料、技术选型)
  - Explore    → Data Agent       (分析代码结构、模式)
  - Oracle     → Strategy Agent   (架构决策、复杂逻辑)
  - Momus      → Review Agent     (代码审查、最佳实践)
  - Ultrabrain → Developer Agent  (硬核逻辑实现)

使用方法:
  manager = AgentManager(project_root="project")
  result = manager.run_task("为股票数据添加缓存层")
  result = manager.run_workflow("daily_review")
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

# Agent 配置
AGENT_PROMPTS = {
    "research": """你是一个专业的研究员 Agent。请对以下问题进行深入调研:
        
问题: {task}

要求:
1. 搜索多个权威来源（GitHub、官方文档、技术博客）
2. 提供至少 3 个不同的解决方案或思路
3. 评估各方案的优缺点和适用场景
4. 给出明确的推荐意见及理由

输出格式:
## 调研结论
### 方案对比
| 方案 | 优点 | 缺点 | 推荐度 |
|---|---|---|---|
| ... | ... | ... | ... |
### 推荐方案
[具体推荐及理由]
""",

    "develop": """你是一个资深 Python 开发 Agent。请实现以下功能:

任务: {task}
项目根目录: {project_root}

要求:
1. 严格遵循现有代码风格和架构模式
2. 使用绝对路径
3. 添加完善的错误处理
4. 不引入不必要的依赖
5. 最小化变更，只改必须改的部分

现有代码结构参考:
{code_structure}

请直接输出代码，不要解释。""",

    "review": """你是一个严格的代码审查 Agent。请审查以下代码变更:

代码: {task}

审查维度:
1. 逻辑正确性 - 有无 bug 风险？
2. 安全性 - 有无注入/泄漏风险？
3. 性能 - 是否有性能瓶颈？
4. 可维护性 - 代码是否清晰易懂？
5. 测试覆盖 - 是否有边界情况未覆盖？

输出格式:
## 审查结论
### 问题列表
- [P0] 严重问题: ...
- [P1] 重要问题: ...
- [P2] 建议改进: ...
### 总体评价
[通过/需要修改]
""",

    "strategy": """你是一个量化策略架构师 Agent。请解决以下策略设计问题:

问题: {task}

约束条件:
1. 必须是趋势跟踪策略，避开龙头战法
2. 资本保全优先于收益最大化
3. 回测数据必须使用 Baostock/腾讯直调的真实数据
4. 信号生成必须可解释

请输出:
1. 策略设计思路
2. 核心参数及依据
3. 风险控制措施
4. 参考实现代码框架
""",
}


@dataclass
class AgentTask:
    task_id: str
    role: str  # research / develop / review / strategy
    prompt: str
    status: str = "pending"  # pending / running / done / failed
    result: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AgentManager:
    """
    Manager Agent — 协调所有专业 Agent 的总控节点。
    
    工作流程:
    1. 接收任务请求
    2. 分析任务类型，选择合适的 Agent
    3. 分发任务给专业 Agent (librarian / explore / oracle / momus / ultrabrain)
    4. 收集结果，汇总报告
    5. 必要时触发 Review 循环
    """

    def __init__(self, project_root: str = "project"):
        self.project_root = project_root
        self.tasks: dict[str, AgentTask] = {}
        self.task_counter = 0
        self.results_history: list[dict] = []

    def _gen_id(self) -> str:
        self.task_counter += 1
        return f"task_{self.task_counter:04d}"

    def _get_project_structure(self) -> str:
        """获取项目代码结构快照"""
        try:
            result = []
            for root, dirs, files in os.walk(self.project_root):
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'logs', 'reports', 'node_modules')]
                level = root.replace(self.project_root, '').count(os.sep)
                indent = ' ' * 2 * level
                result.append(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in sorted(files):
                    if file.endswith(('.py', '.yaml', '.yml', '.md')):
                        result.append(f"{subindent}{file}")
            return '\n'.join(result[:60])  # 限制输出长度
        except Exception as e:
            return f"无法读取项目结构: {e}"

    # ── 公开 API ──────────────────────────────────────────────────────────────

    def run_task(
        self,
        task: str,
        role: str = "develop",
        category: str = "unspecified-high",
        session_id: Optional[str] = None,
        require_review: bool = True,
    ) -> dict:
        """
        运行单个任务，由 Manager 分配给合适的 Agent。
        
        Args:
            task: 任务描述
            role: Agent 角色 (research/develop/review/strategy)
            category: 任务分类 (用于选择模型)
            session_id: 继续已有会话
            require_review: 是否需要 Review Agent 审查
        
        Returns:
            包含任务结果的字典
        """
        task_id = self._gen_id()
        agent_task = AgentTask(
            task_id=task_id,
            role=role,
            prompt=task,
            created_at=datetime.now().isoformat(),
        )
        self.tasks[task_id] = agent_task

        # 构建 prompt
        if role == "develop":
            prompt = AGENT_PROMPTS["develop"].format(
                task=task,
                project_root=self.project_root,
                code_structure=self._get_project_structure(),
            )
        elif role == "research":
            prompt = AGENT_PROMPTS["research"].format(task=task)
        elif role == "review":
            prompt = AGENT_PROMPTS["review"].format(task=task)
        elif role == "strategy":
            prompt = AGENT_PROMPTS["strategy"].format(task=task)
        else:
            prompt = task

        # 选择 Agent
        subagent_map = {
            "research": "librarian",
            "review": "momus",
            "strategy": "oracle",
        }
        subagent_type = subagent_map.get(role, None)

        # 执行任务
        print(f"[Manager] 分发任务 {task_id} → {role} Agent")

        if subagent_type:
            result = self._run_subagent(
                subagent_type=subagent_type,
                prompt=prompt,
                category=category,
                session_id=session_id,
            )
        else:
            # ultrabrain 或 unspecified
            result = self._run_subagent(
                subagent_type="ultrabrain" if category == "ultrabrain" else None,
                prompt=prompt,
                category=category,
                session_id=session_id,
            )

        agent_task.status = "done"
        agent_task.result = result.get("output", str(result))
        agent_task.completed_at = datetime.now().isoformat()

        # 可选: 触发 Review
        if require_review and role == "develop":
            print(f"[Manager] 触发 Code Review → {task_id}")
            review_result = self.run_task(
                task=f"审查以下代码变更（任务ID: {task_id}）:\n{(agent_task.result or '')[:3000]}",
                role="review",
                require_review=False,
            )
            agent_task.result = f"【开发】{agent_task.result}\n\n【审查】{review_result['result']}"

        record = {
            "task_id": task_id,
            "role": role,
            "task": task[:100],
            "status": "done",
            "result_preview": agent_task.result[:200] if agent_task.result else "",
        }
        self.results_history.append(record)
        return record

    def run_workflow(self, workflow_name: str, **kwargs) -> dict:
        """
        运行预定义工作流 (如 daily_review / stock_screening)
        """
        print(f"[Manager] 执行工作流: {workflow_name}")
        workflows = {
            "daily_review": self._workflow_daily_review,
            "stock_screening": self._workflow_stock_screening,
            "strategy_backtest": self._workflow_strategy_backtest,
            "full_pipeline": self._workflow_full_pipeline,
        }
        if workflow_name not in workflows:
            return {"error": f"未知工作流: {workflow_name}"}
        return workflows[workflow_name](**kwargs)

    def get_status(self) -> dict:
        """获取所有任务状态"""
        return {
            "total_tasks": len(self.tasks),
            "done": sum(1 for t in self.tasks.values() if t.status == "done"),
            "pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "recent": self.results_history[-10:],
        }

    # ── 子 Agent 调用 ──────────────────────────────────────────────────────────

    def _run_subagent(
        self,
        prompt: str,
        category: str = "unspecified-high",
        subagent_type: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """通过 task() 调用子 Agent (task 由 OpenCode 框架注入)"""
        import builtins
        _task = getattr(builtins, 'task', None)
        if _task is None:
            return {"output": "OpenCode task function not available", "status": "error"}
        try:
            result = _task(
                category=category,
                load_skills=[],
                prompt=prompt,
                run_in_background=False,
                subagent_type=subagent_type,
                session_id=session_id,
            )
            return {"output": result, "status": "success"}
        except Exception as e:
            return {"output": f"Agent 执行失败: {e}", "status": "error"}

    # ── 预定义工作流 ──────────────────────────────────────────────────────────

    def _workflow_daily_review(self, **kwargs) -> dict:
        """每日复盘工作流"""
        print("[Workflow] 启动每日复盘...")
        
        # Step 1: Research - 获取今日市场数据概况
        self.run_task(
            task="调研今日A股市场概况，找出涨幅前5行业和热门概念板块",
            role="research",
            require_review=False,
        )
        
        # Step 2: Stock Screening
        self.run_task(
            task="基于多因子筛选: ROE>10%, 净利润增速>10%, 资产负债率<60%, 股价站上20日均线",
            role="develop",
            require_review=False,
        )
        
        # Step 3: Strategy signals
        self.run_task(
            task="为筛选出的股票生成双均线交叉策略信号",
            role="strategy",
            require_review=False,
        )

        # Step 4: 生成报告
        try:
            sys.path.insert(0, self.project_root)
            from tasks.daily_review import generate_production_report
            generate_production_report()
            report_status = "报告生成成功"
        except Exception as e:
            report_status = f"报告生成失败: {e}"

        return {
            "workflow": "daily_review",
            "status": "completed",
            "report": report_status,
            "timestamp": datetime.now().isoformat(),
        }

    def _workflow_stock_screening(self, factors: Optional[dict] = None, **kwargs) -> dict:
        """智能选股工作流"""
        print("[Workflow] 启动智能选股...")
        
        factors = factors or {
            "roe_min": 10,
            "profit_growth_min": 10,
            "debt_max": 60,
            "pe_max": 30,
            "volume_boost": 1.5,
        }

        self.run_task(
            task=f"实现多因子选股引擎，支持条件: {factors}",
            role="develop",
            require_review=False,
        )

        return {"workflow": "stock_screening", "status": "completed"}

    def _workflow_strategy_backtest(self, strategy_name: str = "dual_ma", **kwargs) -> dict:
        """策略回测工作流"""
        print(f"[Workflow] 启动策略回测: {strategy_name}")
        
        self.run_task(
            task=f"实现 {strategy_name} 策略的回测模块，使用 Baostock 历史数据",
            role="develop",
            require_review=False,
        )

        return {"workflow": "strategy_backtest", "status": "completed"}

    def _workflow_full_pipeline(self, **kwargs) -> dict:
        """完整流水线: 资讯 → 选股 → 策略 → 报告"""
        print("[Workflow] 启动完整开发流水线...")
        
        # 1. 资讯聚合
        self.run_task(
            task="实现财经新闻爬虫，支持财联社、华尔街见闻，数据存入 SQLite",
            role="develop",
            require_review=False,
        )
        
        # 2. 智能选股
        self.run_task(
            task="实现多因子+技术形态选股引擎",
            role="develop",
            require_review=False,
        )
        
        # 3. 策略增强
        self.run_task(
            task="增加布林带、RSI超卖、海龟交易策略",
            role="develop",
            require_review=False,
        )
        
        # 4. 告警监控
        self.run_task(
            task="实现价格/成交量异动监控，支持邮件和钉钉推送",
            role="develop",
            require_review=False,
        )
        
        # 5. 报告生成
        self.run_task(
            task="更新 Web UI，增加资讯、选股、策略、告警页面",
            role="develop",
            require_review=False,
        )

        return {"workflow": "full_pipeline", "status": "completed"}


# ── 便捷入口函数 ─────────────────────────────────────────────────────────────

def quick_task(task: str, role: str = "develop") -> dict:
    """一行执行: quick_task('实现xx功能')"""
    manager = AgentManager(project_root="project")
    return manager.run_task(task, role=role)


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Manager 初始化完成")
    print("=" * 60)
    print("用法示例:")
    print("  quick_task('为股票数据添加Redis缓存')")
    print("  manager = AgentManager()")
    print("  manager.run_workflow('daily_review')")
    print("  manager.run_workflow('full_pipeline')")
