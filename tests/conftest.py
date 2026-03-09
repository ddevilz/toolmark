"""Shared pytest fixtures for SkillForge tests."""

import json
from pathlib import Path

import pytest

from skillforge.models import Platform, SkillManifest, SkillTool


@pytest.fixture
def sample_manifest() -> SkillManifest:
    return SkillManifest(
        name="test-skill",
        version="0.1.0",
        author="test-author",
        description="A test skill for unit tests",
        platforms=[Platform.CLAWHUB, Platform.CLAUDE_CODE],
        declared_permissions=["network:api.github.com", "env:GITHUB_TOKEN"],
        tools=[
            SkillTool(name="search_prs", description="Search pull requests"),
            SkillTool(name="get_issue", description="Get a specific issue"),
        ],
    )


@pytest.fixture
def skill_project(tmp_path, sample_manifest) -> Path:
    """Creates a minimal skill project directory for command tests."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    # skill.json
    (skill_dir / "skill.json").write_text(
        json.dumps(sample_manifest.model_dump(mode="json", exclude_none=True), indent=2)
    )

    # SKILL.md
    (skill_dir / "SKILL.md").write_text(
        "# test-skill\n\nA skill for searching GitHub pull requests.\n\n"
        "## Tools\n\n### search_prs\nSearch pull requests.\n"
    )

    # tests/
    tests_dir = skill_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_basic.yaml").write_text(
        "- id: basic\n"
        "  input: find my open PRs\n"
        "  expect_invoked: true\n"
        "  expect_tool: search_prs\n"
        "  expect_params: {}\n"
        "  tolerance: fuzzy\n"
        "  tags: [smoke]\n"
    )

    return skill_dir
