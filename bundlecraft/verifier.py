#!/usr/bin/env python3
"""
verifier.py
----------------
Verifies integrity and consistency of PKI trust bundle artifacts.

Features:
- Default: verifies all bundle files (skips manifest.json & package.tar.gz)
- --verify-manifest: show manifest details only (no verification)
- --verify-all: verify bundle files + show manifest in one run
- --verbose: detailed metadata and hash info
- Cert-count consistency check (PEM, P12, P7B, JKS)
- Emoji-rich human output, but pure UTF-8 safe
"""

import hashlib
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click
from cryptography.hazmat.primitives.serialization import pkcs7, pkcs12

# --- logging setup ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHECKSUM_FILE = "checksums.sha256"
MANIFEST_FILE = "manifest.json"
IGNORE_FILES = {"package.tar.gz", MANIFEST_FILE}


def sha256sum(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def file_info(file: Path) -> str:
    size_kb = file.stat().st_size / 1024
    mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
    return f"{size_kb:.1f} KB, modified {mtime.strftime('%Y-%m-%d %H:%M:%S UTC')}"


def load_checksums(path: Path) -> dict:
    checksums = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hash_val, filename = line.split("  ", 1)
            checksums[filename.strip()] = hash_val.strip()
    return checksums


def count_certs_in_pem(file: Path) -> int:
    text = file.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"-----BEGIN CERTIFICATE-----", text))


def count_certs_in_store(file: Path) -> int | None:
    ext = file.suffix.lower()
    try:
        if ext == ".pem":
            return count_certs_in_pem(file)
        elif ext in (".p12", ".pfx"):
            data = file.read_bytes()
            count = 0
            tried_pw = [b"changeit", None]
            for pw in tried_pw:
                try:
                    pkey, cert, addl = pkcs12.load_key_and_certificates(data, password=pw)
                    if cert or addl:
                        if cert:
                            count += 1
                        if addl:
                            count += len(addl)
                        break
                except Exception:
                    continue
            if count == 0:
                for pw in tried_pw:
                    try:
                        pkcs12_obj = pkcs12.load_pkcs12(data, pw)
                        certs = []
                        if hasattr(pkcs12_obj, "certificates"):
                            certs = pkcs12_obj.certificates or []
                        elif hasattr(pkcs12_obj, "get_certificates"):
                            certs = pkcs12_obj.get_certificates() or []
                        if certs:
                            count += len(certs)
                            break
                    except Exception:
                        continue
            if count == 0:
                logger.warning(f"⚠️  Could not read any certificates from {file.name}")
                return None
            return count
        elif ext == ".p7b":
            data = file.read_bytes()
            try:
                certs = pkcs7.load_pem_pkcs7_certificates(data)
            except ValueError:
                certs = pkcs7.load_der_pkcs7_certificates(data)
            return len(certs)
        elif ext == ".jks":
            result = subprocess.run(
                [
                    "keytool",
                    "-list",
                    "-rfc",
                    "-keystore",
                    str(file),
                    "-storepass",
                    "changeit",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=8,
            )
            pem_blocks = re.findall(r"-----BEGIN CERTIFICATE-----", result.stdout)
            if not pem_blocks:
                result2 = subprocess.run(
                    ["keytool", "-list", "-rfc", "-keystore", str(file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=8,
                )
                pem_blocks = re.findall(r"-----BEGIN CERTIFICATE-----", result2.stdout)
            return len(pem_blocks)
    except Exception as e:
        logger.debug(f"Error counting certs in {file.name}: {e}")
    return None


def show_manifest_info(build_dir: Path, verbose: bool = False) -> None:
    manifest_path = build_dir / MANIFEST_FILE
    if not manifest_path.exists():
        logger.error(f"Missing {MANIFEST_FILE} in {build_dir}")
        return
    logger.info("📝 Manifest inspection (no verification performed)")
    logger.info(f"    Path: {manifest_path.resolve()}")
    logger.info(f"    Info: {file_info(manifest_path)}")
    sha = sha256sum(manifest_path)
    logger.info(f"    SHA256: {sha}")
    if verbose:
        content_preview = manifest_path.read_text(encoding="utf-8", errors="ignore").splitlines()[
            :10
        ]
        if len(content_preview) > 0:
            logger.info("    Content preview:")
            for line in content_preview:
                logger.info(f"      {line}")
    logger.info("✅ Manifest inspection complete.")


def verify_directory(build_dir: Path, verbose: bool = False, check_counts: bool = True) -> bool:
    checksum_path = build_dir / CHECKSUM_FILE
    if not checksum_path.exists():
        logger.error(f"Missing {CHECKSUM_FILE} in {build_dir}")
        return False
    checksums = load_checksums(checksum_path)
    logger.info(f"🔍 Starting verification for directory: {build_dir}")
    logger.info(f"📄 Using checksum manifest: {checksum_path.resolve()}")

    success = True
    cert_counts = {}
    verified_files = 0
    skipped_files = 0

    for file in sorted(build_dir.iterdir()):
        if file.is_dir():
            continue
        if file.name in IGNORE_FILES:
            reason = (
                "manifest is signed separately"
                if file.name == MANIFEST_FILE
                else "non-deterministic artifact"
            )
            logger.info(f"⏭️  Skipping {file.name} ({reason})")
            skipped_files += 1
            continue
        if file.name == CHECKSUM_FILE:
            continue

        expected = checksums.get(file.name)
        if not expected:
            logger.warning(f"⚠️  No checksum entry for {file.name}")
            continue

        actual = sha256sum(file)
        if actual != expected:
            logger.error(f"❌ {file.name}: hash mismatch!")
            if verbose:
                logger.error(f"    Expected: {expected}")
                logger.error(f"    Actual:   {actual}")
                logger.error(f"    Info: {file_info(file)}")
            success = False
        else:
            verified_files += 1
            logger.info(f"✅ {file.name} verified successfully.")
            if verbose:
                logger.info(f"    SHA256: {actual}")
                logger.info(f"    Info: {file_info(file)}")

        if check_counts:
            count = count_certs_in_store(file)
            if count is not None:
                cert_counts[file.name] = count
                if verbose:
                    logger.info(f"    Certificate count: {count}")
            else:
                logger.info("    (hash OK, certificate content not readable)")

    total_certs = sum(cert_counts.values()) if cert_counts else 0
    unique_counts = set(cert_counts.values())
    mismatch = False
    if check_counts and cert_counts:
        if len(unique_counts) > 1:
            logger.warning(f"⚠️  Certificate count mismatch detected: {cert_counts}")
            mismatch = True
        elif all(v == 0 for v in unique_counts):
            logger.warning("⚠️  All bundle files appear empty (0 certs).")

    logger.info("🔚 Verification run complete.")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"📦 Verified files: {verified_files}")
    logger.info(f"⏭️  Skipped files:  {skipped_files}")
    logger.info(f"🧾 Certificates counted: {total_certs}")
    if check_counts and cert_counts:
        logger.info(f"🔍 Files with cert counts: {len(cert_counts)}")
        if mismatch:
            logger.info("⚠️  Certificate count mismatch detected.")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return success


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--target",
    required=True,
    type=click.Path(exists=True),
    help="Path to build directory or file",
)
@click.option(
    "--verify-manifest",
    is_flag=True,
    help="Display manifest info only (no verification)",
)
@click.option("--verify-all", is_flag=True, help="Verify both bundle files and manifest together")
@click.option("--verbose", is_flag=True, help="Show detailed file metadata and hashes")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be verified without actually reading files",
)
def main(target, verify_manifest, verify_all, verbose, dry_run):
    """Verify the integrity and consistency of built trust bundles.

    Use --dry-run to preview what would be verified without making any changes.
    """
    click.secho("\n🔐 BundleCraft Verifier\n----------------------", fg="cyan")

    if dry_run:
        click.secho("[DRY RUN MODE] No files will be read or verified\n", fg="yellow", bold=True)

    path = Path(target)
    if path.is_file():
        if dry_run:
            click.echo(f"[dry-run] Would verify single file: {path.name}")
            click.echo("[dry-run] Would compute SHA256 hash")
            if verbose:
                click.echo("[dry-run] Would display file info")
            return
        logger.info(f"Verifying single file: {path.name}")
        digest = sha256sum(path)
        logger.info(f"SHA256: {digest}")
        if verbose:
            logger.info(f"Info: {file_info(path)}")
        return

    ok = True
    if dry_run:
        if verify_manifest:
            click.echo("[dry-run] Would display manifest info from: " + str(path))
        elif verify_all:
            click.echo("[dry-run] Would verify directory: " + str(path))
            click.echo("[dry-run] Would display manifest info from: " + str(path))
        else:
            click.echo("[dry-run] Would verify directory: " + str(path))

        # Show what would be checked
        checksum_path = path / CHECKSUM_FILE
        if checksum_path.exists():
            click.echo(f"[dry-run] Would load checksums from: {checksum_path.name}")
            try:
                checksums = load_checksums(checksum_path)
                click.echo(f"[dry-run] Would verify {len(checksums)} file(s)")
            except Exception as e:
                click.echo(f"[dry-run] Note: Could not parse checksums: {e}", err=True)
        else:
            click.echo(f"[dry-run] Note: {CHECKSUM_FILE} not found", err=True)

        manifest_path = path / MANIFEST_FILE
        if (verify_manifest or verify_all) and manifest_path.exists():
            click.echo(f"[dry-run] Would display manifest from: {manifest_path.name}")

        click.echo("✅ [dry-run] Verification simulation complete")
        return

    if verify_manifest:
        show_manifest_info(path, verbose)
    elif verify_all:
        ok = verify_directory(path, verbose)
        show_manifest_info(path, verbose)
    else:
        ok = verify_directory(path, verbose)

    if ok:
        logger.info("✅ All verifications passed.")
    else:
        logger.error("❌ One or more verifications failed.")
        exit(1)


if __name__ == "__main__":
    main()
