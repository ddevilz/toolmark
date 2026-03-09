"""
skillforge test — LLM-as-judge evaluation framework.

Usage:
    skillforge test
    skillforge test --model anthropic/claude-haiku-4-5
    skillforge test --junit report.xml
    skillforge test --tags smoke
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import typer
import yaml
from rich import box
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from skillforge.models import (
    SkillManifest,
    SkillTestCase,
    TestCaseResult,
)
from skillforge.utils.llm import llm_call, llm_judge
from skillforge.utils.manifest import load_manifest

console = Console()

# Default options for typer to avoid B008 errors
DEFAULT_SKILL_DIR = Path(".")
DEFAULT_MODEL = ""
DEFAULT_TAGS = ""
DEFAULT_JUNIT_OUTPUT = ""
DEFAULT_VERBOSE = False


def _load_test_cases(tests_dir: Path, tags: list[str]) -> list[SkillTestCase]:
    """Load all test cases from tests/*.yaml."""
    cases: list[SkillTestCase] = []
    if not tests_dir.exists():
        return cases

    for f in sorted(tests_dir.glob("*.yaml")):
        raw = yaml.safe_load(f.read_text()) or []
        if isinstance(raw, list):
            for item in raw:
                tc = SkillTestCase(**item)
                if not tags or any(t in tc.tags for t in tags):
                    cases.append(tc)
        elif isinstance(raw, dict):
            # single test case file
            tc = SkillTestCase(**raw)
            if not tags or any(t in tc.tags for t in tags):
                cases.append(tc)

    return cases


def _build_system_prompt(manifest: SkillManifest) -> str:
    tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in manifest.tools)
    return (
        f"You are an AI agent with access to the skill '{manifest.name}'.\n"
        f"Description: {manifest.description}\n\n"
        f"Available tools:\n{tools_desc}\n\n"
        f"When the user sends a message, decide:\n"
        f"1. Should this skill be invoked? (yes/no)\n"
        f"2. If yes, which tool? And with what parameters?\n\n"
        f"Respond ONLY with JSON:\n"
        f'{{ "invoked": true/false, "tool": "<tool_name>", "params": {{...}} }}'
    )


async def _run_single_case(
    case: SkillTestCase,
    manifest: SkillManifest,
    model: str,
) -> TestCaseResult:
    """Run one test case and return result."""
    system = _build_system_prompt(manifest)
    t0 = time.perf_counter()

    # Step 1: Router call — would the skill be invoked?
    router_response, usage = await llm_call(
        model=model,
        system=system,
        user=case.input,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    # Parse router response
    try:
        router_json: dict[str, Any] = json.loads(router_response)
    except json.JSONDecodeError:
        router_json = {"invoked": False, "tool": None, "params": {}}

    actual_invoked = router_json.get("invoked", False)
    actual_tool = router_json.get("tool")
    actual_params = router_json.get("params", {})

    # Step 2: Judge call — was that correct?
    judge_passed, confidence, reasoning = await llm_judge(
        model=model,
        test_case=case,
        actual_invoked=actual_invoked,
        actual_tool=actual_tool,
        actual_params=actual_params,
    )

    return TestCaseResult(
        test_case=case,
        passed=judge_passed,
        confidence=confidence,
        actual_tool=actual_tool,
        actual_params=actual_params,
        judge_reasoning=reasoning,
        latency_ms=latency_ms,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
    )


def test_command(
    skill_dir: Path = typer.Option(DEFAULT_SKILL_DIR, "--dir", "-d", help="Path to skill project"),
    model: str = typer.Option(
        DEFAULT_MODEL, "--model", "-m", help="LiteLLM model string (default from config)"
    ),
    tags: str = typer.Option(
        DEFAULT_TAGS, "--tags", help="Comma-separated tags to filter test cases"
    ),
    junit_output: str = typer.Option(
        DEFAULT_JUNIT_OUTPUT, "--junit", help="Write JUnit XML to this file"
    ),
    verbose: bool = typer.Option(
        DEFAULT_VERBOSE, "--verbose", "-v", help="Show judge reasoning per test"
    ),
) -> None:
    """Run LLM-as-judge evaluation against your skill's test cases."""
    import asyncio

    from skillforge.config import load_config

    # Convert string path to Path object
    skill_dir = Path(skill_dir)

    cfg = load_config()
    _model = model or cfg.llm_model

    # Load manifest and test cases
    manifest = load_manifest(skill_dir)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    cases = _load_test_cases(skill_dir / "tests", tag_list)

    if not cases:
        console.print(
            "[yellow]⚠[/] No test cases found in [bold]tests/[/]. Add YAML files to get started."
        )
        raise typer.Exit(0)

    console.print(
        f"\n[bold red]◈[/] Running [bold]{len(cases)}[/] test cases with [cyan]{_model}[/]\n"
    )

    async def run_all():
        results = []
        with Progress(
            SpinnerColumn(style="red"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30, style="red"),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Evaluating...", total=len(cases))
            for case in cases:
                result = await _run_single_case(case, manifest, _model)
                results.append(result)
                progress.advance(task)
        return results

    results: list[TestCaseResult] = asyncio.run(run_all())

    # ── Results table ─────────────────────────────────────────────────────────
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = passed / total if total else 0.0

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold dim")
    tbl.add_column("Status", width=6)
    tbl.add_column("Input", width=42)
    tbl.add_column("Expected", width=22)
    tbl.add_column("Actual", width=22)
    tbl.add_column("Conf.", width=6)
    tbl.add_column("Lat.", width=7)

    for r in results:
        status_icon = "[green]PASS[/]" if r.passed else "[red]FAIL[/]"
        tbl.add_row(
            status_icon,
            r.test_case.input[:42],
            r.test_case.expect_tool or ("invoked" if r.test_case.expect_invoked else "skip"),
            r.actual_tool or ("invoked" if r.actual_invoked else "skip"),  # type: ignore[attr-defined]
            f"{r.confidence:.2f}",
            f"{r.latency_ms:.0f}ms",
        )
        if verbose and r.judge_reasoning:
            tbl.add_row("", f"  [dim]{r.judge_reasoning[:80]}[/]", "", "", "", "")

    console.print(tbl)

    quality_score = round(pass_rate * 100, 1)
    color = "green" if pass_rate >= 0.8 else "yellow" if pass_rate >= 0.5 else "red"
    console.print(
        f"\n[{color}]{'✓' if pass_rate >= 0.8 else '✗'}[/] "
        f"[bold]{passed}/{total}[/] tests passed — "
        f"Quality Score: [{color}]{quality_score}/100[/]\n"
    )

    # ── JUnit export ──────────────────────────────────────────────────────────
    if junit_output:
        _write_junit(results, junit_output)
        console.print(f"[dim]JUnit XML written → {junit_output}[/]")

    if passed < total:
        raise typer.Exit(1)


def _write_junit(results: list[TestCaseResult], output: str) -> None:
    """Write JUnit-compatible XML for CI/CD integration."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(
        f'<testsuite name="skillforge" tests="{len(results)}" failures="{sum(1 for r in results if not r.passed)}">'
    )
    for r in results:
        safe_input = r.test_case.input.replace("&", "&amp;").replace("<", "&lt;")
        lines.append(f'  <testcase name="{safe_input}" time="{r.latency_ms / 1000:.3f}">')
        if not r.passed:
            lines.append(
                f'    <failure message="Judge confidence={r.confidence:.2f}">{r.judge_reasoning}</failure>'
            )
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    Path(output).write_text("\n".join(lines))
