"""Utilities for loading and validating skill manifests."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from skillforge.models import SkillManifest

console = Console()


def load_manifest(skill_dir: Path) -> SkillManifest:
    """Load and validate skill.json from a skill directory."""
    manifest_path = skill_dir / "skill.json"
    if not manifest_path.exists():
        console.print(
            f"[red]✗[/] [bold]skill.json[/] not found in [bold]{skill_dir}[/]. "
            "Run [cyan]skillforge init[/] first."
        )
        raise typer.Exit(1)

    try:
        raw = json.loads(manifest_path.read_text())
        return SkillManifest(**raw)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/] Invalid JSON in skill.json: {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/] skill.json validation failed: {e}")
        raise typer.Exit(1) from e
