"""
skillforge compat — Cross-platform compatibility checker.

Validates your skill against per-platform constraints and emits
a compat.json report with PASS / WARN / FAIL per platform.

Usage:
    skillforge compat
    skillforge compat --platforms clawhub,cursor
    skillforge compat --output compat.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from skillforge.models import (
    CompatReport,
    CompatStatus,
    Platform,
    PlatformCompatResult,
)
from skillforge.utils.manifest import load_manifest

console = Console()

# ── Platform Constraint Matrix ────────────────────────────────────────────────
# Community-maintained — update per platform release.

PLATFORM_CONSTRAINTS: dict[Platform, dict[str, Any]] = {
    Platform.CLAWHUB: {
        "max_tool_description_chars": 512,
        "max_skill_md_bytes": 16_384,
        "required_fields": ["name", "tools"],
        "blocks_dynamic_fetch": True,
        "permissions_model": "declarative",
        "sandboxing": "docker_optional",
    },
    Platform.CLAUDE_CODE: {
        "max_tool_description_chars": 1024,
        "max_skill_md_bytes": 32_768,
        "required_fields": ["name", "tools", "declared_permissions"],
        "blocks_dynamic_fetch": True,
        "permissions_model": "declarative+runtime",
        "sandboxing": "wasm_roadmap",
    },
    Platform.CURSOR: {
        "max_tool_description_chars": 768,
        "max_skill_md_bytes": 16_384,
        "required_fields": ["name", "tools"],
        "blocks_dynamic_fetch": False,
        "permissions_model": "declarative",
        "sandboxing": "node_sandbox",
    },
    Platform.WINDSURF: {
        "max_tool_description_chars": 512,
        "max_skill_md_bytes": 8_192,
        "required_fields": ["name"],
        "blocks_dynamic_fetch": False,
        "permissions_model": "none",
        "sandboxing": "none",
    },
}


def _check_platform(
    platform: Platform,
    manifest_data: dict[str, Any],
    skill_md_bytes: int,
) -> PlatformCompatResult:
    constraints = PLATFORM_CONSTRAINTS[platform]
    issues: list[str] = []
    warnings: list[str] = []
    auto_fixes: list[str] = []

    # 1. Required fields
    for field in constraints["required_fields"]:
        if field not in manifest_data:
            issues.append(f"Missing required field: '{field}'")
        # For list fields, allow empty list as valid
        elif field == "declared_permissions" and isinstance(manifest_data[field], list):
            pass  # Empty list is valid for permissions
        elif not manifest_data[field]:
            issues.append(f"Missing required field: '{field}'")

    # 2. SKILL.md size
    max_bytes = constraints["max_skill_md_bytes"]
    if skill_md_bytes > max_bytes:
        issues.append(
            f"SKILL.md is {skill_md_bytes:,} bytes; {platform.value} limit is {max_bytes:,} bytes."
        )
        auto_fixes.append("Split large SKILL.md into a concise summary + linked reference doc.")

    # 3. Tool description lengths
    for tool in manifest_data.get("tools", []):
        desc = tool.get("description", "")
        max_desc = constraints["max_tool_description_chars"]
        if len(desc) > max_desc:
            issues.append(
                f"Tool '{tool['name']}' description is {len(desc)} chars; "
                f"{platform.value} limit is {max_desc}."
            )
            auto_fixes.append(
                f"Truncate '{tool['name']}' description to {max_desc} chars for {platform.value}."
            )

    # 4. Permissions model
    if constraints["permissions_model"] == "none":
        declared = manifest_data.get("declared_permissions", [])
        if declared:
            warnings.append(
                f"{platform.value} has no permissions model — "
                f"declared_permissions[] will be ignored."
            )

    # 5. Dynamic fetch
    if not constraints["blocks_dynamic_fetch"]:
        warnings.append(
            f"{platform.value} allows dynamic fetch — extra care needed to avoid supply-chain risk."
        )

    status = CompatStatus.FAIL if issues else CompatStatus.WARN if warnings else CompatStatus.PASS
    return PlatformCompatResult(
        platform=platform,
        status=status,
        issues=issues,
        warnings=warnings,
        auto_fixes=auto_fixes,
    )


def compat_command(
    skill_dir: Path = typer.Option(".", "--dir", "-d", help="Path to skill project"),
    platforms: str = typer.Option(
        "", "--platforms", "-p", help="Comma-separated platforms to check (default: all)"
    ),
    output: str = typer.Option("", "--output", "-o", help="Write compat.json to file"),
) -> None:
    """Check cross-platform compatibility of your skill."""
    # Convert string path to Path object
    skill_dir = Path(skill_dir)
    manifest = load_manifest(skill_dir)

    # Determine which platforms to check
    if platforms:
        target = [Platform(p.strip()) for p in platforms.split(",")]
    else:
        target = manifest.platforms or list(Platform)

    # Read raw manifest dict for constraint checks
    skill_json = skill_dir / "skill.json"
    manifest_data = json.loads(skill_json.read_text()) if skill_json.exists() else {}

    skill_md = skill_dir / "SKILL.md"
    skill_md_bytes = len(skill_md.read_bytes()) if skill_md.exists() else 0

    console.print(
        f"\n[bold red]◈[/] Checking compatibility for [bold]{len(target)}[/] platform(s)...\n"
    )

    results: list[PlatformCompatResult] = [
        _check_platform(p, manifest_data, skill_md_bytes) for p in target
    ]

    report = CompatReport(manifest=manifest, platforms=results)

    # ── Display ────────────────────────────────────────────────────────────────
    status_colors = {
        CompatStatus.PASS: "green",
        CompatStatus.WARN: "yellow",
        CompatStatus.FAIL: "red",
    }
    status_icons = {CompatStatus.PASS: "✓", CompatStatus.WARN: "⚠", CompatStatus.FAIL: "✗"}

    tbl = Table(box=box.SIMPLE_HEAVY, header_style="bold dim")
    tbl.add_column("Platform", width=14)
    tbl.add_column("Status", width=8)
    tbl.add_column("Issues", width=50)
    tbl.add_column("Auto-fix", width=42)

    for r in results:
        col = status_colors[r.status]
        tbl.add_row(
            r.platform.value,
            f"[{col}]{status_icons[r.status]} {r.status.value.upper()}[/]",
            "; ".join(r.issues[:2]) or "[dim]—[/]",
            "; ".join(r.auto_fixes[:1]) or "[dim]—[/]",
        )
        for w in r.warnings:
            tbl.add_row("", "[yellow]WARN[/]", f"[dim]{w[:50]}[/]", "")

    console.print(tbl)

    overall_col = status_colors[report.overall_status]
    console.print(
        f"\n[{overall_col}]{status_icons[report.overall_status]}[/] "
        f"Overall: [{overall_col}]{report.overall_status.value.upper()}[/] "
        f"({sum(1 for r in results if r.status == CompatStatus.PASS)}/{len(results)} platforms passed)\n"
    )

    if output:
        Path(output).write_text(json.dumps(report.model_dump(mode="json"), indent=2))
        console.print(f"[dim]compat.json written → {output}[/]")

    if report.overall_status == CompatStatus.FAIL:
        raise typer.Exit(1)
