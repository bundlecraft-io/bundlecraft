#!/usr/bin/env python3
"""
builder.py
Orchestrates the three core BundleCraft stages: fetch → convert → verify

Architecture:
  1) FETCH: Stage certificate sources (local includes + remote fetches) per bundle config
  2) CONVERT: Aggregate staged sources into canonical PEM, then convert to requested formats
  3) VERIFY: Validate certificates and produce compliance reports

Changes from legacy builder:
  - Removed --prefetch flag (fetch is now always executed)
    - Staging directory: sources/staged/<craft>/<bundle>/ (cleaner separation from sources/)
    - Build output: dist/<craft>/<target>/ (craft display name and target name)
  - Clearer orchestration: each stage is self-contained with explicit inputs/outputs
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import click

from bundlecraft.helpers.convert_utils import convert_to_formats
from bundlecraft.helpers.utils import ensure_dir, load_yaml, sha256_file

# ---------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
ROOT = CURRENT_DIR.parent
CONFIG_DIR = ROOT / "config"
SOURCES_DIR = ROOT / "sources"
STAGED_DIR = SOURCES_DIR / "staged"
DIST_DIR = ROOT / "dist"


# ---------------------------------------------------------------------
# Stage 1: FETCH
# ---------------------------------------------------------------------


def _clean_dir(path: Path) -> None:
    """Recursively remove all files and subdirectories."""
    if path.exists():
        for p in sorted(path.rglob("*"), reverse=True):
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    p.rmdir()
            except Exception:
                pass


def _stage_bundle_sources(
    bundle_name: str, env: str, workspace_root: Path, verbose: bool = False
) -> Path:
    """Stage a bundle's sources (includes + fetch) into sources/staged/<env>/<bundle>/.

    This mirrors the fetch CLI behavior but writes to a staging area for build.
    Returns the staging directory path.
    """
    from bundlecraft.fetch import (
        _fetch_each_to_named_dirs,
        _stage_local_includes,
        load_yaml,
    )

    bundle_cfg_path = CONFIG_DIR / "bundles" / f"{bundle_name}.yaml"
    bundle_cfg = load_yaml(bundle_cfg_path, required=True)

    staging_root = STAGED_DIR / env / bundle_name
    ensure_dir(staging_root)

    # Clean staging dir
    if verbose:
        click.echo(f"[Fetch] Cleaning staging: {staging_root}", err=True)
    _clean_dir(staging_root)
    ensure_dir(staging_root)

    # Stage local includes
    if verbose:
        click.echo(f"[Fetch] Staging local includes for bundle: {bundle_name}", err=True)
    _stage_local_includes(bundle_cfg, staging_root, workspace_root, verbose)

    # Stage remote fetches
    fetch_cfg = bundle_cfg.get("fetch") or []
    if fetch_cfg:
        if verbose:
            click.echo(
                f"[Fetch] Fetching {len(fetch_cfg)} remote source(s) for bundle: {bundle_name}",
                err=True,
            )
        _fetch_each_to_named_dirs(
            fetch_cfg, staging_root, workspace_root, verbose, name_filter=None
        )

    return staging_root


# ---------------------------------------------------------------------
# Stage 2: CONVERT (aggregate + format conversion)
# ---------------------------------------------------------------------


def _read_pem_chunks(paths: list[Path]) -> list[str]:
    """Extract PEM certificate blocks from a list of file paths."""
    start, end = "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"
    blocks = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        buf, inside = [], False
        for line in text.splitlines():
            if start in line:
                inside = True
                buf = [line]
            elif end in line and inside:
                buf.append(line)
                blocks.append("\n".join(buf) + "\n")
                inside = False
            elif inside:
                buf.append(line)
    return blocks


def _dedupe_pem_blocks(pem_blocks: list[str]) -> list[str]:
    """Deduplicate PEM blocks by SHA256 fingerprint, preserving order."""
    import base64
    import hashlib
    import re

    seen, out = set(), []
    b64re = re.compile(
        r"-----BEGIN CERTIFICATE-----\s*([A-Za-z0-9+/=\s]+)-----END CERTIFICATE-----",
        re.S,
    )
    for blk in pem_blocks:
        m = b64re.search(blk)
        if not m:
            continue
        der = base64.b64decode("".join(m.group(1).split()))
        h = hashlib.sha256(der).hexdigest()
        if h not in seen:
            seen.add(h)
            out.append(blk if blk.endswith("\n") else blk + "\n")
    return out


def _write_canonical_pem(
    dst: Path, pem_blocks: list[str], include_subject_comments: bool, *, force: bool = False
) -> None:
    """Write canonical PEM with optional subject comments."""
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    ensure_dir(dst.parent)
    lines = []
    for blk in pem_blocks:
        if include_subject_comments:
            try:
                cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
                subj = cert.subject.rfc4514_string()
                lines.append(f"# Subject: {subj}\n")
            except Exception:
                lines.append("# Subject: (unparsable)\n")
        lines.append(blk if blk.endswith("\n") else blk + "\n")
    dst.write_text("".join(lines), encoding="utf-8")


def _aggregate_staged_sources(staging_dirs: list[Path], verbose: bool = False) -> list[Path]:
    """Aggregate all PEM files from staging directories.

    Walks each staging dir and collects all .pem files.
    Returns list of paths to aggregate.
    """
    pem_files = []
    for staging_dir in staging_dirs:
        if not staging_dir.exists():
            if verbose:
                click.echo(f"[Convert] Staging dir not found (skipping): {staging_dir}", err=True)
            continue
        for pem_path in sorted(staging_dir.rglob("*.pem")):
            if pem_path.is_file():
                pem_files.append(pem_path)
                if verbose:
                    click.echo(f"[Convert] Including: {pem_path.relative_to(ROOT)}", err=True)
    return pem_files


# ---------------------------------------------------------------------
# Stage 3: VERIFY
# ---------------------------------------------------------------------


def _verify_certificates(
    pem_blocks: list[str], fail_on_expired: bool, warn_days: int
) -> tuple[list[str], list[str]]:
    """Verify certificates for expiration and validity.

    Returns (errors, warnings) lists.
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    now = dt.datetime.now(dt.timezone.utc)
    soon_cutoff = now + dt.timedelta(days=warn_days)
    errs, warns = [], []

    for i, blk in enumerate(pem_blocks, 1):
        try:
            cert = x509.load_pem_x509_certificate(blk.encode("utf-8"), default_backend())
            subject = cert.subject.rfc4514_string()
            exp = getattr(cert, "not_valid_after_utc", None)
            if exp is not None and exp.tzinfo is None:
                exp = exp.replace(tzinfo=dt.timezone.utc)
            if exp < now:
                errs.append(f"Expired: {subject} (expired {exp.date()})")
            elif exp < soon_cutoff:
                warns.append(f"Expiring soon: {subject} ({(exp - now).days} days left)")
        except Exception as e:
            errs.append(f"Parse error (block {i}): {e}")

    return errs, warns


# ---------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--craft",
    "--env",
    "env",
    required=True,
    help="Craft name (e.g., dev, prod). Alias: --env (legacy)",
)
@click.option(
    "--bundle",
    required=False,
    help=(
        "Target name to build (from craft 'targets'). If omitted, builds all targets in the craft. "
        "For legacy behavior, provide a bundle name not present in targets to build that bundle directly."
    ),
)
@click.option(
    "--verify-only",
    is_flag=True,
    help="Skip build; only verify existing output or staged sources",
)
@click.option(
    "--skip-fetch",
    is_flag=True,
    help="Skip fetch stage; use existing staged sources (for iteration)",
)
@click.option(
    "--skip-verify",
    is_flag=True,
    help="Skip verification stage (not recommended for production)",
)
@click.option(
    "--output-root",
    type=str,
    default="dist",
    help="Root directory for build outputs (default: ./dist). Outputs are written under dist/<craft-name>/<target-name>.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output for all stages",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing output files (passes through to conversion stage)",
)
def main(env, bundle, verify_only, skip_fetch, skip_verify, output_root, verbose, force):
    """Build trust bundles by orchestrating: fetch → convert → verify.

    This command coordinates the three core BundleCraft stages:
      1. FETCH: Stage certificate sources from bundle configs
      2. CONVERT: Aggregate and convert to requested output formats
      3. VERIFY: Validate certificates and produce reports

    The build always fetches unless --skip-fetch is used (for fast iteration).
    """
    click.secho("\n🔐 BundleCraft Builder\n---------------------", fg="cyan")

    # Load craft config
    craft_path = CONFIG_DIR / "crafts" / f"{env}.yaml"
    legacy_env_path = CONFIG_DIR / "envs" / f"{env}.yaml"
    cfg_path = craft_path if craft_path.exists() else legacy_env_path

    if not cfg_path.exists():
        click.secho(f"[ERROR] Craft config not found: {env}", fg="red", err=True)
        sys.exit(2)

    env_cfg = load_yaml(cfg_path, required=True)

    # Normalize targets from craft config
    raw_targets = env_cfg.get("targets") or {}
    targets_map: dict[str, dict] = {}
    if isinstance(raw_targets, list):
        # Support list form: [{ target_name: str, include_bundles|includes|compose: [...] }]
        for item in raw_targets:
            if not isinstance(item, dict):
                continue
            tname = item.get("target_name") or item.get("name")
            if not tname:
                continue
            includes = (
                item.get("include_bundles") or item.get("includes") or item.get("compose") or []
            )
            targets_map[tname] = {"include_bundles": includes}
    elif isinstance(raw_targets, dict):
        for tname, entry in raw_targets.items():
            entry = entry or {}
            includes = (
                entry.get("include_bundles") or entry.get("includes") or entry.get("compose") or []
            )
            targets_map[tname] = {"include_bundles": includes}

    # Determine which target(s) to build
    targets_to_build: list[tuple[str, list[str]]] = []  # (target_name, include_bundles)
    if bundle:
        if bundle in targets_map:
            targets_to_build.append((bundle, list(targets_map[bundle]["include_bundles"])))
        else:
            # Legacy direct-bundle build as a single-target with same name
            targets_to_build.append((bundle, [bundle]))
    else:
        if targets_map:
            for tname, entry in targets_map.items():
                targets_to_build.append((tname, list(entry["include_bundles"])))
        else:
            click.secho(
                "[ERROR] No targets found in craft config and no --bundle provided.",
                fg="red",
                err=True,
            )
            sys.exit(2)

    # =========================================================================
    # STAGE 1: FETCH
    # =========================================================================
    staging_map: dict[str, list[Path]] = {}
    if not skip_fetch:
        click.secho(
            f"\n[STAGE 1/3] FETCH - Staging sources for {len(targets_to_build)} target(s)",
            fg="blue",
            bold=True,
        )
        for target_name, include_bundles in targets_to_build:
            per_target: list[Path] = []
            for bname in include_bundles:
                try:
                    staging_dir = _stage_bundle_sources(bname, env, ROOT, verbose=verbose)
                    per_target.append(staging_dir)
                    click.secho(
                        f"  [{target_name}] ✓ Staged bundle: {bname} → {staging_dir.relative_to(ROOT)}",
                        fg="green",
                    )
                except Exception as e:
                    click.secho(
                        f"  [{target_name}] ✗ Failed to stage bundle {bname}: {e}",
                        fg="red",
                        err=True,
                    )
                    if verbose:
                        import traceback

                        traceback.print_exc()
                    sys.exit(2)
            staging_map[target_name] = per_target
    else:
        click.secho("\n[STAGE 1/3] FETCH - Skipped (using existing staged sources)", fg="yellow")
        for target_name, include_bundles in targets_to_build:
            per_target = []
            for bname in include_bundles:
                per_target.append(STAGED_DIR / env / bname)
            staging_map[target_name] = per_target

    # =========================================================================
    # STAGE 2: CONVERT
    # =========================================================================
    click.secho("\n[STAGE 2/3] CONVERT - Aggregating and converting formats", fg="blue", bold=True)
    craft_name_for_path = env_cfg.get("name") or env
    safe_craft = str(craft_name_for_path).replace("/", "-").replace(" ", "-")

    # Settings from craft
    pem_cfg = env_cfg.get("pem") or {}
    include_subject_comments = pem_cfg.get("include_subject_comments", True)
    output_formats = env_cfg.get("output_formats") or ["pem"]
    fmt_overrides = env_cfg.get("format_overrides") or {}

    per_target_results: dict[str, dict] = {}
    for target_name, dirs_list in staging_map.items():
        pem_files = _aggregate_staged_sources(dirs_list, verbose=verbose)
        if not pem_files:
            click.secho(
                f"  [ERROR] [{target_name}] No certificate sources found in staging.",
                fg="red",
                err=True,
            )
            sys.exit(2)
        click.secho(f"  [{target_name}] Found {len(pem_files)} source file(s)", fg="green")

        pem_blocks = _read_pem_chunks(pem_files)
        pem_blocks = _dedupe_pem_blocks(pem_blocks)
        if not pem_blocks:
            click.secho(
                f"  [ERROR] [{target_name}] No valid PEM certificates parsed.", fg="red", err=True
            )
            sys.exit(3)
        click.secho(
            f"  [{target_name}] Deduplicated to {len(pem_blocks)} unique certificate(s)", fg="green"
        )

        build_root = (Path(output_root) / safe_craft / target_name).resolve()
        ensure_dir(build_root)

        pem_out = build_root / "bundlecraft-ca-trust.pem"
        _write_canonical_pem(pem_out, pem_blocks, include_subject_comments, force=force)
        click.secho(
            f"  [{target_name}] ✓ Wrote canonical PEM: {pem_out.relative_to(ROOT)}", fg="green"
        )

        extra_formats = [fmt for fmt in output_formats if fmt.lower() != "pem"]
        if extra_formats:
            fmt_overrides_combined = dict(fmt_overrides)
            if force:
                fmt_overrides_combined["force"] = True
            convert_to_formats(
                pem_out, build_root, extra_formats, fmt_overrides_combined, "bundlecraft-ca-trust"
            )
            click.secho(
                f"  [{target_name}] ✓ Converted to formats: {', '.join(extra_formats)}", fg="green"
            )

        per_target_results[target_name] = {
            "build_root": build_root,
            "pem_blocks": pem_blocks,
            "output_formats": output_formats,
        }

    # =========================================================================
    # STAGE 3: VERIFY
    # =========================================================================
    if not skip_verify:
        click.secho("\n[STAGE 3/3] VERIFY - Validating certificates", fg="blue", bold=True)
        verify_cfg = env_cfg.get("verify") or {}
        fail_on_expired = (
            verify_cfg.get("fail_on_expired", True) if isinstance(verify_cfg, dict) else True
        )
        warn_days = (
            verify_cfg.get("warn_days_before_expiry", 30) if isinstance(verify_cfg, dict) else 30
        )
        for target_name, result in per_target_results.items():
            pem_blocks = result["pem_blocks"]
            errs, warns = _verify_certificates(pem_blocks, fail_on_expired, warn_days)
            for e in errs:
                click.secho(f"  [{target_name}] [ERROR] {e}", fg="red")
            for w in warns:
                click.secho(f"  [{target_name}] [WARN] {w}", fg="yellow")
            if errs:
                click.secho(
                    f"  [{target_name}] [SUMMARY] {len(errs)} expired/invalid certificate(s)",
                    fg="red",
                )
                if fail_on_expired:
                    click.secho("  Build FAILED due to expired certificates", fg="red", err=True)
                    sys.exit(5)
            if warns:
                click.secho(
                    f"  [{target_name}] [SUMMARY] {len(warns)} certificate(s) expiring within {warn_days} days",
                    fg="yellow",
                )
            if not errs and not warns:
                click.secho(
                    f"  [{target_name}] ✓ All certificates are valid and healthy", fg="green"
                )
    else:
        click.secho("\n[STAGE 3/3] VERIFY - Skipped", fg="yellow")

    # =========================================================================
    # FINALIZE: Manifest and checksums
    # =========================================================================
    click.secho("\nFinalizing build artifacts...", fg="blue")

    # Build manifest and checksums per target
    for target_name, result in per_target_results.items():
        build_root = result["build_root"]
        pem_blocks = result["pem_blocks"]
        output_formats = result["output_formats"]
        manifest_obj = {
            "craft": env_cfg.get("name") or env,
            "environment": env,  # retained for compatibility
            "target": target_name,
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "certificate_count": len(pem_blocks),
            "output_formats": output_formats,
        }
        # Add verification summary if not skipped (same policy for all targets)
        if not skip_verify:
            manifest_obj["verification"] = {
                "fail_on_expired": (
                    verify_cfg.get("fail_on_expired", True)
                    if isinstance(verify_cfg, dict)
                    else True
                ),
                "warn_days": (
                    verify_cfg.get("warn_days_before_expiry", 30)
                    if isinstance(verify_cfg, dict)
                    else 30
                ),
            }
        output_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])
        manifest_obj["files"] = [
            {"path": fname, "sha256": sha256_file(build_root / fname)}
            for fname in output_files
            if fname != "manifest.json"
        ]
        manifest_path = build_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        click.secho(
            f"  [{target_name}] ✓ Wrote manifest: {manifest_path.relative_to(ROOT)}", fg="green"
        )

        all_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])
        checksum_lines = [f"{sha256_file(build_root / fname)}  {fname}" for fname in all_files]
        checksum_path = build_root / "checksums.sha256"
        checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        click.secho(
            f"  [{target_name}] ✓ Wrote checksums: {checksum_path.relative_to(ROOT)}", fg="green"
        )

    click.secho(
        "\n✅ Build complete for target(s): " + ", ".join(per_target_results.keys()),
        fg="bright_green",
        bold=True,
    )


if __name__ == "__main__":
    main()
