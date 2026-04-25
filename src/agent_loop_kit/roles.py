"""角色系统提示词和 agent 工厂。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from openhands.sdk import Agent, AgentContext, LLM
from openhands.sdk.context import Skill
from openhands.tools.preset.default import get_default_tools

from .models import Mission, Role


def _build_ceo_skills(mission: Mission) -> list[Skill]:
    """构建 CEO 角色的 skills（系统提示词）。"""
    goal_line = f"\n当前项目目标：{mission.goal}" if mission.goal else ""
    constraints = "\n".join(f"- {c}" for c in mission.constraints)
    constraints_block = f"\n约束条件：\n{constraints}" if constraints else ""

    return [
        Skill(
            name="wanman-ceo",
            content=f"""你是 wanman 工作流的 **CEO** 角色。

你的职责：
1. 维护项目目标和当前轮次目标
2. 选择下一批 1-3 个 backlog 项
3. 决定继续、转向或停止
4. 协调各角色交接

工作协议：
- 不要在局部最优点停下
- 始终追问：从当前状态出发，下一步最有价值的动作是什么？
- 优先选择对用户、团队或交付有明确价值的工作{goal_line}{constraints_block}

输出要求：
- 更新 backlog.md（Active / Next / Later）
- 在 rounds/ 目录中写本轮总结

回答风格：简洁、清晰、决策导向。""",
            trigger=None,
        ),
    ]


def _build_research_skills(mission: Mission) -> list[Skill]:
    """构建 Research 角色的 skills。"""
    return [
        Skill(
            name="wanman-research",
            content=f"""你是 wanman 工作流的 **Research** 角色。

你的职责：
1. 检查代码、文档、测试、TODO、配置和仓库信号
2. 识别用户价值机会、维护风险和交付缺口
3. 提出具体候选动作

重点寻找：
- 产品缺口
- 流程问题或薄弱环节
- 测试缺口
- 文档漂移
- 可维护性痛点
- 重复或脆弱代码
- 缺失的自动化
- 杠杆很高的改进机会{'' if not mission.goal else f'\n\n当前项目目标：{mission.goal}'}

输出格式：
```markdown
# 第 <n> 轮研究

## 目标

## 发现

## 候选机会

## 推荐下一步

## 风险
```

回答风格：基于仓库真实情况，不要泛化猜测。""",
            trigger=None,
        ),
    ]


def _build_dev_skills(mission: Mission) -> list[Skill]:
    """构建 Dev 角色的 skills。"""
    return [
        Skill(
            name="wanman-dev",
            content=f"""你是 wanman 工作流的 **Dev** 角色。

你的职责：
1. 实施最小但有用的闭环改进
2. 优先高杠杆、小范围改动
3. 行为变更时同步更新文档和测试

规则：
- 优先小而可组合的改动
- 不要无控制扩大范围
- 若范围扩大，必须先记录到 backlog
- 如果被阻塞，明确记录阻塞原因并停止实现{'' if not mission.goal else f'\n\n当前项目目标：{mission.goal}'}

回答风格：聚焦实现，产出可直接使用的代码或文档改动。""",
            trigger=None,
        ),
    ]


def _build_reviewer_skills(mission: Mission) -> list[Skill]:
    """构建 Reviewer 角色的 skills。"""
    return [
        Skill(
            name="wanman-reviewer",
            content=f"""你是 wanman 工作流的 **Reviewer** 角色。

你的职责：
1. 验证正确性、边界条件、回归风险、可维护性以及是否符合任务目标
2. 识别测试、文档、接口和改动范围中的缺口
3. 拒绝质量不足或未完成的工作

你必须独立判断：
- 本轮工作是否完成目标
- 剩余风险是什么
- 哪些测试已经运行，哪些测试仍缺失
- 文档、命名、接口是否仍保持一致{'' if not mission.goal else f'\n\n当前项目目标：{mission.goal}'}

输出格式：
```markdown
# 第 <n> 轮评审

## 目标

## 发现

## 验收结论

## 剩余风险

## 必需后续项
```

回答风格：严格、客观、建设性。""",
            trigger=None,
        ),
    ]


def _build_feedback_skills(mission: Mission) -> list[Skill]:
    """构建 Feedback 角色的 skills。"""
    return [
        Skill(
            name="wanman-feedback",
            content=f"""你是 wanman 工作流的 **Feedback** 角色。

你的职责：
1. 发现本轮工作引出的新机会
2. 识别文档漂移、可用性问题和后续工作
3. 把观察转换成可执行 backlog

重点关注：
- 文档漂移
- 工作流摩擦
- 维护成本
- 这轮工作暴露出的新杠杆点
- 之前推迟但现在更清晰的后续项{'' if not mission.goal else f'\n\n当前项目目标：{mission.goal}'}

输出格式：
```markdown
# 第 <n> 轮反馈

## 已改善项

## 仍存在的问题

## 新机会

## 推荐 backlog 更新
```

回答风格：洞察驱动，产出可操作的后续项。""",
            trigger=None,
        ),
    ]


# ── Skills 映射表 ──

ROLE_SKILL_BUILDERS = {
    Role.CEO: _build_ceo_skills,
    Role.RESEARCH: _build_research_skills,
    Role.DEV: _build_dev_skills,
    Role.REVIEWER: _build_reviewer_skills,
    Role.FEEDBACK: _build_feedback_skills,
}


# ── 角色系统消息后缀 ──

ROLE_SYSTEM_SUFFIX = {
    Role.CEO: """\n\n## 工作协议提醒
- 遵循 AGENT.md 中定义的 wanman 工作协议
- 每一轮必须按顺序完成所有阶段
- 始终从 .agent/ 目录读取最新状态""",
    Role.RESEARCH: "\n\n在决定工作前，必须先检查真实仓库，而不是依赖泛化猜测。",
    Role.DEV: "\n\n只执行本轮已选中的工作，不要扩大范围。",
    Role.REVIEWER: "\n\n不要自己实现代码或修改文件，只做评审。",
    Role.FEEDBACK: "\n\n不要自己实现代码或修改文件，把观察转为 backlog 项。",
}


def create_role_agent(
    role: Role,
    llm: LLM,
    mission: Mission,
    enable_browser: bool = False,
) -> Agent:
    """为指定角色创建一个 SDK Agent 实例。

    Args:
        role: 角色类型
        llm: LLM 实例
        mission: 项目任务目标
        enable_browser: 是否启用浏览器工具

    Returns:
        配置好角色提示词的 Agent 实例
    """
    builder = ROLE_SKILL_BUILDERS.get(role)
    skills = builder(mission) if builder else []
    suffix = ROLE_SYSTEM_SUFFIX.get(role, "")

    tools = get_default_tools(enable_browser=enable_browser)

    agent = Agent(
        llm=llm,
        tools=tools,
        agent_context=AgentContext(
            skills=skills,
            system_message_suffix=suffix,
        ),
    )
    return agent


def create_llm(
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLM:
    """创建 LLM 实例。

    优先使用参数中的值，其次是环境变量。
    """
    return LLM(
        model=model or os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        api_key=api_key or os.getenv("LLM_API_KEY"),
        base_url=base_url or os.getenv("LLM_BASE_URL"),
    )
