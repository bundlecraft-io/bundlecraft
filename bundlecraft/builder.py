#!/usr/bin/env python3
"""
builder.py
Orchestrates the three core BundleCraft stages: fetch → convert → verify

Architecture:
  1) FETCH: Stage certificate sources (local includes + remote fetches) per source config
  2) CONVERT: Aggregate staged sources into canonical PEM, then convert to requested formats per env config
  3) VERIFY: Validate certificates and produce compliance reports

"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import logging
import sys
import tarfile
from pathlib import Path

import click
import yaml

from bundlecraft.helpers.atomic_build import AtomicBuildContext
from bundlecraft.helpers.config_schema import (
    validate_defaults_config,
    validate_env_config,
    validate_source_config,
)
from bundlecraft.helpers.convert_utils import convert_to_formats
from bundlecraft.helpers.exit_codes import ExitCode
from bundlecraft.helpers.json_output import suppress_output
from bundlecraft.helpers.template_utils import expand_output_metadata
from bundlecraft.helpers.utils import ensure_dir, load_yaml, sha256_file

# ---------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent


def _detect_workspace_root() -> Path:
    """Determine the workspace root for configs and sources.

    Priority:
      1) BUNDLECRAFT_WORKSPACE environment variable, if set and exists
      2) Current working directory if it looks like a BundleCraft workspace (has config/)
      3) Package repo root (parent of this file) as a final fallback (dev/editable installs)
    """
    import os as _os

    env_root = _os.environ.get("BUNDLECRAFT_WORKSPACE")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.exists():
            return p
    cwd = Path.cwd().resolve()
    if (cwd / "config").exists():
        return cwd
    return CURRENT_DIR.parent


ROOT = _detect_workspace_root()
CONFIG_DIR = ROOT / "config"
SOURCES_DIR = ROOT / "cert_sources"
STAGED_DIR = SOURCES_DIR / "staged"
DIST_DIR = ROOT / "dist"
# (no tag-based bundle composition helpers)


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
    bundle_name: str,
    env: str,
    workspace_root: Path,
    verbose: bool = False,
    dry_run: bool = False,
    json_output: bool = False,
) -> Path:
    """Stage a bundle's sources (includes + fetch) into cert_sources/staged/<source_name>/.

    Args:
        env: Environment config file identifier (e.g., 'dev' for config/envs/dev.yaml)

    This mirrors the fetch CLI behavior but writes to a staging area for build.
    Returns the staging directory path.
    """
    from bundlecraft.fetch import (
        _fetch_each_to_named_dirs,
        _stage_local_includes,
        _validate_source_and_fetch_names,
        load_yaml,
    )
    from bundlecraft.fetch import logger as fetch_logger

    # Suppress fetch logging in JSON mode
    if json_output:
        fetch_logger.setLevel(logging.CRITICAL)
    else:
        fetch_logger.setLevel(logging.INFO)

    source_cfg_path = CONFIG_DIR / "sources" / f"{bundle_name}.yaml"
    source_cfg = load_yaml(source_cfg_path, required=True, validate=validate_source_config)
    # Validate local repo and fetch names
    try:
        _validate_source_and_fetch_names(source_cfg)
    except Exception as e:
        raise click.ClickException(str(e)) from e

    # Use the explicit source_name from the source config if provided; fallback to file stem
    source_name = source_cfg.get("source_name") or bundle_name
    staging_root = STAGED_DIR / source_name

    if dry_run:
        if verbose:
            click.secho(
                f"[Fetch] [dry-run] Would stage bundle sources to: {staging_root}",
                fg="yellow",
                err=True,
            )
        return staging_root

    ensure_dir(staging_root)

    # Clean staging dir
    if verbose:
        click.echo(f"[Fetch] Cleaning staging: {staging_root}", err=True)
    _clean_dir(staging_root)
    ensure_dir(staging_root)

    # Stage local includes
    if verbose:
        click.echo(f"[Fetch] Staging local includes for source: {bundle_name}", err=True)
    _stage_local_includes(source_cfg, staging_root, workspace_root, verbose)

    # Stage remote fetches
    fetch_cfg = source_cfg.get("fetch") or []
    if fetch_cfg:
        if verbose:
            click.echo(
                f"[Fetch] Fetching {len(fetch_cfg)} remote source(s) for source: {bundle_name}",
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
    dst: Path,
    pem_blocks: list[str],
    include_subject_comments: bool,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Write canonical PEM with optional subject comments."""
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    if dry_run:
        click.secho(
            f"  [dry-run] Would write {len(pem_blocks)} certificate(s) to: {dst}", fg="yellow"
        )
        return

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
# Deterministic tar packaging
# ---------------------------------------------------------------------


def _create_deterministic_tar(build_root: Path, output_name: str = "package") -> Path:
    """Create a deterministic tar.gz archive with normalized metadata.

    All files in build_root (except the tar itself) are added with:
    - mtime=0 (epoch time)
    - uid=0, gid=0
    - uname='', gname=''
    - Sorted entries for consistent ordering
    - gzip mtime=0 for deterministic compression

    Returns the path to the created tar.gz file.
    """
    import io

    tar_path = build_root / f"{output_name}.tar.gz"

    # Exclude known non-deterministic or meta files
    exclude_names = {
        tar_path.name,
        "manifest.json",
        "checksums.sha256",
        "metadata.yaml",
        "sbom.json",
        "README.md",  # Exclude any user-facing README from packaging
    }

    # Collect files to add with deterministic ordering
    files_to_add = []
    for f in build_root.glob("*"):
        if not f.is_file():
            continue
        if f.name in exclude_names:
            continue
        # Skip signature sidecars
        if f.suffix in {".asc", ".sig"}:
            continue
        files_to_add.append(f)
    files_to_add.sort(key=lambda p: p.name)

    # Create tar in memory first
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for file_path in files_to_add:
            # Create TarInfo with normalized metadata
            tarinfo = tar.gettarinfo(file_path, arcname=file_path.name)
            tarinfo.mtime = 0  # Epoch time for determinism
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.uname = ""
            tarinfo.gname = ""
            # Normalize file mode to ensure parity across environments
            # Use 0644 for regular files
            try:
                if tarinfo.isfile():
                    tarinfo.mode = 0o644
            except Exception:
                # Best-effort; ignore if not applicable
                pass
            if tarinfo.pax_headers:
                for key in ("atime", "ctime"):
                    tarinfo.pax_headers.pop(key, None)

            # Add file with normalized metadata
            with open(file_path, "rb") as f:
                tar.addfile(tarinfo, f)

    # Write compressed tar with mtime=0 for gzip determinism
    tar_buffer.seek(0)
    with gzip.GzipFile(filename="", fileobj=open(tar_path, "wb"), mode="wb", mtime=0) as gz:
        gz.write(tar_buffer.read())

    return tar_path


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
    "--env",
    "env",
    required=True,
    help="Environment identifier from config/envs/<env>.yaml (e.g., dev, prod). References the config file stem, not the display name.",
)
@click.option(
    "--bundle",
    required=False,
    help=(
        "Bundle name to build (from environment 'bundles'). If omitted, builds all bundles in the environment. "
        "For legacy behavior, provide a source name not present in bundles to build that source directly."
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
    help="Root directory for build outputs (default: ./dist). Outputs are written under dist/<env-name>/<bundle-name>.",
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
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually writing any files or executing commands",
)
@click.option(
    "--sign",
    is_flag=True,
    help="Sign release artifacts with GPG (requires --gpg-key-id or GPG_KEY_ID env var)",
)
@click.option(
    "--gpg-key-id",
    type=str,
    help="GPG key ID to use for signing. Can also be set via GPG_KEY_ID environment variable.",
)
@click.option(
    "--generate-sbom",
    is_flag=True,
    default=True,
    help="Generate SBOM (Software Bill of Materials) in CycloneDX format (enabled by default)",
)
@click.option(
    "--no-sbom",
    is_flag=True,
    help="Skip SBOM generation",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit machine-readable JSON output (suppresses human-readable output)",
)
@click.option(
    "--keep-temp",
    is_flag=True,
    help="Preserve temporary build directories on failure (for debugging)",
)
def main(
    env,
    bundle,
    verify_only,
    skip_fetch,
    skip_verify,
    output_root,
    verbose,
    force,
    dry_run,
    sign,
    gpg_key_id,
    generate_sbom,
    no_sbom,
    json_output,
    keep_temp,
):
    """Build trust bundles by orchestrating: fetch → convert → verify.

    This command coordinates the three core BundleCraft stages:
      1. FETCH: Stage certificate sources from source configs
      2. CONVERT: Aggregate and convert to requested output formats
      3. VERIFY: Validate certificates and produce reports

    The build always fetches unless --skip-fetch is used (for fast iteration).
    Use --dry-run to preview what would be done without making any changes.

    Signing and SBOM:
      - Use --sign to GPG-sign all release artifacts (requires GPG key)
      - SBOM (Software Bill of Materials) is generated by default
      - Use --no-sbom to skip SBOM generation
    """
    # Handle SBOM flag logic
    if no_sbom:
        generate_sbom = False
    # Track errors and targets for JSON output
    json_errors = []
    json_targets = []

    if not json_output:
        from bundlecraft.helpers.ui import print_banner

        # Unified banner
        print_banner("Builder")

        if dry_run:
            click.secho(
                "[DRY RUN MODE] No files will be written or commands executed\n",
                fg="yellow",
                bold=True,
            )

    # Load defaults and env config with proper precedence
    from bundlecraft.helpers.utils import merge_configs

    defaults = (
        load_yaml(CONFIG_DIR / "defaults.yaml", required=False, validate=validate_defaults_config)
        or {}
    )
    env_path = CONFIG_DIR / "envs" / f"{env}.yaml"

    if not env_path.exists():
        # Preserve the phrase "environment config not found" for test compatibility,
        # while still showing the expected path explicitly.
        error_msg = f"Environment config not found: config/envs/{env}.yaml"
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_build_response, emit_json

            emit_json(
                create_build_response(
                    success=False, environment=env, bundles=[], errors=json_errors
                )
            )
        else:
            click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
        sys.exit(ExitCode.CONFIG_ERROR)

    env_cfg_raw = load_yaml(env_path, required=True, validate=validate_env_config)
    env_cfg = merge_configs(defaults, env_cfg_raw)

    # Normalize bundles from environment config
    raw_bundles = env_cfg.get("bundles") or {}
    bundles_map: dict[str, dict] = {}
    if isinstance(raw_bundles, dict):
        for bname, entry in raw_bundles.items():
            entry = entry or {}
            sources = list(entry.get("include_sources") or [])
            bundles_map[bname] = {"include_sources": sources}

    # Determine which bundle(s) to build
    bundles_to_build: list[tuple[str, list[str]]] = []  # (bundle_name, include_sources)
    if bundle:
        if bundle in bundles_map:
            bundles_to_build.append((bundle, list(bundles_map[bundle]["include_sources"])))
        else:
            # Legacy direct-source build as a single-bundle with same name
            bundles_to_build.append((bundle, [bundle]))
    else:
        if bundles_map:
            for bname, entry in bundles_map.items():
                bundles_to_build.append((bname, list(entry["include_sources"])))
        else:
            if not json_output:
                click.secho(
                    "[ERROR] No bundles found in environment config and no --bundle provided.",
                    fg="red",
                    err=True,
                )
            else:
                error_msg = "No bundles found in environment config and no --bundle provided."
                json_errors.append(error_msg)
                from bundlecraft.helpers.json_output import create_build_response, emit_json

                emit_json(
                    create_build_response(
                        success=False, environment=env, bundles=[], errors=json_errors
                    )
                )
            sys.exit(ExitCode.CONFIG_ERROR)

    # Precompute environment-safe path and output settings used during caching
    env_name_for_path = env_cfg.get("name") or env
    safe_env = str(env_name_for_path).replace("/", "-").replace(" ", "-")

    # Settings from env (needed for cache conversion)
    pem_cfg = env_cfg.get("pem") or {}
    include_subject_comments = pem_cfg.get("include_subject_comments", True)
    output_formats = env_cfg.get("output_formats") or ["pem"]
    fmt_overrides = env_cfg.get("format_overrides") or {}

    # =========================================================================
    # STAGE 1: FETCH (unique bundle staging + caching)
    # =========================================================================
    staging_map: dict[str, list[Path]] = {}

    # Collect unique source names across bundles
    unique_sources: list[str] = []
    for _, include_sources in bundles_to_build:
        for s in include_sources:
            if s not in unique_sources:
                unique_sources.append(s)

    bundle_cache_root = ROOT / "build_cache" / safe_env
    bundle_cache_root.mkdir(parents=True, exist_ok=True)
    bundle_cache_dirs: dict[str, Path] = {}

    if not skip_fetch:
        if not json_output:
            click.secho(
                f"\n[STAGE 1/3] FETCH - Staging and caching {len(unique_sources)} unique certificate source(s)",
                fg="blue",
                bold=True,
            )
        for bname in unique_sources:
            if not json_output:
                click.secho(f"Staging certificate source: {bname}", fg="cyan")
            try:
                staging_dir = _stage_bundle_sources(
                    bname, env, ROOT, verbose=verbose, dry_run=dry_run, json_output=json_output
                )
                if dry_run:
                    if not json_output:
                        click.secho(
                            f"  [cache] [dry-run] Would stage certificates: {bname} → {staging_dir.relative_to(ROOT)}",
                            fg="yellow",
                        )
                else:
                    if not json_output:
                        click.secho(
                            f"  [cache] ✓ Staged certificates: {bname} → {staging_dir.relative_to(ROOT)}",
                            fg="green",
                        )

                cache_dir = bundle_cache_root / bname
                if not dry_run:
                    ensure_dir(cache_dir)

                if dry_run:
                    # In dry-run, simulate having cached bundles
                    click.secho(
                        f"  [cache] [dry-run] Would write cached PEM to: {cache_dir / 'bundlecraft-ca-trust.pem'}",
                        fg="yellow",
                    )
                    if (
                        output_formats
                        and len([fmt for fmt in output_formats if fmt.lower() != "pem"]) > 0
                    ):
                        extra_formats = [fmt for fmt in output_formats if fmt.lower() != "pem"]
                        click.secho(
                            f"  [cache] [dry-run] Would convert to formats: {', '.join(extra_formats)}",
                            fg="yellow",
                        )
                    bundle_cache_dirs[bname] = cache_dir
                    continue

                # Aggregate and write canonical PEM into cache
                pem_files = _aggregate_staged_sources([staging_dir], verbose=verbose)
                if not pem_files:
                    click.secho(
                        f"  [cache] [ERROR] {bname} - no sources found in staging",
                        fg="red",
                        err=True,
                    )
                    sys.exit(ExitCode.BUILD_ERROR)
                pem_blocks = _read_pem_chunks(pem_files)

                # Apply filters from merged config
                from bundlecraft.helpers.utils import apply_filters

                filters_cfg = env_cfg.get("filters") or {}
                pem_blocks = apply_filters(pem_blocks, filters_cfg)

                if not pem_blocks:
                    click.secho(
                        f"  [cache] [ERROR] {bname} - no valid PEM parsed", fg="red", err=True
                    )
                    sys.exit(ExitCode.INVALID_CERT)
                cache_pem = cache_dir / "bundlecraft-ca-trust.pem"
                _write_canonical_pem(
                    cache_pem, pem_blocks, include_subject_comments, force=True, dry_run=dry_run
                )
                if not json_output:
                    click.secho(
                        f"  [cache] ✓ Wrote cached canonical PEM: {cache_pem.relative_to(ROOT)}",
                        fg="green",
                    )

                # Convert cached canonical PEM to configured extra formats (once)
                extra_formats = [fmt for fmt in output_formats if fmt.lower() != "pem"]
                if extra_formats:
                    fmt_overrides_combined = dict(fmt_overrides)
                    if force:
                        fmt_overrides_combined["force"] = True
                    # Suppress print output in JSON mode
                    if json_output:
                        with suppress_output():
                            convert_to_formats(
                                cache_pem,
                                cache_dir,
                                extra_formats,
                                fmt_overrides_combined,
                                "bundlecraft-ca-trust",
                                dry_run=dry_run,
                            )
                    else:
                        convert_to_formats(
                            cache_pem,
                            cache_dir,
                            extra_formats,
                            fmt_overrides_combined,
                            "bundlecraft-ca-trust",
                            dry_run=dry_run,
                        )
                    if not json_output:
                        click.secho(
                            f"  [cache] ✓ Converted cached bundle to formats: {', '.join(extra_formats)}",
                            fg="green",
                        )

                bundle_cache_dirs[bname] = cache_dir
            except FileNotFoundError as e:
                # More specific error for missing source configs
                click.secho(
                    f"  [cache] ✗ Source config not found for '{bname}': {e}", fg="red", err=True
                )
                click.secho(
                    f"  [HINT] Create config/sources/{bname}.yaml with source configuration",
                    fg="yellow",
                    err=True,
                )
                sys.exit(ExitCode.CONFIG_ERROR)
            except Exception as e:
                click.secho(
                    f"  [cache] ✗ Failed to stage/cache bundle {bname}: {e}", fg="red", err=True
                )
                if verbose:
                    import traceback

                    traceback.print_exc()
                sys.exit(ExitCode.BUILD_ERROR)
    else:
        if not json_output:
            click.secho(
                "\n[STAGE 1/3] FETCH - Skipped (using existing staged sources)", fg="yellow"
            )
        for bname in unique_sources:
            cache_dir = bundle_cache_root / bname
            bundle_cache_dirs[bname] = cache_dir

    # Map targets to their bundle staging/cache dirs
    for bundle_name, include_sources in bundles_to_build:
        per_bundle = []
        for bname in include_sources:
            # Fallback to the new staging layout if cache dir is not present
            per_bundle.append(bundle_cache_dirs.get(bname, STAGED_DIR / bname))
        staging_map[bundle_name] = per_bundle

    # =========================================================================
    # STAGE 2: CONVERT
    # =========================================================================
    if not json_output:
        click.secho(
            "\n[STAGE 2/3] CONVERT - Aggregating and converting formats", fg="blue", bold=True
        )
    env_name_for_path = env_cfg.get("name") or env
    safe_env = str(env_name_for_path).replace("/", "-").replace(" ", "-")

    # Settings from env
    pem_cfg = env_cfg.get("pem") or {}
    include_subject_comments = pem_cfg.get("include_subject_comments", True)
    output_formats = env_cfg.get("output_formats") or ["pem"]
    fmt_overrides = env_cfg.get("format_overrides") or {}

    # Determine the build output directory with build_path override support
    # IMPORTANT: All builds must be rooted in dist/<env>/ for security
    # build_path can only specify a subdirectory within that root
    build_path_cfg = env_cfg.get("build_path")
    if build_path_cfg:
        # Normalize and validate the build_path (should already be validated by schema)
        build_path_clean = str(build_path_cfg).strip("/")

        # Final structure: dist/<env>/<build_path>/<bundle>
        # Note: safe_env is the environment name, build_path_clean is the custom subdirectory
        build_output_base = (ROOT / "dist" / safe_env / build_path_clean).resolve()

        # Double-check that resolved path is under dist/<env> (defense in depth)
        expected_root = (ROOT / "dist" / safe_env).resolve()
        if not str(build_output_base).startswith(str(expected_root)):
            error_msg = (
                f"build_path must remain under dist/{safe_env}/ directory (got: {build_path_cfg})"
            )
            if json_output:
                json_errors.append(error_msg)
                from bundlecraft.helpers.json_output import create_build_response, emit_json

                emit_json(
                    create_build_response(
                        success=False, environment=env, bundles=[], errors=json_errors
                    )
                )
            else:
                click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
            sys.exit(ExitCode.CONFIG_ERROR)

        # Manifest shows the full path relative to project root
        manifest_build_path = f"dist/{safe_env}/{build_path_clean}"
    else:
        # Default: dist/<env>/<bundle>
        build_output_base = (Path(output_root) / safe_env).resolve()
        # Effective default base for manifest field ignores --output-root and follows spec
        manifest_build_path = f"dist/{safe_env}"

    per_bundle_results: dict[str, dict] = {}
    import shutil

    # Process each bundle atomically
    for bundle_name, bundle_dirs in staging_map.items():
        final_build_root = (build_output_base / bundle_name).resolve()

        # Use atomic build context for each bundle
        with AtomicBuildContext(
            final_build_root, keep_temp=keep_temp, verbose=verbose, dry_run=dry_run
        ) as build_root:
            # Ensure build directory exists (atomic context handles this)
            if not dry_run:
                ensure_dir(build_root)

            # Single-bundle target: copy cached outputs directly
            if len(bundle_dirs) == 1:
                if dry_run:
                    # Use absolute path if outside ROOT, otherwise relative
                    try:
                        display_path = final_build_root.relative_to(ROOT)
                    except ValueError:
                        display_path = final_build_root
                    click.secho(
                        f"  [{bundle_name}] [dry-run] Would copy cached bundle to: {display_path}",
                        fg="yellow",
                    )
                    per_bundle_results[bundle_name] = {
                        "build_root": final_build_root,
                        "pem_blocks": ["# dry-run placeholder"],
                        "output_formats": output_formats,
                    }
                    continue

                bdir = bundle_dirs[0]
                cache_pem = bdir / "bundlecraft-ca-trust.pem"
                if cache_pem.exists():
                    for f in sorted([p for p in bdir.iterdir() if p.is_file()]):
                        dst = build_root / f.name
                        try:
                            shutil.copy2(f, dst)
                        except Exception:
                            dst.write_bytes(f.read_bytes())
                    # Use absolute path if outside ROOT, otherwise relative
                    try:
                        display_path = final_build_root.relative_to(ROOT)
                    except ValueError:
                        display_path = final_build_root
                    if not json_output:
                        click.secho(
                            f"  [{bundle_name}] ✓ Copied cached bundle '{bdir.name}' to {display_path}",
                            fg="green",
                        )
                pem_blocks = _read_pem_chunks([cache_pem])
                per_bundle_results[bundle_name] = {
                    "build_root": final_build_root,
                    "pem_blocks": pem_blocks,
                    "output_formats": output_formats,
                }

                # Write manifest and checksums for single-bundle target too
                if not dry_run:
                    # Check if packaging is enabled
                    package_enabled = env_cfg.get("package", True)

                    # Create deterministic tar package if enabled (before computing checksums)
                    if package_enabled:
                        tar_path = _create_deterministic_tar(build_root, "package")
                        if verbose:
                            click.echo(
                                f"  [{bundle_name}] ✓ Created deterministic package: {tar_path.name}",
                                err=True,
                            )

                    # Prepare manifest object
                    manifest_obj = {
                        "env": env_cfg.get("name") or env,
                        "environment": env,  # retained for compatibility
                        "bundle": bundle_name,
                        "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        "certificate_count": len(pem_blocks),
                        "output_formats": output_formats,
                        "build_path": manifest_build_path,
                    }

                    # Add verification summary if not skipped
                    if not skip_verify:
                        verify_cfg = env_cfg.get("verify") or {}
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

                    # Collect all output files except manifest.json and checksums.sha256
                    output_files = sorted(
                        [
                            f.name
                            for f in build_root.glob("*")
                            if f.is_file() and f.name not in ("manifest.json", "checksums.sha256")
                        ]
                    )

                    # Compute checksums once for all files (including tar if created)
                    manifest_obj["files"] = [
                        {"path": fname, "sha256": sha256_file(build_root / fname)}
                        for fname in output_files
                    ]

                    # Write manifest
                    manifest_path = build_root / "manifest.json"
                    manifest_path.write_text(
                        json.dumps(manifest_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    if verbose:
                        click.echo(
                            f"  [{bundle_name}] ✓ Wrote manifest: {manifest_path.name}",
                            err=True,
                        )

                    # Write checksums file with all files including manifest
                    all_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])
                    checksum_lines = [
                        f"{sha256_file(build_root / fname)}  {fname}" for fname in all_files
                    ]
                    checksum_path = build_root / "checksums.sha256"
                    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
                    if verbose:
                        click.echo(
                            f"  [{bundle_name}] ✓ Wrote checksums: {checksum_path.name}",
                            err=True,
                        )

                # Continue to next bundle (exit atomic context)
                continue

            # Multi-bundle target: merge cached canonical PEMs
            merged_blocks: list[str] = []
            for bdir in bundle_dirs:
                cache_pem = bdir / "bundlecraft-ca-trust.pem"
                if cache_pem.exists():
                    blocks_before = len(merged_blocks)
                    merged_blocks.extend(_read_pem_chunks([cache_pem]))
                    blocks_added = len(merged_blocks) - blocks_before
                    if verbose:
                        click.echo(
                            f"  [{bundle_name}] Loaded {blocks_added} cert(s) from cached: {cache_pem.relative_to(ROOT)}",
                            err=True,
                        )
                else:
                    if not bdir.exists():
                        click.secho(
                            f"  [ERROR] [{bundle_name}] Bundle directory does not exist: {bdir.relative_to(ROOT)}",
                            fg="red",
                            err=True,
                        )
                        click.secho(
                            f"  [HINT] Run without --skip-fetch or check that source '{bdir.name}' is configured correctly",
                            fg="yellow",
                            err=True,
                        )
                        sys.exit(ExitCode.BUILD_ERROR)
                    pem_files = _aggregate_staged_sources([bdir], verbose=verbose)
                    if not pem_files:
                        click.secho(
                            f"  [ERROR] [{bundle_name}] No .pem files found in: {bdir.relative_to(ROOT)}",
                            fg="red",
                            err=True,
                        )
                        sys.exit(ExitCode.BUILD_ERROR)
                    blocks_before = len(merged_blocks)
                    merged_blocks.extend(_read_pem_chunks(pem_files))
                    blocks_added = len(merged_blocks) - blocks_before
                    if verbose:
                        click.echo(
                            f"  [{bundle_name}] Loaded {blocks_added} cert(s) from {len(pem_files)} file(s) in: {bdir.relative_to(ROOT)}",
                            err=True,
                        )

            # Apply filters to merged blocks
            from bundlecraft.helpers.utils import apply_filters

            filters_cfg = env_cfg.get("filters") or {}
            blocks_before_filter = len(merged_blocks)
            merged_blocks = apply_filters(merged_blocks, filters_cfg)
            blocks_filtered = blocks_before_filter - len(merged_blocks)
            if blocks_filtered > 0 and verbose:
                click.echo(
                    f"  [{bundle_name}] Filtered out {blocks_filtered} certificate(s) per configuration",
                    err=True,
                )

            if not merged_blocks:
                click.secho(
                    f"  [ERROR] [{bundle_name}] No valid PEM certificates parsed for merged bundle.",
                    fg="red",
                    err=True,
                )
                if blocks_before_filter > 0:
                    click.secho(
                        f"  [HINT] All {blocks_before_filter} certificate(s) were filtered out. Check your filter configuration.",
                        fg="yellow",
                        err=True,
                    )
                else:
                    click.secho(
                        "  [HINT] No certificates were loaded from bundle directories. Check source configs and staging.",
                        fg="yellow",
                        err=True,
                    )
                sys.exit(ExitCode.INVALID_CERT)

            pem_out = build_root / "bundlecraft-ca-trust.pem"
            _write_canonical_pem(
                pem_out, merged_blocks, include_subject_comments, force=force, dry_run=dry_run
            )
            if not dry_run:
                # Use absolute path if outside ROOT, otherwise relative
                try:
                    display_path = final_build_root.relative_to(ROOT)
                except ValueError:
                    display_path = final_build_root
                if not json_output:
                    click.secho(
                        f"  [{bundle_name}] ✓ Wrote merged canonical PEM: {display_path}/bundlecraft-ca-trust.pem",
                        fg="green",
                    )

            extra_formats = [fmt for fmt in output_formats if fmt.lower() != "pem"]
            if extra_formats:
                fmt_overrides_combined = dict(fmt_overrides)
                if force:
                    fmt_overrides_combined["force"] = True
                # Suppress print output in JSON mode
                if json_output:
                    with suppress_output():
                        convert_to_formats(
                            pem_out,
                            build_root,
                            extra_formats,
                            fmt_overrides_combined,
                            "bundlecraft-ca-trust",
                            dry_run=dry_run,
                        )
                else:
                    convert_to_formats(
                        pem_out,
                        build_root,
                        extra_formats,
                        fmt_overrides_combined,
                        "bundlecraft-ca-trust",
                        dry_run=dry_run,
                    )
                if not dry_run and not json_output:
                    click.secho(
                        f"  [{bundle_name}] ✓ Converted merged bundle to formats: {', '.join(extra_formats)}",
                        fg="green",
                    )

            per_bundle_results[bundle_name] = {
                "build_root": final_build_root,
                "pem_blocks": merged_blocks,
                "output_formats": output_formats,
            }

            # =========================================================================
            # FINALIZE (inside atomic context): Manifest and checksums
            # =========================================================================
            if not dry_run:
                # Check if packaging is enabled
                package_enabled = env_cfg.get("package", True)

                # Create deterministic tar package if enabled (before computing checksums)
                if package_enabled:
                    tar_path = _create_deterministic_tar(build_root, "package")
                    if verbose:
                        click.echo(
                            f"  [{bundle_name}] ✓ Created deterministic package: {tar_path.name}",
                            err=True,
                        )

                # Prepare manifest object
                manifest_obj = {
                    "env": env_cfg.get("name") or env,
                    "environment": env,  # retained for compatibility
                    "bundle": bundle_name,
                    "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "certificate_count": len(merged_blocks),
                    "output_formats": output_formats,
                    "build_path": manifest_build_path,
                }

                # Add verification summary if not skipped
                if not skip_verify:
                    verify_cfg = env_cfg.get("verify") or {}
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

                # Collect all output files except manifest.json and checksums.sha256
                output_files = sorted(
                    [
                        f.name
                        for f in build_root.glob("*")
                        if f.is_file() and f.name not in ("manifest.json", "checksums.sha256")
                    ]
                )

                # Compute checksums once for all files (including tar if created)
                manifest_obj["files"] = [
                    {"path": fname, "sha256": sha256_file(build_root / fname)}
                    for fname in output_files
                ]

                # Write manifest
                manifest_path = build_root / "manifest.json"
                manifest_path.write_text(
                    json.dumps(manifest_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                if verbose:
                    click.echo(
                        f"  [{bundle_name}] ✓ Wrote manifest: {manifest_path.name}",
                        err=True,
                    )

                # Write checksums file with all files including manifest
                all_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])
                checksum_lines = [
                    f"{sha256_file(build_root / fname)}  {fname}" for fname in all_files
                ]
                checksum_path = build_root / "checksums.sha256"
                checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
                if verbose:
                    click.echo(
                        f"  [{bundle_name}] ✓ Wrote checksums: {checksum_path.name}",
                        err=True,
                    )

            # Atomic context commits temp → final on successful __exit__

    # =========================================================================
    # STAGE 3: VERIFY
    # =========================================================================
    verify_results = {}  # Track verification results per target for JSON output
    if not skip_verify:
        if not json_output:
            click.secho("\n[STAGE 3/3] VERIFY - Validating certificates", fg="blue", bold=True)
        verify_cfg = env_cfg.get("verify") or {}
        fail_on_expired = (
            verify_cfg.get("fail_on_expired", True) if isinstance(verify_cfg, dict) else True
        )
        warn_days = (
            verify_cfg.get("warn_days_before_expiry", 30) if isinstance(verify_cfg, dict) else 30
        )
        for bundle_name, result in per_bundle_results.items():
            pem_blocks = result["pem_blocks"]
            if dry_run:
                click.secho(
                    f"  [{bundle_name}] [dry-run] Would verify {len(pem_blocks)} certificate(s)",
                    fg="yellow",
                )
                click.secho(
                    f"  [{bundle_name}] [dry-run] Would check for expiry (fail_on_expired={fail_on_expired}, warn_days={warn_days})",
                    fg="yellow",
                )
                continue
            errs, warns = _verify_certificates(pem_blocks, fail_on_expired, warn_days)
            verify_results[bundle_name] = {
                "passed": len(errs) == 0,
                "errors": errs,
                "warnings": warns,
            }
            if not json_output:
                for e in errs:
                    click.secho(f"  [{bundle_name}] [ERROR] {e}", fg="red")
                for w in warns:
                    click.secho(f"  [{bundle_name}] [WARN] {w}", fg="yellow")
            if errs:
                if not json_output:
                    click.secho(
                        f"  [{bundle_name}] [SUMMARY] {len(errs)} expired/invalid certificate(s)",
                        fg="red",
                    )
                if fail_on_expired:
                    if not json_output:
                        click.secho(
                            "  Build FAILED due to expired certificates", fg="red", err=True
                        )
                    else:
                        # For JSON mode, we'll output at the end with success=False
                        pass
                    # Don't exit yet in JSON mode, let it collect all errors
                    if not json_output:
                        sys.exit(ExitCode.EXPIRED_CERT)
            if not json_output:
                if warns:
                    click.secho(
                        f"  [{bundle_name}] [SUMMARY] {len(warns)} certificate(s) expiring within {warn_days} days",
                        fg="yellow",
                    )
                if not errs and not warns:
                    click.secho(
                        f"  [{bundle_name}] ✓ All certificates are valid and healthy", fg="green"
                    )
    else:
        if not json_output:
            click.secho("\n[STAGE 3/3] VERIFY - Skipped", fg="yellow")

    # =========================================================================
    # Build complete - Note: manifest/checksums/SBOM written in OUTPUT RESULTS section below
    # =========================================================================
    if not dry_run:
        # Package creation (if enabled) happens here, manifest/checksums deferred to OUTPUT RESULTS
        for bundle_name, result in per_bundle_results.items():
            build_root = result["build_root"]
            pem_blocks = result["pem_blocks"]
            output_formats = result["output_formats"]

            # Create deterministic tar package if enabled (before computing checksums)
            if package_enabled:
                existing_tar = build_root / "package.tar.gz"
                if not existing_tar.exists():
                    tar_path = _create_deterministic_tar(build_root, "package")
                    # Use absolute path if outside ROOT, otherwise relative
                    try:
                        display_path = tar_path.relative_to(ROOT)
                    except ValueError:
                        display_path = tar_path
                    if not json_output:
                        click.secho(
                            f"  [{bundle_name}] ✓ Created deterministic package: {display_path}",
                            fg="green",
                        )

            # Prepare manifest object
            timestamp_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            manifest_obj = {
                "env": env_cfg.get("name") or env,
                "environment": env,  # retained for compatibility
                "bundle": bundle_name,
                "timestamp_utc": timestamp_utc,
                "certificate_count": len(pem_blocks),
                "output_formats": output_formats,
                "build_path": manifest_build_path,
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

            # Collect all output files except manifest.json and checksums.sha256
            output_files = sorted(
                [
                    f.name
                    for f in build_root.glob("*")
                    if f.is_file() and f.name not in ("manifest.json", "checksums.sha256")
                ]
            )

            # Note: Manifest and checksums are written in OUTPUT RESULTS section below
            # to ensure all artifacts (including SBOM) are included

    # =========================================================================
    # OUTPUT RESULTS - Write manifest, checksums, SBOM, and optionally sign
    # =========================================================================
    if not dry_run:
        if not json_output:
            click.secho("\nFinalizing build artifacts...", fg="blue")

        # Check if packaging is enabled
        package_enabled = env_cfg.get("package", True)

        # Build manifest and checksums per target
        for bundle_name, result in per_bundle_results.items():
            build_root = result["build_root"]
            pem_blocks = result["pem_blocks"]
            output_formats = result["output_formats"]

            # Create deterministic tar package if enabled (before computing checksums)
            if package_enabled:
                existing_tar = build_root / "package.tar.gz"
                if not existing_tar.exists():
                    tar_path = _create_deterministic_tar(build_root, "package")
                    # Use absolute path if outside ROOT, otherwise relative
                    try:
                        display_path = tar_path.relative_to(ROOT)
                    except ValueError:
                        display_path = tar_path
                    if not json_output:
                        click.secho(
                            f"  [{bundle_name}] ✓ Created deterministic package: {display_path}",
                            fg="green",
                        )

            # Prepare manifest object
            manifest_obj = {
                "env": env_cfg.get("name") or env,
                "environment": env,  # retained for compatibility
                "bundle": bundle_name,
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "certificate_count": len(pem_blocks),
                "output_formats": output_formats,
                "build_path": manifest_build_path,
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

            # Collect all output files except manifest.json and checksums.sha256
            output_files = sorted(
                [
                    f.name
                    for f in build_root.glob("*")
                    if f.is_file() and f.name not in ("manifest.json", "checksums.sha256")
                ]
            )

            # Compute checksums once for all files (including tar if created)
            manifest_obj["files"] = [
                {"path": fname, "sha256": sha256_file(build_root / fname)} for fname in output_files
            ]

            # Add expanded output metadata if configured
            output_metadata_cfg = env_cfg.get("output_metadata")
            if output_metadata_cfg:
                expanded_metadata = expand_output_metadata(
                    output_metadata_cfg,
                    bundle=bundle_name,
                    env=env,
                    timestamp_utc=manifest_obj["timestamp_utc"],
                )
                if expanded_metadata:
                    manifest_obj["output_metadata"] = expanded_metadata
                    # Also write a YAML sidecar for easy consumption in tools like ConfigMap generation
                    sidecar_path = build_root / "metadata.yaml"
                    sidecar_path.write_text(
                        yaml.dump(expanded_metadata, default_flow_style=False, sort_keys=True),
                        encoding="utf-8",
                    )
                    if not json_output:
                        try:
                            display_path = sidecar_path.relative_to(ROOT)
                        except ValueError:
                            display_path = sidecar_path
                        click.secho(
                            f"  [{bundle_name}] ✓ Wrote metadata sidecar: {display_path}",
                            fg="green",
                        )

            # Write manifest
            manifest_path = build_root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            # Use absolute path if outside ROOT, otherwise relative
            try:
                display_path = manifest_path.relative_to(ROOT)
            except ValueError:
                display_path = manifest_path
            if not json_output:
                click.secho(f"  [{bundle_name}] ✓ Wrote manifest: {display_path}", fg="green")

            # Write checksums file with all files including manifest
            all_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])
            checksum_lines = [f"{sha256_file(build_root / fname)}  {fname}" for fname in all_files]
            checksum_path = build_root / "checksums.sha256"
            checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
            # Use absolute path if outside ROOT, otherwise relative
            try:
                display_path = checksum_path.relative_to(ROOT)
            except ValueError:
                display_path = checksum_path
            if not json_output:
                click.secho(
                    f"  [{bundle_name}] ✓ Wrote checksums: {display_path}",
                    fg="green",
                )

            # Generate SBOM if enabled
            if generate_sbom:
                try:
                    from bundlecraft.helpers.sbom import generate_cyclonedx_sbom

                    sbom_path = generate_cyclonedx_sbom(build_root, manifest_obj, pem_blocks)
                    # Use absolute path if outside ROOT, otherwise relative
                    try:
                        display_path = sbom_path.relative_to(ROOT)
                    except ValueError:
                        display_path = sbom_path
                    if not json_output:
                        click.secho(
                            f"  [{bundle_name}] ✓ Generated SBOM: {display_path}",
                            fg="green",
                        )
                except Exception as e:
                    if not json_output:
                        click.secho(
                            f"  [{bundle_name}] [WARN] SBOM generation failed: {e}",
                            fg="yellow",
                        )

            # Sign artifacts if requested
            if sign:
                from bundlecraft.helpers.signing import sign_file

                # Determine which files to sign (all artifacts except signatures)
                files_to_sign = [
                    build_root / "manifest.json",
                    build_root / "checksums.sha256",
                ]
                # Add main bundle files
                for fmt in output_formats:
                    artifact_path = build_root / f"bundlecraft-ca-trust.{fmt}"
                    if artifact_path.exists():
                        files_to_sign.append(artifact_path)

                # Add package.tar.gz if it exists
                package_tar = build_root / "package.tar.gz"
                if package_tar.exists():
                    files_to_sign.append(package_tar)

                # Add SBOM if it was generated
                sbom_file = build_root / "sbom.json"
                if sbom_file.exists():
                    files_to_sign.append(sbom_file)

                # Sign each file
                signed_count = 0
                for file_to_sign in files_to_sign:
                    try:
                        sig_path = sign_file(
                            file_to_sign,
                            key_id=gpg_key_id,
                            passphrase=None,  # Will use GPG_PASSPHRASE env var if set
                        )
                        # Use absolute path if outside ROOT, otherwise relative
                        try:
                            display_path = sig_path.relative_to(ROOT)
                        except ValueError:
                            display_path = sig_path
                        if not json_output:
                            click.secho(
                                f"  [{bundle_name}] ✓ Signed: {display_path}",
                                fg="green",
                            )
                        signed_count += 1
                    except Exception as e:
                        if not json_output:
                            click.secho(
                                f"  [{bundle_name}] [ERROR] Failed to sign {file_to_sign.name}: {e}",
                                fg="red",
                                err=True,
                            )
                        sys.exit(ExitCode.BUILD_ERROR)

                if not json_output:
                    click.secho(
                        f"  [{bundle_name}] ✓ Signed {signed_count} artifact(s)",
                        fg="green",
                    )

    # First completion message (removed duplicate below)
    # Build bundle display names with environment context
    env_display_name = env_cfg.get("name") or env
    bundle_display_names = [f"{env_display_name}/{bundle}" for bundle in per_bundle_results.keys()]

    if dry_run:
        if not json_output:
            click.secho(
                "\n✅ [DRY RUN] Build simulation complete for bundle(s): "
                + ", ".join(bundle_display_names),
                fg="yellow",
                bold=True,
            )
    else:
        if not json_output:
            click.secho(
                "\n✅ Build complete for bundle(s): " + ", ".join(bundle_display_names),
                fg="bright_green",
                bold=True,
            )

    # Collect bundle information for JSON output
    for bundle_name, result in per_bundle_results.items():
        build_root = result["build_root"]
        pem_blocks = result["pem_blocks"]
        output_formats = result["output_formats"]

        # Get bundles for this target
        target_bundles = []
        for tname, include_sources in bundles_to_build:
            if tname == bundle_name:
                target_bundles = include_sources
                break

        target_info = {
            "name": bundle_name,
            "certificate_count": len(pem_blocks),
            "output_formats": output_formats,
            "output_path": str(build_root.relative_to(ROOT)) if not dry_run else str(build_root),
            "bundles": target_bundles,
        }

        # Add verification results if available
        if bundle_name in verify_results:
            target_info["verification"] = verify_results[bundle_name]

        json_targets.append(target_info)

    # Check if any verification errors occurred
    verification_failed = False
    if not skip_verify:
        verify_cfg = env_cfg.get("verify") or {}
        fail_on_expired = (
            verify_cfg.get("fail_on_expired", True) if isinstance(verify_cfg, dict) else True
        )
        for bundle_name in verify_results:
            if verify_results[bundle_name]["errors"] and fail_on_expired:
                verification_failed = True
                break

    # Output results
    if json_output:
        from bundlecraft.helpers.json_output import create_build_response, emit_json

        emit_json(
            create_build_response(
                success=not verification_failed and not json_errors,
                environment=env_cfg.get("name") or env,
                bundles=json_targets,
                errors=json_errors if json_errors else None,
                dry_run=dry_run,
            )
        )

        if verification_failed:
            sys.exit(ExitCode.VALIDATION_ERROR)
    else:
        # Non-JSON mode: show final confirmation (duplicate message removed from above)
        if not dry_run:
            click.secho(
                "All bundles committed atomically to final locations.",
                fg="green",
            )

            # Friendly final summary with bundle locations for manual users
            # Display paths relative to the current workspace root when possible
            try:
                from pathlib import Path as _Path

                _cwd = _Path.cwd()
            except Exception:
                _cwd = ROOT

            click.echo("")
            click.secho("Build successful, bundles built at the following locations:", fg="cyan")
            for _bundle_name, _result in per_bundle_results.items():
                _build_root = _result["build_root"]
                _label = f"{env_display_name}/{_bundle_name}"
                try:
                    _rel = _build_root.relative_to(_cwd)
                    _path_str = f"./{str(_rel).rstrip('/')}"  # prefix with ./ for clarity
                except Exception:
                    _path_str = str(_build_root)
                # Ensure trailing slash for directory display
                if not _path_str.endswith("/"):
                    _path_str += "/"
                click.secho(f" - [{_label}] {_path_str}")


if __name__ == "__main__":
    main()
