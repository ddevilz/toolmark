"""
skillforge scan — Security scanner for agent skills.

Runs:
  1. Built-in rule engine  (prompt injection, dynamic fetch, permission audit)
  2. Snyk agent-scan       (subprocess, 138 rules across 15 categories)

Usage:
    skillforge scan
    skillforge scan --no-snyk
    skillforge scan --output report.json
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from skillforge.models import ScanFinding, ScanReport, Severity
from skillforge.utils.manifest import load_manifest

console = Console()

# Default options for typer to avoid B008 errors
DEFAULT_SKILL_DIR = Path(".")
DEFAULT_NO_SNYK = False
DEFAULT_OUTPUT = ""
DEFAULT_STRICT = False

# ── Built-in rules ────────────────────────────────────────────────────────────

_DYNAMIC_FETCH_PATTERNS = [
    r"curl\s+https?://",
    r"wget\s+https?://",
    r"\beval\s*\(",
    r"__import__\s*\(",
    r"subprocess\.call\s*\(\[.*(curl|wget)",
    r"requests\.get\(",  # undeclared outbound
    r"httpx\.get\(",
]

_CRED_PATTERNS = [
    r"(?i)(password|passwd|secret|token|api[_\-]?key)\s*=\s*['\"][^'\"]{8,}",
    r"sk-[a-zA-Z0-9]{32,}",  # OpenAI key pattern
    r"ant-[a-zA-Z0-9\-]{30,}",  # Anthropic key pattern
]

_INJECTION_TRIGGER_PHRASES = [
    "ignore previous instructions",
    "disregard your system prompt",
    "you are now",
    "new persona",
    "jailbreak",
    "do anything now",
]


def _scan_dynamic_fetch(content: str, file_label: str) -> Iterator[ScanFinding]:
    for pat in _DYNAMIC_FETCH_PATTERNS:
        for m in re.finditer(pat, content):
            yield ScanFinding(
                rule_id="SF001",
                severity=Severity.HIGH,
                message="Dynamic content fetch detected — skill may load remote instructions at runtime.",
                location=f"{file_label}",
                evidence=m.group(0)[:80],
                remediation="Declare all external endpoints in declared_permissions[]. Avoid curl|source patterns.",
            )


def _scan_hardcoded_creds(content: str, file_label: str) -> Iterator[ScanFinding]:
    for pat in _CRED_PATTERNS:
        for m in re.finditer(pat, content):
            yield ScanFinding(
                rule_id="SF002",
                severity=Severity.CRITICAL,
                message="Hardcoded credential or API key detected.",
                location=file_label,
                evidence=m.group(0)[:60] + "...",
                remediation="Use environment variables declared in declared_permissions[env:VAR_NAME].",
            )


def _scan_prompt_injection(content: str, file_label: str) -> Iterator[ScanFinding]:
    content_lower = content.lower()
    for phrase in _INJECTION_TRIGGER_PHRASES:
        if phrase in content_lower:
            idx = content_lower.index(phrase)
            yield ScanFinding(
                rule_id="SF003",
                severity=Severity.HIGH,
                message=f"Potential prompt injection phrase detected in tool description: '{phrase}'",
                location=file_label,
                evidence=content[max(0, idx - 20) : idx + len(phrase) + 20],
                remediation="Remove adversarial phrases from tool descriptions and SKILL.md.",
            )


def _scan_undeclared_permissions(manifest_data: dict, content: str) -> Iterator[ScanFinding]:
    """Check if network calls or env reads appear in SKILL.md but aren't declared."""
    declared = set(manifest_data.get("declared_permissions", []))
    declared_networks = {p.replace("network:", "") for p in declared if p.startswith("network:")}
    domain_pattern = re.compile(r"https?://([a-zA-Z0-9\-\.]+)/")
    for m in domain_pattern.finditer(content):
        domain = m.group(1)
        if domain not in declared_networks and not domain.startswith("localhost"):
            yield ScanFinding(
                rule_id="SF004",
                severity=Severity.MEDIUM,
                message=f"Undeclared network endpoint referenced: {domain}",
                location="SKILL.md",
                evidence=m.group(0),
                remediation=f"Add 'network:{domain}' to declared_permissions in skill.json.",
            )


def _run_snyk(skill_dir: Path, snyk_binary: str) -> list[ScanFinding]:
    """Run snyk agent-scan as subprocess and parse output."""
    try:
        result = subprocess.run(
            [snyk_binary, "agent-scan", str(skill_dir), "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        console.print(
            f"[yellow]⚠[/] Snyk binary [bold]{snyk_binary}[/] not found — skipping Snyk scan."
        )
        return []
    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠[/] Snyk scan timed out after 120s.")
        return []

    if not result.stdout.strip():
        return []

    try:
        snyk_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    findings: list[ScanFinding] = []
    for issue in snyk_data.get("issues", []):
        sev_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        findings.append(
            ScanFinding(
                rule_id=f"SNYK-{issue.get('id', 'UNKNOWN')}",
                severity=sev_map.get(issue.get("severity", "low"), Severity.LOW),
                message=issue.get("title", "Snyk finding"),
                location=issue.get("filePath"),
                remediation=issue.get("remediation"),
            )
        )
    return findings


def scan_command(
    skill_dir: Path = typer.Option(DEFAULT_SKILL_DIR, "--dir", "-d", help="Path to skill project"),
    no_snyk: bool = typer.Option(DEFAULT_NO_SNYK, "--no-snyk", help="Skip Snyk agent-scan"),
    output: str = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Write JSON report to file"),
    strict: bool = typer.Option(DEFAULT_STRICT, "--strict", help="Also fail on MEDIUM findings"),
) -> None:
    """Run security scanner — prompt injection, dynamic fetch, creds, undeclared permissions."""
    from skillforge.config import load_config

    # Convert string path to Path object
    skill_dir = Path(skill_dir)
    cfg = load_config()

    manifest = load_manifest(skill_dir)
    findings: list[ScanFinding] = []

    # ── Read all skill content ─────────────────────────────────────────────────
    skill_md = skill_dir / "SKILL.md"
    skill_json = skill_dir / "skill.json"

    skill_md_content = skill_md.read_text() if skill_md.exists() else ""
    skill_json_content = skill_json.read_text() if skill_json.exists() else "{}"

    combined = skill_md_content + "\n" + skill_json_content

    # ── Built-in rules ─────────────────────────────────────────────────────────
    console.print("\n[bold red]◈[/] Running built-in rules...", end=" ")
    findings.extend(_scan_dynamic_fetch(combined, "SKILL.md+skill.json"))
    findings.extend(_scan_hardcoded_creds(combined, "SKILL.md+skill.json"))
    findings.extend(_scan_prompt_injection(skill_md_content, "SKILL.md"))
    findings.extend(_scan_undeclared_permissions(json.loads(skill_json_content), skill_md_content))
    console.print("[green]done[/]")

    # ── Snyk ───────────────────────────────────────────────────────────────────
    if not no_snyk:
        console.print("[bold red]◈[/] Running Snyk agent-scan...", end=" ")
        findings.extend(_run_snyk(skill_dir, cfg.snyk_binary))
        console.print("[green]done[/]")

    # ── Build report ───────────────────────────────────────────────────────────
    report = ScanReport(manifest=manifest, findings=findings)

    # ── Display ────────────────────────────────────────────────────────────────
    sev_colors = {
        Severity.CRITICAL: "bold red",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "dim",
    }

    if findings:
        tbl = Table(box=box.SIMPLE_HEAVY, header_style="bold dim", show_lines=False)
        tbl.add_column("Sev", width=8)
        tbl.add_column("Rule", width=12)
        tbl.add_column("Message", width=50)
        tbl.add_column("Remediation", width=34)

        for f in sorted(
            findings, key=lambda x: ["critical", "high", "medium", "low"].index(x.severity.value)
        ):
            tbl.add_row(
                f"[{sev_colors[f.severity]}]{f.severity.value.upper()}[/]",
                f.rule_id,
                f.message[:50],
                (f.remediation or "")[:34],
            )
        console.print(tbl)
    else:
        console.print("\n[green]✓ No findings — skill looks clean.[/]\n")

    console.print(
        f"[bold]Summary:[/] "
        f"[red]{report.critical_count} CRITICAL[/]  "
        f"[red]{report.high_count} HIGH[/]  "
        f"[yellow]{report.medium_count} MEDIUM[/]  "
        f"[dim]{report.low_count} LOW[/]\n"
    )

    # ── JSON output ────────────────────────────────────────────────────────────
    if output:
        Path(output).write_text(json.dumps(report.model_dump(mode="json"), indent=2))
        console.print(f"[dim]Report written → {output}[/]")

    # ── Exit codes ─────────────────────────────────────────────────────────────
    should_fail = (
        report.critical_count > 0
        or (cfg.scan_block_on_high and report.high_count > 0)
        or (strict and report.medium_count > 0)
    )
    if should_fail:
        raise typer.Exit(1)
