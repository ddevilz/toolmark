"""
skillforge bench — Performance benchmarking for skills.

Runs the test suite N times with timing instrumentation and computes:
  - Latency p50 / p95 / p99
  - Token consumption averages
  - Composite Quality Score (0–100)

Usage:
    skillforge bench
    skillforge bench --runs 20
    skillforge bench --output scorecard.json
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from skillforge.models import BenchResult
from skillforge.utils.manifest import load_manifest

console = Console()


def _compute_security_score(scan_report_path: Path | None) -> float:
    """Derive a security score (0-100) from a scan report if available."""
    if not scan_report_path or not scan_report_path.exists():
        return 100.0  # assume clean if no report
    try:
        data = json.loads(scan_report_path.read_text())
    except Exception:
        return 100.0
    # Deductions per finding severity
    deductions = {
        "critical": 40,
        "high": 20,
        "medium": 8,
        "low": 2,
    }
    score = 100.0
    for finding in data.get("findings", []):
        score -= deductions.get(finding.get("severity", "low"), 0)
    return max(0.0, score)


def _compute_compat_score(compat_report_path: Path | None) -> float:
    """Derive compat score from compat.json if available."""
    if not compat_report_path or not compat_report_path.exists():
        return 0.0
    try:
        data = json.loads(compat_report_path.read_text())
    except Exception:
        return 0.0
    platforms = data.get("platforms", [])
    if not platforms:
        return 0.0
    passed = sum(1 for p in platforms if p.get("status") == "pass")
    return round(passed / len(platforms) * 100, 1)


def _percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def bench_command(
    skill_dir: Path = typer.Option(".", "--dir", "-d", help="Path to skill project"),
    runs: int = typer.Option(
        0, "--runs", "-r", help="Number of benchmark runs (default from config)"
    ),
    model: str = typer.Option("", "--model", "-m"),
    output: str = typer.Option("", "--output", "-o", help="Write scorecard JSON to file"),
    scan_report: str = typer.Option("", "--scan-report", help="Path to existing scan report JSON"),
    compat_report: str = typer.Option(
        "", "--compat-report", help="Path to existing compat report JSON"
    ),
) -> None:
    """Benchmark skill latency, token usage, and compute composite quality score."""
    # Convert string path to Path object
    skill_dir = Path(skill_dir)
    import asyncio

    from skillforge.commands.test import _load_test_cases, _run_single_case
    from skillforge.config import load_config

    cfg = load_config()
    _model = model or cfg.llm_model
    _runs = runs or cfg.bench_runs

    manifest = load_manifest(skill_dir)
    cases = _load_test_cases(skill_dir / "tests", [])

    if not cases:
        console.print("[yellow]⚠[/] No test cases found — nothing to benchmark.")
        raise typer.Exit(0)

    console.print(
        f"\n[bold red]◈[/] Benchmarking [bold]{manifest.name}[/] — "
        f"[cyan]{_runs} runs × {len(cases)} test cases[/]\n"
    )

    latencies: list[float] = []
    prompt_tokens_list: list[float] = []
    completion_tokens_list: list[float] = []
    pass_count = 0
    total_count = 0

    async def run_bench():
        nonlocal pass_count, total_count
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(style="red"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40, style="red"),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running...", total=_runs * len(cases))
            for _ in range(_runs):
                for case in cases:
                    result = await _run_single_case(case, manifest, _model)
                    latencies.append(result.latency_ms)
                    prompt_tokens_list.append(result.prompt_tokens)
                    completion_tokens_list.append(result.completion_tokens)
                    if result.passed:
                        pass_count += 1
                    total_count += 1
                    progress.advance(task)

    asyncio.run(run_bench())

    # ── Compute scores ─────────────────────────────────────────────────────────
    pass_rate = pass_count / total_count if total_count else 0.0
    sec_score = _compute_security_score(Path(scan_report) if scan_report else None)
    compat_score = _compute_compat_score(Path(compat_report) if compat_report else None)

    # Weighted composite: test 50%, security 30%, compat 20%
    quality_score = round((pass_rate * 100 * 0.50) + (sec_score * 0.30) + (compat_score * 0.20), 1)

    result = BenchResult(
        manifest=manifest,
        latency_p50_ms=_percentile(latencies, 50),
        latency_p95_ms=_percentile(latencies, 95),
        latency_p99_ms=_percentile(latencies, 99),
        avg_prompt_tokens=statistics.mean(prompt_tokens_list) if prompt_tokens_list else 0,
        avg_completion_tokens=statistics.mean(completion_tokens_list)
        if completion_tokens_list
        else 0,
        test_pass_rate=pass_rate,
        security_score=sec_score,
        compat_score=compat_score,
        quality_score=quality_score,
        runs=_runs,
    )

    # ── Display scorecard ──────────────────────────────────────────────────────
    color = "green" if quality_score >= 80 else "yellow" if quality_score >= 50 else "red"

    scorecard = (
        f"[bold]Skill:[/]              {manifest.name} v{manifest.version}\n"
        f"[bold]Runs:[/]               {_runs} × {len(cases)} test cases\n\n"
        f"[bold cyan]Latency[/]\n"
        f"  p50  {result.latency_p50_ms:.0f} ms\n"
        f"  p95  {result.latency_p95_ms:.0f} ms\n"
        f"  p99  {result.latency_p99_ms:.0f} ms\n\n"
        f"[bold cyan]Tokens (avg/call)[/]\n"
        f"  Prompt      {result.avg_prompt_tokens:.0f}\n"
        f"  Completion  {result.avg_completion_tokens:.0f}\n\n"
        f"[bold cyan]Scores[/]\n"
        f"  Test pass rate   {pass_rate * 100:.1f}%\n"
        f"  Security score   {sec_score:.1f}/100\n"
        f"  Compat score     {compat_score:.1f}/100\n\n"
        f"[bold {color}]Quality Score: {quality_score}/100[/]"
    )

    console.print(
        Panel(scorecard, title="[bold red]SkillForge Benchmark[/]", border_style="dim red")
    )

    if output:
        Path(output).write_text(json.dumps(result.model_dump(mode="json"), indent=2))
        console.print(f"\n[dim]Scorecard written → {output}[/]")
