#!/usr/bin/env python3
"""
builder.py
Central build engine that produces ready-to-distribute trust bundles.

Enhancements:
- PEM files now include # Subject comments above each cert block (configurable)
- Build fails by default if any expired cert is found (configurable)
- Expiration warnings for certs expiring within 30 days
- Uses timezone-aware datetime (UTC safe)
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import tarfile
from pathlib import Path

import click

from bundlecraft.fetch import run_fetch
from bundlecraft.helpers.convert_utils import convert_to_formats
from bundlecraft.helpers.utils import ensure_dir, list_files, load_yaml, sha256_file
from bundlecraft.helpers.verify_utils import verifier

# ---------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
HELPERS_DIR = CURRENT_DIR / "helpers"
sys.path.insert(0, str(HELPERS_DIR))

# ---------------------------------------------------------------------
# Helper imports
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------
ROOT = CURRENT_DIR.parent
CONFIG_DIR = ROOT / "config"
SOURCES_DIR = ROOT / "sources"
BUILD_DIR = ROOT / "dist"

# -------------------------------
# Helper functions
# -------------------------------


def read_pem_chunks(paths):
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


def dedupe_ordered(pem_blocks):
    """Deduplicate PEM blocks by SHA256 fingerprint."""
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


def write_canonical_pem(dst: Path, pem_blocks, include_subject_comments: bool):
    """Write PEM with optional '# Subject:' lines."""
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


def build_checksums(build_path: Path) -> Path:
    lines = []
    for f in sorted(build_path.glob("*")):
        if f.is_file():
            lines.append(f"{sha256_file(f)}  {f.name}")
    out = build_path / "checksums.sha256"
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out


def package_tar(build_path: Path) -> Path:
    out = build_path / "package.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        for f in sorted(build_path.glob("*")):
            if f.is_file() and f.name != out.name:
                tar.add(f, arcname=f.name)
    return out


# -------------------------------
# Core Build Function
# -------------------------------


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--env",
    "--craft",
    "env",
    required=True,
    help="Craft name (e.g., dev, prod, dmz)",
)
@click.option("--bundle", required=True, help="Bundle name (e.g., internal, external)")
@click.option("--package", is_flag=True, help="Also create a .tar.gz of the build folder")
@click.option("--verify-only", is_flag=True, help="Only verify certificates; skip build")
@click.option(
    "--prefetch/--no-prefetch",
    default=False,
    help="Run 'fetch' first to stage remote sources for this env/bundle (default: no-prefetch)",
)
@click.option(
    "--offline",
    is_flag=True,
    default=False,
    help="Offline mode: do not contact network; fail if fetch is required",
)
@click.option(
    "--output-root",
    type=str,
    default="dist",
    help="Root directory for build outputs (default: ./dist)",
)
def main(env, bundle, package, verify_only, prefetch, offline, output_root):
    """Build or verify trust bundles based on configuration."""
    click.secho(
        "\n🔐 BundleCraft CA Trust Store Builder\n--------------------------------------",
        fg="cyan",
    )

    # defaults is currently unused, to be refactored when the config structure is revalidated
    # defaults = load_yaml(CONFIG_DIR / "defaults.yaml", required=False) or {}
    # Prefer crafts configs, fall back to legacy envs for backward compatibility
    craft_path = CONFIG_DIR / "crafts" / f"{env}.yaml"
    legacy_env_path = CONFIG_DIR / "envs" / f"{env}.yaml"
    cfg_path = craft_path if craft_path.exists() else legacy_env_path
    env_cfg = load_yaml(cfg_path, required=True)

    # Environment-driven composition support: env can define targets mapping
    # a target bundle name to one or more base bundle configs to include/merge.
    # Schema examples:
    #   targets:
    #     internal-dev:
    #       includes: [internal, mozilla]
    #     mozilla:
    #       includes: [mozilla]
    # Back-compat: some envs may define bundle_targets as a list (no composition).
    targets = env_cfg.get("targets") or {}
    comp_includes = None
    if isinstance(targets, dict) and bundle in targets:
        entry = targets[bundle] or {}
        comp_includes = entry.get("includes") or entry.get("compose") or []

    # Load bundle config; if this bundle is only an env-level composition target,
    # allow the bundle file to be missing and use an empty dict.
    bundle_cfg = None
    bundle_cfg_path = CONFIG_DIR / "bundles" / f"{bundle}.yaml"
    if bundle_cfg_path.exists():
        bundle_cfg = load_yaml(bundle_cfg_path, required=True)
    elif comp_includes:
        bundle_cfg = {}  # Use empty config for composed targets
    else:
        click.secho(f"[ERROR] Bundle config not found: {bundle_cfg_path}", fg="red")
        sys.exit(2)

    # Optional prefetch step (stages into sources/fetched/<env>/<bundle>)
    if offline and prefetch:
        click.secho("[ERROR] --offline and --prefetch cannot be used together.", fg="red")
        sys.exit(2)

    if prefetch:
        try:
            # If composed, prefetch each included base bundle; otherwise prefetch this bundle
            base_bundles = comp_includes if comp_includes else [bundle]
            total_staged = 0
            for bname in base_bundles:
                # For now, use legacy run_fetch to stage into sources/fetched/<env>/<bundle>
                # Future: replace with a thin wrapper that calls the new fetch CLI for more control
                staged = run_fetch(env, bname, ROOT, no_clean=False)
                total_staged += len(staged)
            if total_staged:
                click.secho(f"[INFO] Prefetch staged {total_staged} file(s).", fg="blue")
            else:
                click.secho("[INFO] No fetch entries; skipping prefetch.", fg="blue")
        except Exception as e:
            click.secho(f"[ERROR] Prefetch failed: {e}", fg="red")
            sys.exit(2)

    # Prefer env-level verify config, fall back to bundle-level (build-time verification policy)
    verify_cfg = env_cfg.get("verify") or bundle_cfg.get("verify", True)
    fail_on_expired = (
        verify_cfg.get("fail_on_expired", True) if isinstance(verify_cfg, dict) else True
    )
    warn_days = (
        verify_cfg.get("warn_days_before_expiry", 30) if isinstance(verify_cfg, dict) else 30
    )

    # Prefer env-level pem config, fall back to bundle-level
    pem_cfg = env_cfg.get("pem") or bundle_cfg.get("pem", {})
    include_subject_comments = pem_cfg.get("include_subject_comments", True)

    # Prefer env-level output_formats, fall back to bundle-level, then default to ["pem"]
    output_formats = env_cfg.get("output_formats") or bundle_cfg.get("output_formats", ["pem"])
    do_package = bool(package or bundle_cfg.get("package", False))

    BUILD_DIR = Path(output_root)
    build_root = BUILD_DIR / env / bundle
    ensure_dir(build_root)

    # Build include/exclude lists, possibly across composed base bundles.
    # This is effectively the orchestration between previously-staged sources (from fetch)
    # and local includes defined in bundle configs.
    include_items = []
    exclude_items = set()

    def _rel(p: Path) -> str:
        return str(p.relative_to(ROOT)).replace("\\", "/")

    base_bundles = comp_includes if comp_includes else [bundle]
    base_bundle_cfgs = {}
    for bname in base_bundles:
        # Include staged fetched sources for each base bundle if present
        b_staged_dir = SOURCES_DIR / "fetched" / env / bname
        if b_staged_dir.exists():
            include_items.append(_rel(b_staged_dir))
        # Load base bundle config for source includes/excludes
        b_cfg = load_yaml(CONFIG_DIR / "bundles" / f"{bname}.yaml", required=True)
        base_bundle_cfgs[bname] = b_cfg
        include_items.extend(b_cfg.get("include", []) or [])
        for ex in b_cfg.get("exclude", []) or []:
            exclude_items.add(ex)

    # Also allow the target bundle file to contribute extra include/exclude if it exists
    if bundle_cfg:
        include_items.extend(bundle_cfg.get("include", []) or [])
        for ex in bundle_cfg.get("exclude", []) or []:
            exclude_items.add(ex)
    include_paths = []
    for item in include_items:
        p = (ROOT / item).resolve()
        if p.is_dir():
            include_paths.extend(list_files(p, suffixes=(".pem",)))
        elif p.is_file():
            include_paths.append(p)
        else:
            click.secho(f"[WARN] Include path not found: {item}", fg="yellow")
    include_paths = [
        p for p in include_paths if str(p.relative_to(ROOT)).replace("\\", "/") not in exclude_items
    ]

    if not include_paths:
        click.secho("[ERROR] No certificate sources found.", fg="red", err=True)
        sys.exit(2)

    pem_blocks = dedupe_ordered(read_pem_chunks(include_paths))
    if not pem_blocks:
        click.secho("[ERROR] No valid PEM certificates parsed.", fg="red", err=True)
        sys.exit(3)

    # -----------------------
    # Verify-only mode
    # -----------------------
    if verify_only:
        pem_path = build_root / "bundlecraft-ca-trust.pem"
        if pem_path.exists():
            click.secho(f"[INFO] Verifying existing PEM bundle: {pem_path}", fg="blue")
            code = verifier(pem_path, warn_days, fail_on_expired)
        else:
            click.secho("[INFO] No built bundle found; verifying sources directly.", fg="blue")
            import tempfile

            tmp_pem = Path(tempfile.gettempdir()) / "verify-temp.pem"
            tmp_pem.write_text("".join(pem_blocks), encoding="utf-8")
            code = verifier(tmp_pem, warn_days, fail_on_expired)
            tmp_pem.unlink(missing_ok=True)
        sys.exit(code)

    # -----------------------
    # Verification integrated (build-time)
    # -----------------------
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

    for e in errs:
        click.secho(f"[ERROR] {e}", fg="red")
    for w in warns:
        click.secho(f"[WARN] {w}", fg="yellow")

    if errs:
        click.secho(f"[SUMMARY] {len(errs)} expired or invalid certificates detected.", fg="red")
        if fail_on_expired:
            click.secho("[ERROR] Build aborted due to expired certificates.", fg="red")
            sys.exit(5)
    if warns:
        click.secho(
            f"[SUMMARY] {len(warns)} certificates expiring within {warn_days} days.",
            fg="yellow",
        )
    if not errs and not warns:
        click.secho("[INFO] All certificates are valid and healthy.", fg="green")

    # -----------------------
    # Write canonical PEM
    # -----------------------
    pem_out = build_root / "bundlecraft-ca-trust.pem"
    write_canonical_pem(pem_out, pem_blocks, include_subject_comments)
    click.secho(f"[INFO] Wrote canonical PEM: {pem_out}", fg="green")

    # -----------------------
    # Convert formats
    # -----------------------
    extra_formats = [fmt for fmt in output_formats if fmt.lower() != "pem"]
    fmt_overrides = env_cfg.get("format_overrides") or {}
    convert_to_formats(pem_out, build_root, extra_formats, fmt_overrides)

    # --- OPTIONAL PACKAGING (must happen before manifest) ---
    if package:
        import tarfile

        archive_path = build_root / "package.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(build_root, arcname=".")
        click.secho(f"[INFO] Packaged archive: {archive_path}", fg="green")

    # -----------------------
    # Final deterministic manifest + checksums
    # -----------------------
    from datetime import datetime

    expiry_summary = {
        "total": len(pem_blocks),
        "expired": len(errs),
        "expiring_soon": len(warns),
        "valid": len(pem_blocks) - len(errs) - len(warns),
        "warn_days_before_expiry": warn_days,
    }

    manifest_path = build_root / "manifest.json"
    checksum_path = build_root / "checksums.sha256"

    # Collect all files that currently exist in the build dir
    all_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])

    # Files recorded inside manifest["files"]:
    #   - include everything EXCEPT manifest.json
    files_for_manifest = [n for n in all_files if n != "manifest.json"]

    # Build manifest["files"] entries (manifest.json excluded)
    file_entries = [{"path": n, "sha256": sha256_file(build_root / n)} for n in files_for_manifest]

    # Load fetch provenance if present
    fetch_provenance = None
    # Embed fetch provenance for each base bundle (if any)
    fetched_prov_map = {}
    for bname in base_bundles:
        b_staged_dir = SOURCES_DIR / "fetched" / env / bname
        prov_path = b_staged_dir / "provenance.fetch.json"
        if prov_path.exists():
            try:
                fetched_prov_map[bname] = json.loads(prov_path.read_text(encoding="utf-8"))
            except Exception:
                fetched_prov_map[bname] = {"error": "unreadable"}
    fetch_provenance = {"bundles": fetched_prov_map} if fetched_prov_map else None

    manifest_obj = {
        "bundle": bundle,
        "environment": env,
        "timestamp_utc": datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": [str(p.relative_to(ROOT)).replace("\\", "/") for p in include_paths],
        "outputs": files_for_manifest,  # includes package.tar.gz if present
        "verify": {"fail_on_expired": fail_on_expired},
        "expiry_summary": expiry_summary,
        "fetched": fetch_provenance,
        "files": file_entries,
    }

    # Write manifest exactly once (deterministic order)
    manifest_json = json.dumps(manifest_obj, indent=2, sort_keys=True)
    manifest_path.write_text(manifest_json + "\n", encoding="utf-8")
    click.secho(f"[INFO] Wrote manifest: {manifest_path}", fg="green")

    # checksums.sha256 includes EVERY file, INCLUDING manifest.json
    checksum_lines = [f"{sha256_file(build_root / n)}  {n}" for n in all_files]
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    click.secho(f"[INFO] Wrote checksums: {checksum_path}", fg="green")

    click.secho("[SUCCESS] Build completed successfully.", fg="green")

    # Compute fresh checksums including manifest.json itself
    all_files = sorted([f.name for f in build_root.glob("*") if f.is_file()])
    checksum_lines = [f"{sha256_file(build_root / f)}  {f}" for f in all_files]
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    click.secho(f"[INFO] Wrote checksums: {checksum_path}", fg="green")

    # -----------------------
    # Embed hash data into manifest (for verifier)
    # -----------------------
    file_entries = []
    for f in sorted(build_root.glob("*")):
        if f.is_file():
            file_entries.append({"path": f.name, "sha256": sha256_file(f)})

    # Reload manifest JSON, inject "files" array
    mdata = json.loads(manifest_path.read_text(encoding="utf-8"))
    mdata["files"] = file_entries
    manifest_path.write_text(json.dumps(mdata, indent=2), encoding="utf-8")
    click.secho("[INFO] Updated manifest with file hashes.", fg="green")

    # -----------------------
    # Package (optional)
    # -----------------------
    if do_package:
        pkg = package_tar(build_root)
        click.secho(f"[INFO] Wrote package archive: {pkg}", fg="green")

    click.secho("\n✅ Build complete.", fg="bright_green")


if __name__ == "__main__":
    main()
