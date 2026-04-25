"""测试 IO 模块。"""

from pathlib import Path

import pytest

from agent_loop_kit.io import (
    ensure_agent_dir,
    read_artifact,
    read_backlog,
    read_context,
    read_latest_artifact,
    read_mission,
    write_artifact,
    write_backlog,
    write_context,
)
from agent_loop_kit.models import (
    BacklogItem,
    Priority,
    Role,
    Status,
    WanmanConfig,
)


class TestEnsureAgentDir:
    def test_creates_directories(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path / ".agent")
        ensure_agent_dir(config)
        assert config.rounds_dir.exists()
        assert config.research_dir.exists()
        assert config.reviews_dir.exists()
        assert config.feedback_dir.exists()

    def test_idempotent(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path / ".agent")
        ensure_agent_dir(config)
        ensure_agent_dir(config)  # 不应抛出异常


class TestReadWriteBacklog:
    def test_empty_file(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path)
        items = read_backlog(config)
        assert items == []

    def test_roundtrip(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path)
        original = [
            BacklogItem(
                title="任务一",
                priority=Priority.P1,
                owner=Role.DEV,
                status=Status.TODO,
            ),
            BacklogItem(
                title="任务二",
                priority=Priority.P2,
                owner=Role.RESEARCH,
                status=Status.QUEUED,
            ),
            BacklogItem(
                title="任务三",
                priority=Priority.P3,
                owner=Role.FEEDBACK,
                status=Status.PARKED,
            ),
            BacklogItem(
                title="已完成的",
                priority=Priority.P1,
                owner=Role.CEO,
                status=Status.DONE,
            ),
        ]
        write_backlog(config, original)
        loaded = read_backlog(config)
        assert len(loaded) == 4
        assert loaded[0].title == "任务一"
        assert loaded[0].priority == Priority.P1
        assert loaded[0].owner == Role.DEV
        assert loaded[0].status == Status.TODO
        assert loaded[1].status == Status.QUEUED
        assert loaded[2].status == Status.PARKED
        assert loaded[3].status == Status.DONE

    def test_read_realistic(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path)
        config.backlog_file.write_text(
            "# Backlog\n\n"
            "## Active\n\n"
            "- [P1] 重构核心模块 - owner: dev - status: todo\n\n"
            "## Next\n\n"
            "- [P2] 添加测试 - owner: dev - status: queued\n\n"
            "## Later\n\n"
            "- [P3] 优化文档 - owner: feedback - status: parked\n\n"
            "## Done\n\n"
            "- [P1] 初始化项目 - owner: ceo - status: done\n",
            encoding="utf-8",
        )
        items = read_backlog(config)
        assert len(items) == 4
        assert items[0].title == "重构核心模块"
        assert items[0].status == Status.TODO
        assert items[1].title == "添加测试"
        assert items[1].status == Status.QUEUED
        assert items[2].title == "优化文档"
        assert items[2].status == Status.PARKED
        assert items[3].title == "初始化项目"
        assert items[3].status == Status.DONE


class TestReadWriteContext:
    def test_empty(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path)
        assert read_context(config) == ""

    def test_roundtrip(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path)
        write_context(config, "## 稳定事实\n\n- Python 3.12\n")
        assert read_context(config) == "## 稳定事实\n\n- Python 3.12\n"


class TestReadWriteArtifact:
    def test_write_and_read(self, tmp_path: Path):
        path = tmp_path / "research" / "1-research.md"
        write_artifact(path, "# 研究结果\n\n内容")
        assert path.exists()
        assert read_artifact(path) == "# 研究结果\n\n内容"

    def test_read_nonexistent(self, tmp_path: Path):
        assert read_artifact(tmp_path / "nothing.md") == ""

    def test_latest_artifact(self, tmp_path: Path):
        (tmp_path / "1-research.md").write_text("第一轮")
        (tmp_path / "2-research.md").write_text("第二轮")
        result = read_latest_artifact(tmp_path)
        # 按字母倒序，2 > 1
        assert "第二轮" in result


class TestReadMission:
    def test_from_config(self, tmp_path: Path):
        config = WanmanConfig(agent_dir=tmp_path)
        (tmp_path / "mission.md").write_text(
            "## 总目标\n\n测试目标\n\n## 成功标准\n\n- 标准1\n",
            encoding="utf-8",
        )
        mission = read_mission(config)
        assert mission.goal == "测试目标"
        assert mission.success_criteria == ["标准1"]
