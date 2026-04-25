"""CLI 入口 — 从命令行运行 wanman 循环。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .engine import WanmanEngine
from .models import WanmanConfig


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agent Loop Kit — wanman 风格的持续改进循环引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  agent-loop                      # 在当前目录运行一轮
  agent-loop --auto               # 自动运行多轮直到完成
  agent-loop --rounds 5           # 最多运行 5 轮
  agent-loop --workspace /path    # 在指定项目目录运行
  agent-loop --model openhands/gpt-4o  # 指定模型
        """,
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动运行多轮直到完成（默认只运行一轮）",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="最大运行轮数（默认：1，与 --auto 一起使用时默认 10）",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        default=None,
        help="目标项目目录（默认：当前目录）",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="LLM 模型标识（默认：环境变量 LLM_MODEL）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="输出详细日志",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="在当前目录初始化 .agent/ 模板文件",
    )
    return parser.parse_args(argv)


def _cmd_init(workspace: str) -> None:
    """初始化 .agent/ 模板文件。"""
    agent_dir = Path(workspace) / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    templates = {
        "mission.md": """# 任务目标

## 总目标

请在这里填写项目目标。

## 成功标准

- 明确定义什么叫"达到目标"

## 约束条件

- 在这里写硬约束

## 范围内

- 在这里写 agent 允许做的事情

## 范围外

- 在这里写不应该做的事情

## 目标对象

- 谁会从这些改进中受益
""",
        "backlog.md": """# Backlog

## Active

- [P1] 请填写当前最有价值的任务 - owner: ceo - status: todo

## Next

- [P2] 请填写下一个待执行任务 - owner: research - status: queued

## Later

- [P3] 请填写延后任务 - owner: feedback - status: parked
""",
        "context.md": """# 上下文

这个文件只记录需要跨多轮保留的稳定信息。

## 稳定事实

- 在这里记录仓库、架构、流程和约束中的稳定事实

## 当前方向

- 在这里记录当前战略方向

## 已知风险

- 在这里记录多轮都持续有效的风险

## 人类偏好

- 在这里记录明确的人类偏好和取舍
""",
    }

    for name, content in templates.items():
        path = agent_dir / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            print(f"  ✓ 创建 {path}")
        else:
            print(f"  - 跳过（已存在）{path}")

    for subdir in ["rounds", "research", "reviews", "feedback"]:
        (agent_dir / subdir).mkdir(exist_ok=True)
        print(f"  ✓ 创建 {agent_dir / subdir}/")

    print(f"\n.agent/ 模板已初始化完毕。请先编辑 {agent_dir / 'mission.md'} 填入项目目标。")


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。"""
    args = _parse_args(argv)

    if args.init:
        workspace = args.workspace or os.getcwd()
        _cmd_init(workspace)
        return 0

    max_rounds = args.rounds
    if max_rounds is None:
        max_rounds = 10 if args.auto else 1

    config = WanmanConfig(
        llm_model=args.model or os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        max_rounds=max_rounds,
        auto_run=args.auto,
        verbose=args.verbose,
        workspace=args.workspace or os.getcwd(),
    )

    engine = WanmanEngine(config=config, verbose=args.verbose)

    if args.auto:
        engine.run()
    else:
        engine.run_round()

    return 0


if __name__ == "__main__":
    sys.exit(main())
