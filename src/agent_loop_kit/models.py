"""数据模型定义。"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Wanman 工作流中的角色。"""

    CEO = "ceo"
    RESEARCH = "research"
    DEV = "dev"
    REVIEWER = "reviewer"
    FEEDBACK = "feedback"


class Priority(str, Enum):
    """Backlog 优先级。"""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Status(str, Enum):
    """任务状态。"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    QUEUED = "queued"
    PARKED = "parked"


class RoundNumber(BaseModel):
    """轮次编号。"""

    number: int = Field(default=0, ge=0)

    def next(self) -> RoundNumber:
        return RoundNumber(number=self.number + 1)

    def __str__(self) -> str:
        return str(self.number)

    def __int__(self) -> int:
        return self.number

    @classmethod
    def from_dir(cls, rounds_dir: Path) -> RoundNumber:
        """从 rounds 目录中读取最新轮次编号。"""
        if not rounds_dir.exists():
            return cls(number=0)
        max_n = 0
        for f in rounds_dir.iterdir():
            if f.suffix == ".md":
                m = re.match(r"(\d+)-summary", f.stem)
                if m:
                    max_n = max(max_n, int(m.group(1)))
        return cls(number=max_n)


class BacklogItem(BaseModel):
    """Backlog 中的单个任务项。"""

    title: str
    priority: Priority = Priority.P2
    owner: Role = Role.CEO
    status: Status = Status.TODO


class Mission(BaseModel):
    """任务目标定义。"""

    goal: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> Mission:
        """从 mission.md 文件解析。"""
        if not path.exists():
            return cls()
        text = path.read_text(encoding="utf-8")
        return cls(
            goal=_extract_section(text, "总目标", single_line=True),
            success_criteria=_extract_bullets(text, "成功标准"),
            constraints=_extract_bullets(text, "约束条件"),
            in_scope=_extract_bullets(text, "范围内"),
            out_of_scope=_extract_bullets(text, "范围外"),
            audience=_extract_bullets(text, "目标对象"),
        )


class RoundArtifacts(BaseModel):
    """一轮产生的所有 artifact 路径。"""

    round_number: RoundNumber
    base_dir: Path

    @property
    def research(self) -> Path:
        return self.base_dir / "research" / f"{self.round_number}-research.md"

    @property
    def review(self) -> Path:
        return self.base_dir / "reviews" / f"{self.round_number}-review.md"

    @property
    def feedback(self) -> Path:
        return self.base_dir / "feedback" / f"{self.round_number}-feedback.md"

    @property
    def summary(self) -> Path:
        return self.base_dir / "rounds" / f"{self.round_number}-summary.md"


class WanmanConfig(BaseModel):
    """Wanman 引擎配置。"""

    agent_dir: Path = Field(default=Path(".agent"))
    llm_model: str = Field(
        default="anthropic/claude-sonnet-4-5-20250929",
        description="LLM 模型标识",
    )
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    max_rounds: int = Field(default=10, ge=1)
    auto_run: bool = False
    verbose: bool = False
    workspace: Optional[str] = None

    @property
    def mission_file(self) -> Path:
        return self.agent_dir / "mission.md"

    @property
    def backlog_file(self) -> Path:
        return self.agent_dir / "backlog.md"

    @property
    def context_file(self) -> Path:
        return self.agent_dir / "context.md"

    @property
    def rounds_dir(self) -> Path:
        return self.agent_dir / "rounds"

    @property
    def research_dir(self) -> Path:
        return self.agent_dir / "research"

    @property
    def reviews_dir(self) -> Path:
        return self.agent_dir / "reviews"

    @property
    def feedback_dir(self) -> Path:
        return self.agent_dir / "feedback"


# ── 辅助解析函数 ──


def _extract_section(text: str, heading: str, single_line: bool = False) -> str:
    """从 Markdown 文本中提取指定标题下的内容。"""
    # 匹配 ## heading 或 ### heading
    pattern = re.compile(
        rf"^#{{1,4}}\s+{re.escape(heading)}\s*$(.+?)(?=^#|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return ""
    content = m.group(1).strip()
    if single_line:
        # 取第一行非空内容
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("-"):
                return line
    return content


def _extract_bullets(text: str, heading: str) -> list[str]:
    """从 Markdown 文本中提取指定标题下的列表项。"""
    section = _extract_section(text, heading)
    if not section:
        return []
    bullets = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            bullets.append(line[2:].strip())
    return bullets
