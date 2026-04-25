"""
Agent Loop Kit — OpenHands SDK 实现的 wanman 风格持续改进循环。

提供稳定的轮次引擎，驱动 AI agent 在多轮循环中持续改进项目。
"""

from .engine import WanmanEngine
from .models import (
    BacklogItem,
    Mission,
    Priority,
    Role,
    RoundArtifacts,
    RoundNumber,
    Status,
    WanmanConfig,
)
from .cli import main as cli_main

__all__ = [
    "WanmanEngine",
    "WanmanConfig",
    "Mission",
    "BacklogItem",
    "RoundArtifacts",
    "RoundNumber",
    "Role",
    "Priority",
    "Status",
    "cli_main",
]
