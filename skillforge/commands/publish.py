"""
skillforge publish — Sign and publish your skill to one or more registries.

Usage:
    skillforge publish
    skillforge publish --platforms clawhub,claude-code
    skillforge publish --no-sign --dry-run
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path

import typer
from rich.console import Console

from skillforge.models import Platform, SkillManifest, SkillSignature
from skillforge.utils.manifest import load_manifest

console = Console()

# Default options for typer to avoid B008 errors
DEFAULT_SKILL_DIR = Path(".")
DEFAULT_PLATFORMS = ""
DEFAULT_NO_SIGN = False
DEFAULT_DRY_RUN = False
DEFAULT_SKIP_SCAN = False


def _hash_skill(skill_dir: Path) -> str:
    """SHA-256 over SKILL.md + skill.json (sorted bytes concat)."""
    h = hashlib.sha256()
    for fname in ["SKILL.md", "skill.json"]:
        p = skill_dir / fname
        if p.exists():
            h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()


def _sign_skill(content_hash: str, key_path: Path) -> tuple[str, str]:
    """
    Sign content_hash with Ed25519 private key.
    Returns (public_key_fingerprint, base64_signature).
    """
    try:
        from nacl.encoding import HexEncoder
        from nacl.signing import SigningKey
    except ImportError as err:
        raise RuntimeError(
            "PyNaCl is required for signing. Install with: pip install pynacl"
        ) from err

    if not key_path.exists():
        raise FileNotFoundError(f"Signing key not found at {key_path}. Run: skillforge keygen")

    raw_key = bytes.fromhex(key_path.read_text().strip())
    signing_key = SigningKey(raw_key)
    signed = signing_key.sign(content_hash.encode(), encoder=HexEncoder)
    verify_key = signing_key.verify_key
    pubkey_hex = verify_key.encode(encoder=HexEncoder).decode()
    fingerprint = "sha256:" + hashlib.sha256(bytes.fromhex(pubkey_hex)).hexdigest()[:16]

    signature_b64 = base64.b64encode(signed.signature).decode()
    return fingerprint, signature_b64


def _publish_to_clawhub(manifest: SkillManifest, skill_dir: Path, dry_run: bool) -> bool:
    """POST skill to ClawHub API."""
    import httpx

    from skillforge.config import load_config

    cfg = load_config()

    console.print(f"  [cyan]→ ClawHub[/] {cfg.clawhub_api}/skills ...", end=" ")
    if dry_run:
        console.print("[yellow]DRY RUN[/]")
        return True

    payload = {
        "manifest": manifest.model_dump(mode="json", exclude_none=True),
        "skill_md": (skill_dir / "SKILL.md").read_text()
        if (skill_dir / "SKILL.md").exists()
        else "",
    }
    try:
        r = httpx.post(
            f"{cfg.clawhub_api}/skills",
            json=payload,
            timeout=30,
            headers={"User-Agent": "skillforge/0.1.0"},
        )
        if r.status_code in (200, 201):
            console.print("[green]✓[/]")
            return True
        else:
            console.print(f"[red]✗ {r.status_code}[/]")
            return False
    except Exception as e:
        console.print(f"[red]✗ {e}[/]")
        return False


_REGISTRY_PUBLISHERS = {
    Platform.CLAWHUB: _publish_to_clawhub,
    # TODO: Platform.CLAUDE_CODE, Platform.CURSOR, Platform.WINDSURF
}


def publish_command(
    skill_dir: Path = typer.Option(DEFAULT_SKILL_DIR, "--dir", "-d", help="Path to skill project"),
    platforms: str = typer.Option(
        DEFAULT_PLATFORMS, "--platforms", "-p", help="Comma-separated publish targets"
    ),
    no_sign: bool = typer.Option(
        DEFAULT_NO_SIGN, "--no-sign", help="Skip Ed25519 provenance signing"
    ),
    dry_run: bool = typer.Option(
        DEFAULT_DRY_RUN, "--dry-run", help="Validate and sign but don't upload"
    ),
    skip_scan: bool = typer.Option(
        DEFAULT_SKIP_SCAN, "--skip-scan", help="Skip security scan gate (not recommended)"
    ),
) -> None:
    """Sign and publish skill to ClawHub, Claude Code, Cursor, or Windsurf."""
    from skillforge.commands.scan import scan_command
    from skillforge.config import load_config

    # Convert string path to Path object
    skill_dir = Path(skill_dir)

    cfg = load_config()

    # ── Security gate ─────────────────────────────────────────────────────────
    if not skip_scan:
        console.print("\n[bold red]◈[/] Running security gate before publish...\n")
        try:
            scan_command(skill_dir=skill_dir)
        except SystemExit as e:
            if e.code != 0:
                console.print(
                    "[red]✗ Publish blocked by security findings. Fix issues or use --skip-scan.[/]"
                )
                raise typer.Exit(1) from e

    manifest = load_manifest(skill_dir)

    # ── Signing ───────────────────────────────────────────────────────────────
    if not no_sign and cfg.auto_sign:
        console.print("\n[bold red]◈[/] Signing skill...", end=" ")
        try:
            content_hash = _hash_skill(skill_dir)
            fingerprint, _ = _sign_skill(content_hash, cfg.signing_key_path)
            manifest.signature = SkillSignature(
                public_key_fingerprint=fingerprint,
                content_hash=content_hash,
                signed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                signer=manifest.author,
            )
            # Write signature back into skill.json
            skill_json = skill_dir / "skill.json"
            data = json.loads(skill_json.read_text())
            data["signature"] = manifest.signature.model_dump()
            skill_json.write_text(json.dumps(data, indent=2))
            console.print(f"[green]✓[/] [{fingerprint[:24]}...]")
        except Exception as e:
            console.print(f"[red]✗ Signing failed: {e}[/]")
            raise typer.Exit(1) from e

    # ── Determine platforms ───────────────────────────────────────────────────
    if platforms:
        target_platforms = [Platform(p.strip()) for p in platforms.split(",")]
    else:
        target_platforms = manifest.platforms or [Platform.CLAWHUB]

    console.print(
        f"\n[bold red]◈[/] Publishing [bold]{manifest.name}[/] v{manifest.version} to {len(target_platforms)} platform(s)...\n"
    )

    success_count = 0
    for platform in target_platforms:
        publisher = _REGISTRY_PUBLISHERS.get(platform)
        if publisher:
            ok = publisher(manifest, skill_dir, dry_run)
            if ok:
                success_count += 1
        else:
            console.print(f"  [yellow]⚠ {platform.value}[/] publish not yet implemented in v0.1")

    console.print(
        f"\n[{'green' if success_count == len(target_platforms) else 'yellow'}]"
        f"{'✓' if success_count == len(target_platforms) else '⚠'} "
        f"{success_count}/{len(target_platforms)} platforms published.[/]\n"
    )

    if success_count < len(target_platforms):
        raise typer.Exit(1)
