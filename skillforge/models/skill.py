"""
Pydantic models for SkillForge schemas.

Defines:
  - SkillTool          : a single tool declared in a skill
  - SkillSignature     : Ed25519 provenance signature metadata
  - SkillManifest      : full skill.json schema (machine-readable)
  - SkillTestCase      : a single LLM-as-judge test case
  - TestSuiteConfig    : tests/*.yaml schema
  - ScanFinding        : a single scanner finding
  - ScanReport         : full scan output
  - CompatReport       : cross-platform compatibility report
  - BenchResult        : benchmark scorecard
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ── Enums ─────────────────────────────────────────────────────────────────────


class Platform(StrEnum):
    CLAWHUB = "clawhub"
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    WINDSURF = "windsurf"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CompatStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class ToleranceLevel(StrEnum):
    STRICT = "strict"  # exact parameter match
    FUZZY = "fuzzy"  # semantic match
    INVOKED = "invoked"  # only check if skill was invoked at all


# ── Skill Schema ──────────────────────────────────────────────────────────────


class SkillToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class SkillTool(BaseModel):
    name: str = Field(..., description="Tool function name, snake_case")
    description: str = Field(..., max_length=1024)
    parameters: list[SkillToolParameter] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_snake_case(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"Tool name must be snake_case, got: {v!r}")
        return v


class SkillSignature(BaseModel):
    public_key_fingerprint: str
    content_hash: str  # sha256: of SKILL.md + skill.json
    signed_at: str  # ISO 8601
    signer: str | None = None  # author identifier


class SkillManifest(BaseModel):
    """Represents a complete skill.json manifest."""

    name: str = Field(..., pattern=r"^[a-z][a-z0-9\-]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    author: str
    license: str = "MIT"
    description: str = Field(..., max_length=280)
    platforms: list[Platform] = Field(default_factory=list)
    declared_permissions: list[str] = Field(
        default_factory=list, description="e.g. ['network:api.github.com', 'env:GITHUB_TOKEN']"
    )
    tools: list[SkillTool] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    homepage: str | None = None
    repository: str | None = None
    signature: SkillSignature | None = None

    @field_validator("name")
    @classmethod
    def name_no_reserved(cls, v: str) -> str:
        reserved = {"skillforge", "clawhub", "anthropic", "openai"}
        if v in reserved:
            raise ValueError(f"Name {v!r} is reserved")
        return v


# ── Test Schema ───────────────────────────────────────────────────────────────


class SkillTestCase(BaseModel):
    """One LLM-as-judge test case from tests/*.yaml."""

    id: str | None = None
    input: str = Field(..., description="Natural language user message")
    expect_invoked: bool = True
    expect_tool: str | None = None
    expect_params: dict[str, Any] = Field(default_factory=dict)
    tolerance: ToleranceLevel = ToleranceLevel.FUZZY
    tags: list[str] = Field(default_factory=list)


class TestCaseResult(BaseModel):
    test_case: SkillTestCase
    passed: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    actual_tool: str | None = None
    actual_params: dict[str, Any] = Field(default_factory=dict)
    judge_reasoning: str = ""
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class TestSuiteResult(BaseModel):
    manifest: SkillManifest
    results: list[TestCaseResult]
    quality_score: float = 0.0  # 0–100
    pass_rate: float = 0.0
    total_latency_ms: float = 0.0
    total_tokens: int = 0


# ── Scan Schema ───────────────────────────────────────────────────────────────


class ScanFinding(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    location: str | None = None  # file:line or field name
    evidence: str | None = None  # snippet that triggered the rule
    remediation: str | None = None


class ScanReport(BaseModel):
    manifest: SkillManifest
    findings: list[ScanFinding] = Field(default_factory=list)
    passed: bool = True
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    scanner_version: str = "0.1.0"

    def model_post_init(self, __context: Any) -> None:
        self.critical_count = sum(1 for f in self.findings if f.severity == Severity.CRITICAL)
        self.high_count = sum(1 for f in self.findings if f.severity == Severity.HIGH)
        self.medium_count = sum(1 for f in self.findings if f.severity == Severity.MEDIUM)
        self.low_count = sum(1 for f in self.findings if f.severity == Severity.LOW)
        self.passed = self.critical_count == 0


# ── Compat Schema ─────────────────────────────────────────────────────────────


class PlatformCompatResult(BaseModel):
    platform: Platform
    status: CompatStatus
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    auto_fixes: list[str] = Field(default_factory=list)


class CompatReport(BaseModel):
    manifest: SkillManifest
    platforms: list[PlatformCompatResult] = Field(default_factory=list)
    overall_status: CompatStatus = CompatStatus.PASS

    def model_post_init(self, __context: Any) -> None:
        if any(p.status == CompatStatus.FAIL for p in self.platforms):
            self.overall_status = CompatStatus.FAIL
        elif any(p.status == CompatStatus.WARN for p in self.platforms):
            self.overall_status = CompatStatus.WARN


# ── Bench Schema ──────────────────────────────────────────────────────────────


class BenchResult(BaseModel):
    manifest: SkillManifest
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    avg_prompt_tokens: float = 0.0
    avg_completion_tokens: float = 0.0
    test_pass_rate: float = 0.0  # from test suite
    security_score: float = 100.0  # penalised per finding severity
    compat_score: float = 0.0  # platforms passed / total
    quality_score: float = 0.0  # weighted composite 0–100
    runs: int = 50
