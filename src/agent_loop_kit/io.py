""".agent/ 目录下状态文件的读写管理。"""

from __future__ import annotations

from pathlib import Path

from .models import BacklogItem, Mission, Priority, Role, Status, WanmanConfig


def ensure_agent_dir(config: WanmanConfig) -> None:
    """确保 .agent/ 目录及子目录存在。"""
    for d in [
        config.agent_dir,
        config.rounds_dir,
        config.research_dir,
        config.reviews_dir,
        config.feedback_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)


def read_mission(config: WanmanConfig) -> Mission:
    """读取任务目标。"""
    return Mission.from_file(config.mission_file)


def write_backlog(config: WanmanConfig, items: list[BacklogItem]) -> None:
    """将 backlog 写入文件。"""
    active = [i for i in items if i.status == Status.TODO]
    next_items = [i for i in items if i.status == Status.QUEUED]
    later = [i for i in items if i.status == Status.PARKED]
    done = [i for i in items if i.status == Status.DONE]

    lines = ["# Backlog\n"]
    if active:
        lines.append("## Active\n")
        for item in active:
            lines.append(
                f"- [{item.priority.value}] {item.title}"
                f" - owner: {item.owner.value} - status: {item.status.value}\n"
            )
        lines.append("\n")
    if next_items:
        lines.append("## Next\n")
        for item in next_items:
            lines.append(
                f"- [{item.priority.value}] {item.title}"
                f" - owner: {item.owner.value} - status: {item.status.value}\n"
            )
        lines.append("\n")
    if later:
        lines.append("## Later\n")
        for item in later:
            lines.append(
                f"- [{item.priority.value}] {item.title}"
                f" - owner: {item.owner.value} - status: {item.status.value}\n"
            )
        lines.append("\n")
    if done:
        lines.append("## Done\n")
        for item in done:
            lines.append(
                f"- [{item.priority.value}] {item.title}"
                f" - owner: {item.owner.value} - status: {item.status.value}\n"
            )
        lines.append("\n")

    config.backlog_file.write_text("".join(lines), encoding="utf-8")


def read_backlog(config: WanmanConfig) -> list[BacklogItem]:
    """从文件读取 backlog。"""
    if not config.backlog_file.exists():
        return []
    text = config.backlog_file.read_text(encoding="utf-8")
    items = []
    current_section = Status.TODO

    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("## Active"):
            current_section = Status.TODO
        elif line_stripped.startswith("## Next"):
            current_section = Status.QUEUED
        elif line_stripped.startswith("## Later"):
            current_section = Status.PARKED
        elif line_stripped.startswith("## Done"):
            current_section = Status.DONE
        elif line_stripped.startswith("- [") and "] " in line_stripped:
            # 解析: - [P1] 标题 - owner: role - status: xxx
            rest = line_stripped[2:]  # 去掉 "- "
            prio_end = rest.index("]")
            priority = Priority(rest[1:prio_end])
            rest = rest[prio_end + 1 :].strip()

            owner = Role.CEO
            status = current_section

            if " - owner: " in rest:
                parts = rest.split(" - owner: ")
                title = parts[0].strip()
                rest2 = parts[1]
                if " - status: " in rest2:
                    owner_str, status_str = rest2.split(" - status: ")
                    owner = Role(owner_str.strip())
                    status = Status(status_str.strip())
                else:
                    owner = Role(rest2.strip())
            elif " - status: " in rest:
                title, _ = rest.split(" - status: ")
            else:
                title = rest

            items.append(
                BacklogItem(
                    title=title,
                    priority=priority,
                    owner=owner,
                    status=status,
                )
            )

    return items


def read_context(config: WanmanConfig) -> str:
    """读取 context.md 内容。"""
    if config.context_file.exists():
        return config.context_file.read_text(encoding="utf-8")
    return ""


def write_context(config: WanmanConfig, content: str) -> None:
    """写入 context.md。"""
    config.context_file.write_text(content, encoding="utf-8")


def write_artifact(path: Path, content: str) -> None:
    """写入 artifact 文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_artifact(path: Path) -> str:
    """读取 artifact 文件。"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def read_latest_artifact(directory: Path) -> str:
    """读取目录中最新的 artifact 文件。"""
    if not directory.exists():
        return ""
    files = sorted(directory.glob("*.md"), reverse=True)
    for f in files:
        return f.read_text(encoding="utf-8")
    return ""
