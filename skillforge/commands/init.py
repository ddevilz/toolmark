"""
skillforge init — Scaffold a new skill project.

Usage:
    skillforge init <skill-name>
    skillforge init my-github-skill --template github-api
    skillforge init my-skill --platforms clawhub,claude-code --author ddevilz
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from skillforge.models import Platform, SkillManifest
from skillforge.utils.fs import find_templates_dir

console = Console()

VALID_TEMPLATES = [
    "github-api",
    "file-ops",
    "mcp-integration",
    "web-search",
    "loom-query",
    "blank",
]

PLATFORM_CHOICES = [p.value for p in Platform]


def init_command(
    name: str = typer.Argument(..., help="Skill name (kebab-case, e.g. my-github-skill)"),
    template: str = typer.Option(
        "blank",
        "--template",
        "-t",
        help=f"Starter template: {', '.join(VALID_TEMPLATES)}",
    ),
    author: str = typer.Option("", "--author", "-a", help="Author handle"),
    platforms: str = typer.Option(
        "clawhub",
        "--platforms",
        "-p",
        help="Comma-separated platforms: clawhub,claude-code,cursor,windsurf",
    ),
    output_dir: Path = typer.Option(
        ".",
        "--dir",
        "-d",
        help="Parent directory for the new skill folder",
    ),
) -> None:
    """Scaffold a new SkillForge project with a SKILL.md, skill.json, and test suite."""

    # Convert string path to Path object
    output_dir = Path(output_dir)

    # ── Validate inputs ───────────────────────────────────────────────────────
    import re

    if not re.match(r"^[a-z][a-z0-9\-]*$", name):
        console.print(
            f"[red]✗[/] Skill name must be kebab-case (e.g. my-skill). Got: [bold]{name}[/]"
        )
        raise typer.Exit(1)

    if template not in VALID_TEMPLATES:
        console.print(
            f"[red]✗[/] Unknown template [bold]{template}[/]. Choose from: {', '.join(VALID_TEMPLATES)}"
        )
        raise typer.Exit(1)

    requested_platforms: list[Platform] = []
    for p in platforms.split(","):
        p = p.strip()
        try:
            requested_platforms.append(Platform(p))
        except ValueError as err:
            console.print(
                f"[red]✗[/] Unknown platform [bold]{p}[/]. Choose from: {', '.join(PLATFORM_CHOICES)}"
            )
            raise typer.Exit(1) from err

    # ── Target directory ──────────────────────────────────────────────────────
    skill_dir = output_dir / name
    if skill_dir.exists():
        console.print(f"[red]✗[/] Directory [bold]{skill_dir}[/] already exists.")
        raise typer.Exit(1)

    console.print(
        f"\n[bold red]◈[/] Scaffolding [bold]{name}[/] from template [cyan]{template}[/]...\n"
    )

    # ── Copy template files ───────────────────────────────────────────────────
    template_src = find_templates_dir() / template
    shutil.copytree(template_src, skill_dir)

    # ── Build skill.json ──────────────────────────────────────────────────────
    manifest = SkillManifest(
        name=name,
        version="0.1.0",
        author=author or "unknown",
        description=f"A SkillForge skill: {name}",
        platforms=requested_platforms,
        declared_permissions=[],
        tools=[],
    )

    manifest_path = skill_dir / "skill.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json", exclude_none=True), indent=2)
    )

    # ── Write .skillforge.yml ─────────────────────────────────────────────────
    skill_forge_yml = skill_dir / ".skillforge.yml"
    skill_forge_yml.write_text(
        f"name: {name}\n"
        f"template: {template}\n"
        f"platforms: [{', '.join(p.value for p in requested_platforms)}]\n"
        f"auto_sign: true\n"
    )

    # ── Copy GitHub Actions workflow ──────────────────────────────────────────
    gha_dir = skill_dir / ".github" / "workflows"
    gha_dir.mkdir(parents=True, exist_ok=True)
    gha_workflow = find_templates_dir() / "_shared" / "skillforge.yml"
    if gha_workflow.exists():
        shutil.copy(gha_workflow, gha_dir / "skillforge.yml")

    # ── Print summary tree ────────────────────────────────────────────────────
    tree = Tree(f"[bold cyan]{name}/[/]")
    for p in sorted(skill_dir.rglob("*")):
        rel: Path = p.relative_to(skill_dir)
        parts = rel.parts
        for _part in parts[:-1]:
            # find or create subtree — simplified: just show flat for now
            pass
        icon = "📁" if p.is_dir() else "📄"
        tree.add(f"{icon} {rel}")

    console.print(tree)
    console.print(
        Panel(
            f"[green]✓ Skill scaffold created:[/] [bold]{skill_dir}[/]\n\n"
            f"Next steps:\n"
            f"  [cyan]cd {name}[/]\n"
            f"  [cyan]skillforge test[/]      — run LLM-as-judge evaluation\n"
            f"  [cyan]skillforge scan[/]      — security scan\n"
            f"  [cyan]skillforge compat[/]    — platform compatibility check\n"
            f"  [cyan]skillforge publish[/]   — sign and publish",
            title="[bold red]SkillForge[/]",
            border_style="dim red",
        )
    )
