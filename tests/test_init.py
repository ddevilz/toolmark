"""
Tests for skillforge.commands.init
"""

import json

import pytest
from typer.testing import CliRunner

from skillforge.cli import app

runner = CliRunner()


@pytest.fixture
def tmp_skill_dir(tmp_path):
    """Provides a temp directory as the output parent."""
    return tmp_path


class TestInitCommand:
    def test_init_creates_skill_json(self, tmp_skill_dir):
        """init should create a valid skill.json with correct fields."""
        result = runner.invoke(app, ["init", "my-skill", "--dir", str(tmp_skill_dir)])
        assert result.exit_code == 0, result.output
        skill_json = tmp_skill_dir / "my-skill" / "skill.json"
        assert skill_json.exists(), "skill.json was not created"
        data = json.loads(skill_json.read_text())
        assert data["name"] == "my-skill"
        assert data["version"] == "0.1.0"

    def test_init_creates_skill_md(self, tmp_skill_dir):
        """init should create a SKILL.md from the template."""
        runner.invoke(app, ["init", "my-skill", "--template", "blank", "--dir", str(tmp_skill_dir)])
        skill_md = tmp_skill_dir / "my-skill" / "SKILL.md"
        assert skill_md.exists(), "SKILL.md was not created"
        content = skill_md.read_text()
        assert len(content) > 20, "SKILL.md appears empty"

    def test_init_creates_skillforge_yml(self, tmp_skill_dir):
        """init should create a .skillforge.yml project config."""
        runner.invoke(app, ["init", "my-skill", "--dir", str(tmp_skill_dir)])
        cfg = tmp_skill_dir / "my-skill" / ".skillforge.yml"
        assert cfg.exists()
        content = cfg.read_text()
        assert "my-skill" in content

    def test_init_creates_github_actions(self, tmp_skill_dir):
        """init should copy the GitHub Actions workflow."""
        runner.invoke(app, ["init", "my-skill", "--dir", str(tmp_skill_dir)])
        workflow = tmp_skill_dir / "my-skill" / ".github" / "workflows" / "skillforge.yml"
        assert workflow.exists(), ".github/workflows/skillforge.yml not created"

    def test_init_with_invalid_name_raises(self, tmp_skill_dir):
        """init should reject names that aren't kebab-case."""
        result = runner.invoke(app, ["init", "MySkill", "--dir", str(tmp_skill_dir)])
        assert result.exit_code != 0

    def test_init_with_invalid_template_raises(self, tmp_skill_dir):
        """init should reject unknown template names."""
        result = runner.invoke(
            app, ["init", "my-skill", "--template", "nonexistent", "--dir", str(tmp_skill_dir)]
        )
        assert result.exit_code != 0

    def test_init_template_github_api(self, tmp_skill_dir):
        """github-api template should include search_pull_requests tool."""
        runner.invoke(
            app, ["init", "my-gh-skill", "--template", "github-api", "--dir", str(tmp_skill_dir)]
        )
        skill_md = tmp_skill_dir / "my-gh-skill" / "SKILL.md"
        assert "search_pull_requests" in skill_md.read_text()

    def test_init_sets_platforms_in_manifest(self, tmp_skill_dir):
        """Platforms flag should be reflected in skill.json."""
        runner.invoke(
            app,
            [
                "init",
                "my-skill",
                "--platforms",
                "clawhub,cursor",
                "--dir",
                str(tmp_skill_dir),
            ],
        )
        data = json.loads((tmp_skill_dir / "my-skill" / "skill.json").read_text())
        assert "clawhub" in data.get("platforms", [])
        assert "cursor" in data.get("platforms", [])

    def test_init_duplicate_name_fails(self, tmp_skill_dir):
        """init should fail if the directory already exists."""
        runner.invoke(app, ["init", "my-skill", "--dir", str(tmp_skill_dir)])
        result = runner.invoke(app, ["init", "my-skill", "--dir", str(tmp_skill_dir)])
        assert result.exit_code != 0
