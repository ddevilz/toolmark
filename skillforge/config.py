"""
SkillForge configuration loader.

Priority (highest → lowest):
  1. CLI flags (handled per-command with typer options)
  2. Environment variables  (SKILLFORGE_*)
  3. .skillforge.yml        (project-level)
  4. ~/.skillforge/config.yml (user-level)
  5. Built-in defaults
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from skillforge.models.skill import Platform

_PROJECT_CONFIG = Path(".skillforge.yml")
_USER_CONFIG = Path.home() / ".skillforge" / "config.yml"
_USER_KEY = Path.home() / ".skillforge" / "signing.key"
_USER_PUBKEY = Path.home() / ".skillforge" / "signing.pub"


class SkillForgeConfig(BaseModel):
    """Merged runtime configuration."""

    # LLM provider for test/bench judge calls
    llm_model: str = "anthropic/claude-sonnet-4-20250514"
    llm_api_key: str | None = None  # falls back to env ANTHROPIC_API_KEY etc.

    # Publish targets
    default_platforms: list[Platform] = Field(default_factory=lambda: [Platform.CLAWHUB])

    # Signing
    signing_key_path: Path = _USER_KEY
    auto_sign: bool = True

    # Scanner
    snyk_binary: str = "snyk"  # path or name on PATH
    scan_block_on_high: bool = True  # fail publish on HIGH findings

    # Bench
    bench_runs: int = 50

    # Registry endpoints
    clawhub_api: str = "https://api.clawhub.dev/v1"
    claude_code_api: str = "https://api.anthropic.com/v1/skills"
    cursor_api: str = "https://api.cursor.sh/v1/skills"
    windsurf_api: str = "https://api.windsurf.sh/v1/skills"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_config() -> SkillForgeConfig:
    """Merge user config → project config → env vars into a SkillForgeConfig."""
    data: dict[str, Any] = {}

    # 1. user-level defaults
    data.update(_load_yaml(_USER_CONFIG))

    # 2. project-level overrides
    data.update(_load_yaml(_PROJECT_CONFIG))

    # 3. env var overrides
    env_map = {
        "SKILLFORGE_LLM_MODEL": "llm_model",
        "SKILLFORGE_LLM_API_KEY": "llm_api_key",
        "SKILLFORGE_AUTO_SIGN": "auto_sign",
        "SKILLFORGE_SCAN_BLOCK_HIGH": "scan_block_on_high",
        "SKILLFORGE_BENCH_RUNS": "bench_runs",
        "ANTHROPIC_API_KEY": "llm_api_key",  # convenience alias
    }
    for env_key, field in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            data[field] = val

    return SkillForgeConfig(**data)


def write_project_config(config: dict[str, Any]) -> None:
    """Write or update .skillforge.yml in the current directory."""
    existing = _load_yaml(_PROJECT_CONFIG)
    existing.update(config)
    with _PROJECT_CONFIG.open("w") as f:
        yaml.safe_dump(existing, f, default_flow_style=False)


def ensure_user_dir() -> Path:
    """Create ~/.skillforge/ if it doesn't exist."""
    user_dir = Path.home() / ".skillforge"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir
