"""Filesystem helpers for SkillForge."""

from __future__ import annotations

from pathlib import Path
from string import Template


def find_templates_dir() -> Path:
    """Locate the bundled templates directory."""
    # When installed via pip, templates sit next to this package
    pkg_root = Path(__file__).parent.parent.parent
    candidates = [
        pkg_root / "templates",
        Path(__file__).parent.parent / "templates",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "SkillForge templates directory not found. "
        "Reinstall with: pip install --force-reinstall skillforge"
    )


def render_template(template_path: Path, context: dict) -> str:
    """Render a $-style template file with the given context dict."""
    raw = template_path.read_text()
    return Template(raw).safe_substitute(context)
