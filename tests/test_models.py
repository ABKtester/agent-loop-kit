"""测试数据模型模块。"""

from pathlib import Path

import pytest

from agent_loop_kit.models import (
    BacklogItem,
    Mission,
    Priority,
    Role,
    RoundNumber,
    Status,
    WanmanConfig,
    _extract_bullets,
    _extract_section,
)


class TestRoundNumber:
    def test_default(self):
        r = RoundNumber()
        assert r.number == 0
        assert str(r) == "0"
        assert int(r) == 0

    def test_next(self):
        r = RoundNumber(number=3)
        r2 = r.next()
        assert int(r2) == 4
        assert r == RoundNumber(number=3)  # 不修改原始值

    def test_from_dir_empty(self, tmp_path: Path):
        r = RoundNumber.from_dir(tmp_path)
        assert int(r) == 0

    def test_from_dir_with_files(self, tmp_path: Path):
        (tmp_path / "3-summary.md").touch()
        (tmp_path / "5-summary.md").touch()
        (tmp_path / "1-summary.md").touch()
        r = RoundNumber.from_dir(tmp_path)
        assert int(r) == 5

    def test_from_dir_ignores_non_summary(self, tmp_path: Path):
        (tmp_path / "10-feedback.md").touch()
        (tmp_path / "2-summary.md").touch()
        r = RoundNumber.from_dir(tmp_path)
        assert int(r) == 2


class TestMission:
    def test_empty(self):
        m = Mission()
        assert m.goal == ""

    def test_from_file_not_exists(self, tmp_path: Path):
        m = Mission.from_file(tmp_path / "nonexistent.md")
        assert m.goal == ""

    def test_from_file_with_content(self, tmp_path: Path):
        content = """# 任务目标

## 总目标

实现一个持续改进循环引擎。

## 成功标准

- 测试覆盖率达到 80%
- 文档完整

## 约束条件

- 使用 OpenHands SDK
- Python 3.12+
"""
        path = tmp_path / "mission.md"
        path.write_text(content, encoding="utf-8")
        m = Mission.from_file(path)
        assert m.goal == "实现一个持续改进循环引擎。"
        assert len(m.success_criteria) == 2
        assert m.success_criteria[0] == "测试覆盖率达到 80%"
        assert m.constraints[0] == "使用 OpenHands SDK"


class TestBacklogItem:
    def test_defaults(self):
        item = BacklogItem(title="测试任务")
        assert item.priority == Priority.P2
        assert item.owner == Role.CEO
        assert item.status == Status.TODO

    def test_custom(self):
        item = BacklogItem(
            title="重要任务",
            priority=Priority.P1,
            owner=Role.DEV,
            status=Status.IN_PROGRESS,
        )
        assert item.priority == Priority.P1
        assert item.owner == Role.DEV
        assert item.status == Status.IN_PROGRESS


class TestWanmanConfig:
    def test_defaults(self):
        config = WanmanConfig()
        assert config.agent_dir == Path(".agent")
        assert config.max_rounds == 10
        assert config.auto_run is False

    def test_subdirs(self):
        config = WanmanConfig(agent_dir=Path("/tmp/test-agent"))
        assert config.mission_file == Path("/tmp/test-agent/mission.md")
        assert config.backlog_file == Path("/tmp/test-agent/backlog.md")
        assert config.context_file == Path("/tmp/test-agent/context.md")
        assert config.rounds_dir == Path("/tmp/test-agent/rounds")
        assert config.research_dir == Path("/tmp/test-agent/research")
        assert config.reviews_dir == Path("/tmp/test-agent/reviews")
        assert config.feedback_dir == Path("/tmp/test-agent/feedback")


class TestExtractHelpers:
    md = """# 标题

## 总目标

改进代码质量。

## 成功标准

- 标准一
- 标准二
- 标准三

## 其他

一些文字描述。
"""

    def test_extract_section_bullets(self):
        bullets = _extract_bullets(self.md, "成功标准")
        assert bullets == ["标准一", "标准二", "标准三"]

    def test_extract_section_single_line(self):
        result = _extract_section(self.md, "总目标", single_line=True)
        assert result == "改进代码质量。"

    def test_extract_missing_section(self):
        assert _extract_section(self.md, "不存在") == ""

    def test_extract_bullets_missing(self):
        assert _extract_bullets(self.md, "不存在") == []


class TestEnums:
    def test_role_values(self):
        assert Role.CEO.value == "ceo"
        assert Role.RESEARCH.value == "research"
        assert Role.DEV.value == "dev"
        assert Role.REVIEWER.value == "reviewer"
        assert Role.FEEDBACK.value == "feedback"

    def test_priority_order(self):
        assert Priority.P1.value == "P1"
        assert Priority.P2.value == "P2"
        assert Priority.P3.value == "P3"

    def test_status_values(self):
        assert Status.TODO.value == "todo"
        assert Status.DONE.value == "done"
        assert Status.QUEUED.value == "queued"
        assert Status.PARKED.value == "parked"
