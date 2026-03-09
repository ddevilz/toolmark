"""
Tests for skillforge.models — schema validation, edge cases, field validators.
"""

import pytest
from pydantic import ValidationError

from skillforge.models import (
    CompatReport,
    CompatStatus,
    Platform,
    PlatformCompatResult,
    ScanFinding,
    ScanReport,
    Severity,
    SkillManifest,
    SkillTestCase,
    SkillTool,
    ToleranceLevel,
)


class TestSkillManifest:

    def test_valid_manifest(self):
        m = SkillManifest(
            name="my-skill",
            version="1.0.0",
            author="ddevilz",
            description="A test skill",
        )
        assert m.name == "my-skill"
        assert m.version == "1.0.0"

    def test_invalid_name_uppercase_fails(self):
        with pytest.raises(ValidationError):
            SkillManifest(name="MySkill", version="1.0.0", author="x", description="d")

    def test_invalid_name_spaces_fails(self):
        with pytest.raises(ValidationError):
            SkillManifest(name="my skill", version="1.0.0", author="x", description="d")

    def test_reserved_name_fails(self):
        with pytest.raises(ValidationError):
            SkillManifest(name="skillforge", version="1.0.0", author="x", description="d")

    def test_invalid_version_format_fails(self):
        with pytest.raises(ValidationError):
            SkillManifest(name="ok-name", version="v1.0", author="x", description="d")

    def test_platforms_list(self):
        m = SkillManifest(
            name="my-skill", version="1.0.0", author="x", description="d",
            platforms=[Platform.CLAWHUB, Platform.CURSOR],
        )
        assert Platform.CLAWHUB in m.platforms

    def test_tools_list(self):
        tool = SkillTool(
            name="search_prs",
            description="Search pull requests",
        )
        m = SkillManifest(name="my-skill", version="1.0.0", author="x", description="d", tools=[tool])
        assert m.tools[0].name == "search_prs"


class TestSkillTool:

    def test_tool_name_snake_case_ok(self):
        t = SkillTool(name="my_tool", description="A tool")
        assert t.name == "my_tool"

    def test_tool_name_camel_case_fails(self):
        with pytest.raises(ValidationError):
            SkillTool(name="MyTool", description="A tool")

    def test_tool_name_with_dash_fails(self):
        with pytest.raises(ValidationError):
            SkillTool(name="my-tool", description="A tool")

    def test_tool_description_max_length(self):
        with pytest.raises(ValidationError):
            SkillTool(name="my_tool", description="x" * 1025)


class TestScanReport:

    def test_scan_report_counts_severities(self):
        manifest = SkillManifest(name="s", version="0.0.1", author="x", description="d")
        findings = [
            ScanFinding(rule_id="R1", severity=Severity.CRITICAL, message="crit"),
            ScanFinding(rule_id="R2", severity=Severity.HIGH, message="high"),
            ScanFinding(rule_id="R3", severity=Severity.HIGH, message="high2"),
            ScanFinding(rule_id="R4", severity=Severity.LOW, message="low"),
        ]
        report = ScanReport(manifest=manifest, findings=findings)
        assert report.critical_count == 1
        assert report.high_count == 2
        assert report.low_count == 1
        assert report.passed is False  # has CRITICAL

    def test_scan_report_passed_when_no_critical(self):
        manifest = SkillManifest(name="s", version="0.0.1", author="x", description="d")
        findings = [
            ScanFinding(rule_id="R1", severity=Severity.LOW, message="low only"),
        ]
        report = ScanReport(manifest=manifest, findings=findings)
        assert report.passed is True


class TestCompatReport:

    def test_overall_fail_when_any_platform_fails(self):
        manifest = SkillManifest(name="s", version="0.0.1", author="x", description="d")
        platforms = [
            PlatformCompatResult(platform=Platform.CLAWHUB, status=CompatStatus.PASS),
            PlatformCompatResult(platform=Platform.CURSOR,  status=CompatStatus.FAIL, issues=["Too big"]),
        ]
        report = CompatReport(manifest=manifest, platforms=platforms)
        assert report.overall_status == CompatStatus.FAIL

    def test_overall_warn_when_any_platform_warns(self):
        manifest = SkillManifest(name="s", version="0.0.1", author="x", description="d")
        platforms = [
            PlatformCompatResult(platform=Platform.CLAWHUB, status=CompatStatus.PASS),
            PlatformCompatResult(platform=Platform.CURSOR,  status=CompatStatus.WARN, warnings=["note"]),
        ]
        report = CompatReport(manifest=manifest, platforms=platforms)
        assert report.overall_status == CompatStatus.WARN

    def test_overall_pass_when_all_pass(self):
        manifest = SkillManifest(name="s", version="0.0.1", author="x", description="d")
        platforms = [
            PlatformCompatResult(platform=Platform.CLAWHUB,     status=CompatStatus.PASS),
            PlatformCompatResult(platform=Platform.CLAUDE_CODE, status=CompatStatus.PASS),
        ]
        report = CompatReport(manifest=manifest, platforms=platforms)
        assert report.overall_status == CompatStatus.PASS


class TestSkillTestCase:

    def test_default_tolerance_is_fuzzy(self):
        tc = SkillTestCase(input="search my PRs", expect_invoked=True)
        assert tc.tolerance == ToleranceLevel.FUZZY

    def test_strict_tolerance(self):
        tc = SkillTestCase(input="get issue 42", expect_invoked=True, tolerance=ToleranceLevel.STRICT)
        assert tc.tolerance == ToleranceLevel.STRICT
