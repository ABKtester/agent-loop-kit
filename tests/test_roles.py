"""测试角色模块（不依赖 LLM）。"""

import pytest
from openhands.tools.preset.default import get_default_tools

from agent_loop_kit.models import Mission, Role
from agent_loop_kit.roles import (
    ROLE_SKILL_BUILDERS,
    create_role_agent,
    create_llm,
)


class TestRoleSkillBuilders:
    def test_all_roles_have_builders(self):
        for role in Role:
            assert role in ROLE_SKILL_BUILDERS, f"{role} 缺少 skill builder"

    def test_ceo_skills_mention_ceo(self):
        builder = ROLE_SKILL_BUILDERS[Role.CEO]
        skills = builder(Mission(goal="测试项目"))
        assert len(skills) > 0
        content = skills[0].content
        assert "CEO" in content
        assert "测试项目" in content

    def test_research_skills_mention_research(self):
        builder = ROLE_SKILL_BUILDERS[Role.RESEARCH]
        skills = builder(Mission())
        assert len(skills) > 0
        assert "Research" in skills[0].content

    def test_dev_skills(self):
        builder = ROLE_SKILL_BUILDERS[Role.DEV]
        skills = builder(Mission())
        assert "Dev" in skills[0].content

    def test_reviewer_skills(self):
        builder = ROLE_SKILL_BUILDERS[Role.REVIEWER]
        skills = builder(Mission())
        assert "Reviewer" in skills[0].content

    def test_feedback_skills(self):
        builder = ROLE_SKILL_BUILDERS[Role.FEEDBACK]
        skills = builder(Mission())
        assert "Feedback" in skills[0].content


class TestCreateRoleAgent:
    def test_ceo_skills_have_content(self):
        """验证 CEO 的 skill content 不为空（不实际创建 Agent）。"""
        builder = ROLE_SKILL_BUILDERS[Role.CEO]
        skills = builder(Mission(goal="测试目标"))
        assert len(skills) > 0
        assert len(skills[0].content) > 100

    def test_all_role_skills_have_content(self):
        """验证所有角色的 skill content 都不为空。"""
        for role in Role:
            builder = ROLE_SKILL_BUILDERS.get(role)
            assert builder is not None
            skills = builder(Mission())
            assert len(skills) > 0
            assert len(skills[0].content) > 50
