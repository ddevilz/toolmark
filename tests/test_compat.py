"""
Tests for skillforge.commands.compat — platform compatibility checker.
No external API calls required.
"""

from skillforge.commands.compat import PLATFORM_CONSTRAINTS, _check_platform
from skillforge.models import CompatStatus, Platform


def _base_manifest():
    return {
        "name": "my-skill",
        "version": "0.1.0",
        "author": "test",
        "description": "A test skill",
        "tools": [{"name": "search_prs", "description": "Search pull requests", "parameters": []}],
        "declared_permissions": [],
        "platforms": ["clawhub"],
    }


class TestCompatChecker:
    def test_valid_manifest_passes_all_platforms(self):
        manifest = _base_manifest()
        for platform in Platform:
            result = _check_platform(platform, manifest, skill_md_bytes=100)
            # Even if some warnings, should not FAIL for a basic valid manifest
            assert result.status in (CompatStatus.PASS, CompatStatus.WARN), (
                f"{platform.value} failed: {result.issues}"
            )

    def test_skill_md_too_large_clawhub_fails(self):
        manifest = _base_manifest()
        limit = PLATFORM_CONSTRAINTS[Platform.CLAWHUB]["max_skill_md_bytes"]
        result = _check_platform(Platform.CLAWHUB, manifest, skill_md_bytes=limit + 1)
        assert result.status == CompatStatus.FAIL
        assert any("bytes" in issue for issue in result.issues)

    def test_skill_md_too_large_windsurf_fails(self):
        manifest = _base_manifest()
        limit = PLATFORM_CONSTRAINTS[Platform.WINDSURF]["max_skill_md_bytes"]
        result = _check_platform(Platform.WINDSURF, manifest, skill_md_bytes=limit + 1)
        assert result.status == CompatStatus.FAIL

    def test_tool_description_too_long_clawhub(self):
        manifest = _base_manifest()
        limit = PLATFORM_CONSTRAINTS[Platform.CLAWHUB]["max_tool_description_chars"]
        manifest["tools"][0]["description"] = "x" * (limit + 1)
        result = _check_platform(Platform.CLAWHUB, manifest, skill_md_bytes=100)
        assert result.status == CompatStatus.FAIL
        assert any("description" in i for i in result.issues)

    def test_auto_fix_suggested_for_oversized_skill_md(self):
        manifest = _base_manifest()
        limit = PLATFORM_CONSTRAINTS[Platform.CLAWHUB]["max_skill_md_bytes"]
        result = _check_platform(Platform.CLAWHUB, manifest, skill_md_bytes=limit + 1)
        assert len(result.auto_fixes) > 0

    def test_missing_required_field_claude_code(self):
        manifest = _base_manifest()
        del manifest["declared_permissions"]  # required on claude-code
        result = _check_platform(Platform.CLAUDE_CODE, manifest, skill_md_bytes=100)
        assert result.status == CompatStatus.FAIL
        assert any("declared_permissions" in i for i in result.issues)

    def test_windsurf_no_permissions_model_warning(self):
        manifest = _base_manifest()
        manifest["declared_permissions"] = ["network:api.github.com"]
        result = _check_platform(Platform.WINDSURF, manifest, skill_md_bytes=100)
        # Windsurf has no permissions model — should warn that permissions are ignored
        assert any("ignored" in w or "no permissions" in w.lower() for w in result.warnings)

    def test_platform_constraints_matrix_complete(self):
        """All 4 platforms must be present in the constraint matrix."""
        for platform in Platform:
            assert platform in PLATFORM_CONSTRAINTS, (
                f"{platform.value} missing from constraint matrix"
            )
