"""Wanman 轮次引擎 — 驱动完整的研究→改进循环。

使用 OpenHands SDK 的 Agent + Conversation 机制，为每个角色
创建专用 agent 实例，按 wanman 协议驱动多轮改进循环。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from openhands.sdk import Conversation, Event, MessageEvent

from . import io as agent_io
from .models import (
    BacklogItem,
    Mission,
    Role,
    RoundArtifacts,
    RoundNumber,
    Status,
    WanmanConfig,
)
from .roles import create_llm, create_role_agent

logger = logging.getLogger(__name__)

# ── 阶段提示词模板 ──

_STAGE_PROMPTS: dict[Role, str] = {
    Role.RESEARCH: """你正在执行 wanman 工作流的 **Research** 阶段（第 {round_num} 轮）。

你的任务：
1. 探索当前仓库的代码、文档、测试、TODO、配置
2. 识别问题、机会和改进点
3. 输出结构化研究报告

{context}

请先探索仓库再进行研究。完成后，将你的完整研究报告写入文件：
{artifact_path}

使用以下 Markdown 格式：

```markdown
# 第 {round_num} 轮研究

## 目标

## 发现

## 候选机会

## 推荐下一步

## 风险
```""",
    Role.DEV: """你正在执行 wanman 工作流的 **Dev** 阶段（第 {round_num} 轮）。

当前选中的任务：
{backlog}

请实施最小但有用的闭环改进：
- 优先高杠杆、小范围改动
- 行为变更时同步更新文档和测试
- 如果被阻塞，明确记录原因

完成实现后，将改动总结写入文件：
{artifact_path}""",
    Role.REVIEWER: """你正在执行 wanman 工作流的 **Reviewer** 阶段（第 {round_num} 轮）。

请评审本轮已完成的工作。

不要自己实现代码或修改文件，只做评审。

将评审报告写入文件：
{artifact_path}

格式：
```markdown
# 第 {round_num} 轮评审

## 目标

## 发现

## 验收结论

## 剩余风险

## 必需后续项
```""",
    Role.FEEDBACK: """你正在执行 wanman 工作流的 **Feedback** 阶段（第 {round_num} 轮）。

请根据本轮所有产出，输出反馈报告。

不要自己实现代码或修改文件，把观察转为 backlog 项。

将反馈报告写入文件：
{artifact_path}

格式：
```markdown
# 第 {round_num} 轮反馈

## 已改善项

## 仍存在的问题

## 新机会

## 推荐 backlog 更新
```""",
}

_CEO_SELECTION_PROMPT = """你正在执行 wanman 工作流的 **CEO** 角色 — 选择工作项（第 {round_num} 轮）。

当前 backlog：
{backlog}

当前轮次的研究结果：
{research}

请分析 backlog 和研究结果，选择 1-3 个当前最有价值的工作项。
更新 backlog 文件 {backlog_path}，将选中的工作项放在 Active 区。

工作项格式：- [P1/P2/P3] 标题 - owner: 角色 - status: todo|queued|parked|done

选择原则：
1. 优先选择对项目有明确价值的工作
2. 优先能解锁后续工作的工作
3. 优先最小但完整的改进闭环
"""

_CEO_SUMMARY_PROMPT = """你正在执行 wanman 工作流的 **CEO** 角色 — 收束本轮（第 {round_num} 轮）。

本轮 artifacts：
- 研究：{research}
- 评审：{review}
- 反馈：{feedback}

请完成以下工作：
1. 将本轮总结写入 {summary_path}
2. 更新 {backlog_path}，将已完成项标记为 done，调整下一轮 active 项

总结格式：
```markdown
# 第 {round_num} 轮总结

## 目标

## 动作

## 决策

## 证据

## 风险

## 下一步
```"""


def _extract_assistant_reply(conversation: Conversation) -> str:
    """从 conversation events 中提取 assistant 的最后一条文本回复。"""
    parts: list[str] = []
    for event in conversation.events:
        if isinstance(event, MessageEvent) and event.source == "assistant":
            if event.message:
                parts.append(event.message)
    return "\n".join(parts)


def _extract_all_messages(conversation: Conversation) -> str:
    """从 conversation 中提取所有消息文本。"""
    parts: list[str] = []
    for event in conversation.events:
        if isinstance(event, MessageEvent):
            label = event.source or "unknown"
            msg = event.message or ""
            if msg.strip():
                parts.append(f"[{label}]\n{msg}")
    return "\n\n".join(parts)


class WanmanEngine:
    """Wanman 持续改进循环引擎。

    使用 OpenHands SDK 创建 agent 实例，按轮次协议驱动
    CEO → Research → CEO → Dev → Reviewer → Feedback → CEO 循环。
    """

    def __init__(
        self,
        config: Optional[WanmanConfig] = None,
        workspace: Optional[str] = None,
        verbose: bool = False,
    ):
        self.config = config or WanmanConfig()
        if workspace:
            self.config.workspace = workspace
        if verbose:
            self.config.verbose = verbose

        self._workspace_path = (
            Path(self.config.workspace).resolve()
            if self.config.workspace
            else Path.cwd()
        )
        self._llm: Optional["LLM"] = None
        self._mission: Mission = Mission()

        agent_io.ensure_agent_dir(self.config)
        self._setup_logging()

    def _setup_logging(self) -> None:
        level = logging.DEBUG if self.config.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )

    @property
    def _llm_instance(self):
        if self._llm is None:
            self._llm = create_llm(
                model=self.config.llm_model,
                api_key=self.config.llm_api_key,
                base_url=self.config.llm_base_url,
            )
        return self._llm

    def _get_agent(self, role: Role):
        return create_role_agent(
            role=role,
            llm=self._llm_instance,
            mission=self._mission,
        )

    def _converse(self, role: Role, prompt: str) -> Conversation:
        """用指定角色运行一次对话，返回 Conversation 实例。"""
        agent = self._get_agent(role)
        cwd = str(self._workspace_path)
        conv = Conversation(agent=agent, workspace=cwd)
        conv.send_message(prompt)
        conv.run()
        return conv

    def _load_state(self) -> tuple[RoundNumber, list[BacklogItem], str]:
        """加载当前状态。"""
        self._mission = agent_io.read_mission(self.config)
        current_round = RoundNumber.from_dir(self.config.rounds_dir).next()
        backlog = agent_io.read_backlog(self.config)
        context = agent_io.read_context(self.config)
        return current_round, backlog, context

    def run_round(self) -> bool:
        """执行一轮完整的 wanman 循环。

        Returns:
            True 表示可以继续下一轮，False 表示应该停止。
        """
        round_num, backlog, context = self._load_state()
        artifacts = RoundArtifacts(
            round_number=round_num,
            base_dir=self.config.agent_dir,
        )

        round_tag = f"[第 {round_num} 轮]"
        logger.info("%s === 开始新一轮 ===", round_tag)

        # ── Step 1: CEO 加载状态（隐式：已在 _load_state 中完成）──

        # ── Step 2: Research ──
        logger.info("%s Research 阶段", round_tag)
        ctx_block = f"\n当前上下文：\n{context}" if context else ""
        research_prompt = _STAGE_PROMPTS[Role.RESEARCH].format(
            artifact_path=str(artifacts.research),
            round_num=round_num,
            context=ctx_block,
        )
        research_conv = self._converse(Role.RESEARCH, research_prompt)
        if not artifacts.research.exists():
            reply = _extract_assistant_reply(research_conv)
            if reply.strip():
                agent_io.write_artifact(artifacts.research, reply)
        research_text = agent_io.read_artifact(artifacts.research)
        logger.info("%s Research 完成", round_tag)

        # ── Step 3: CEO 选择工作项 ──
        logger.info("%s CEO 选择工作项", round_tag)
        backlog_str = "\n".join(
            f"- [{b.priority.value}] {b.title} (owner: {b.owner.value})"
            for b in backlog
        )
        selection_prompt = _CEO_SELECTION_PROMPT.format(
            backlog=backlog_str or "（空）",
            research=research_text,
            backlog_path=str(self.config.backlog_file),
            round_num=round_num,
        )
        self._converse(Role.CEO, selection_prompt)

        # 重新读取 backlog
        backlog = agent_io.read_backlog(self.config)
        active_items = [b for b in backlog if b.status == Status.TODO]

        if not active_items:
            logger.warning(
                "%s 没有选中的工作项，停止循环。"
                "请在 backlog.md 中手动添加任务后重试，"
                "或编辑 mission.md 明确项目目标。",
                round_tag,
            )
            return False

        # ── Step 4: Dev ──
        logger.info("%s Dev 阶段", round_tag)
        dev_artifact = artifacts.base_dir / "rounds" / f"{round_num}-implementation.md"
        backlog_str = "\n".join(
            f"- [{b.priority.value}] {b.title} (owner: {b.owner.value})"
            for b in active_items
        )
        dev_prompt = _STAGE_PROMPTS[Role.DEV].format(
            artifact_path=str(dev_artifact),
            backlog=backlog_str,
            round_num=round_num,
        )
        self._converse(Role.DEV, dev_prompt)
        logger.info("%s Dev 完成", round_tag)

        # ── Step 5: Reviewer ──
        logger.info("%s Reviewer 阶段", round_tag)
        review_prompt = _STAGE_PROMPTS[Role.REVIEWER].format(
            artifact_path=str(artifacts.review),
            round_num=round_num,
        )
        review_conv = self._converse(Role.REVIEWER, review_prompt)
        if not artifacts.review.exists():
            reply = _extract_assistant_reply(review_conv)
            if reply.strip():
                agent_io.write_artifact(artifacts.review, reply)
        logger.info("%s Reviewer 完成", round_tag)

        # ── Step 6: Feedback ──
        logger.info("%s Feedback 阶段", round_tag)
        feedback_prompt = _STAGE_PROMPTS[Role.FEEDBACK].format(
            artifact_path=str(artifacts.feedback),
            round_num=round_num,
        )
        feedback_conv = self._converse(Role.FEEDBACK, feedback_prompt)
        if not artifacts.feedback.exists():
            reply = _extract_assistant_reply(feedback_conv)
            if reply.strip():
                agent_io.write_artifact(artifacts.feedback, reply)
        logger.info("%s Feedback 完成", round_tag)

        # ── Step 7: CEO 收束本轮 ──
        logger.info("%s CEO 收束阶段", round_tag)
        summary_prompt = _CEO_SUMMARY_PROMPT.format(
            research=research_text,
            review=agent_io.read_artifact(artifacts.review),
            feedback=agent_io.read_artifact(artifacts.feedback),
            summary_path=str(artifacts.summary),
            backlog_path=str(self.config.backlog_file),
            round_num=round_num,
        )
        self._converse(Role.CEO, summary_prompt)

        # 收集已生成的 artifacts
        produced = []
        for p in [
            artifacts.research,
            artifacts.review,
            artifacts.feedback,
            artifacts.summary,
        ]:
            if p.exists():
                produced.append(p.name)
        logger.info("%s ✓ 完成 (产出: %s)", round_tag, ", ".join(produced))
        return True

    def run(self) -> None:
        """运行多轮循环直到停止条件满足。"""
        for i in range(self.config.max_rounds):
            logger.info("=== 第 %d/%d 轮 ===", i + 1, self.config.max_rounds)
            should_continue = self.run_round()
            if not should_continue:
                break

        backlog = agent_io.read_backlog(self.config)
        active = [b for b in backlog if b.status not in (Status.DONE, Status.PARKED)]
        if active:
            logger.info(
                "引擎暂停。还有 %d 个工作项未完成。再次运行以继续。",
                len(active),
            )
        else:
            logger.info("引擎完成：所有工作项已完成。")
