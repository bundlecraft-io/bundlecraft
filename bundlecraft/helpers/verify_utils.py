#!/usr/bin/env python3
"""
verify_utils.py
Verification utilities for BundleCraft.

Capabilities:
    • verifier() – Verify PEMs or built trust bundles
    • verify_manifest() – Validate manifest.json and checksums.sha256 integrity
    • _check_output_files() – Detect empty/missing output files
    • _compare_output_counts() – Compare certificate counts across formats
"""

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from bundlecraft.helpers.exit_codes import ExitCode

# ---------------------------------------------------------------------
# Core verifier
# ---------------------------------------------------------------------


def verifier(target: Path, warn_days: int = 30, fail_on_expired: bool = True) -> int:
    if not target.exists():
        print(f"[ERROR] Target not found: {target}", file=sys.stderr)
        return ExitCode.INPUT_ERROR

    pem_files = []
    if target.is_dir():
        pem_files = list(target.rglob("*.pem"))
    elif target.suffix.lower() == ".pem":
        pem_files = [target]
    else:
        print(f"[ERROR] Unsupported file type: {target}", file=sys.stderr)
        return ExitCode.INPUT_ERROR

    if not pem_files:
        print(f"[WARN] No PEM files found in {target}")
        return ExitCode.SUCCESS

    now = dt.datetime.now(dt.timezone.utc)
    soon_cutoff = now + dt.timedelta(days=warn_days)
    total, expired, expiring, errors = 0, 0, 0, 0

    for pem in pem_files:
        text = pem.read_text(encoding="utf-8", errors="ignore")
        blocks = _split_pem_blocks(text)
        for blk in blocks:
            total += 1
            try:
                cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
                subj = cert.subject.rfc4514_string()
                exp = getattr(cert, "not_valid_after_utc", None)
                if exp is not None and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=dt.timezone.utc)

                if exp < now:
                    expired += 1
                    print(f"[ERROR] Expired: {subj} ({exp.date()}) [{pem.name}]")
                elif exp < soon_cutoff:
                    expiring += 1
                    days = (exp - now).days
                    print(f"[WARN] Expiring soon: {subj} ({days} days left) [{pem.name}]")
            except Exception as e:
                errors += 1
                print(f"[ERROR] Parse error in {pem.name}: {e}")

    print(f"\n[SUMMARY] Verified {total} certificate(s):")
    print(f"          Expired = {expired}, Expiring Soon = {expiring}, Errors = {errors}")

    if errors or (expired and fail_on_expired):
        print("[RESULT] ❌ Verification failed.")
        return ExitCode.EXPIRED_CERT if expired else ExitCode.INVALID_CERT
    if expiring > 0:
        print("[RESULT] ⚠️  Certificates expiring soon.")
        return ExitCode.GENERAL_ERROR

    if target.is_dir():
        if not _check_output_files(target):
            print("[RESULT] ❌ Detected empty or invalid output files.")
            return ExitCode.VALIDATION_ERROR
        _compare_output_counts(target)

    if expiring > 0:
        return ExitCode.GENERAL_ERROR

    print("[RESULT] ✅ All certificates valid.")
    return ExitCode.SUCCESS


# ---------------------------------------------------------------------
# Manifest verification
# ---------------------------------------------------------------------


def verify_manifest(manifest_path: Path) -> bool:
    base_dir = manifest_path.parent
    manifest_file = manifest_path
    checksum_file = base_dir / "checksums.sha256"

    if not manifest_file.exists():
        print(f"[ERROR] Manifest file missing: {manifest_file}")
        return False

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to parse manifest: {e}")
        return False

    files = manifest.get("files", [])
    if not files:
        print("[WARN] No 'files' field found in manifest.")
        return False

    success = True
    for entry in files:
        relpath = entry.get("path")
        expected_hash = entry.get("sha256")
        if not relpath or not expected_hash:
            print(f"[WARN] Malformed entry in manifest: {entry}")
            continue

        # Skip manifest.json itself
        if Path(relpath).name == "manifest.json":
            print(f"[INFO] Skipping manifest file: {relpath}")
            continue

        target_file = base_dir / relpath
        if not target_file.exists():
            print(f"[ERROR] Missing file: {target_file}")
            success = False
            continue

        actual_hash = _sha256_file(target_file)
        if actual_hash != expected_hash:
            print(f"[ERROR] Hash mismatch for {relpath}")
            print(f"        Expected: {expected_hash}")
            print(f"        Actual:   {actual_hash}")
            success = False
        else:
            print(f"[INFO] Verified: {relpath}")

    if checksum_file.exists():
        for line in checksum_file.read_text(encoding="utf-8").splitlines():
            if "  " not in line:
                continue
            expected_hash, relpath = line.split("  ", 1)
            target_file = base_dir / relpath
            if target_file.exists():
                actual_hash = _sha256_file(target_file)
                if actual_hash != expected_hash:
                    print(f"[ERROR] Checksum mismatch for {relpath}")
                    success = False

    if success:
        print("[RESULT] ✅ Manifest verification successful.")
    else:
        print("[RESULT] ❌ Manifest verification failed.")
    return success


def _sha256_file(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _split_pem_blocks(text: str) -> list[str]:
    start, end = "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"
    blocks, buf, inside = [], [], False
    for line in text.splitlines():
        if start in line:
            inside, buf = True, [line]
        elif end in line and inside:
            buf.append(line)
            blocks.append("\n".join(buf) + "\n")
            inside = False
        elif inside:
            buf.append(line)
    return blocks


def _check_output_files(build_path: Path) -> bool:
    valid = True
    for ext in ("*.p7b", "*.p12"):
        for f in build_path.glob(ext):
            if not f.exists() or f.stat().st_size == 0:
                print(f"[ERROR] Empty or missing output file: {f}")
                valid = False
    return valid


def _compare_output_counts(build_path: Path):
    counts = {}
    for pattern, label in [
        ("*.pem", "PEM"),
        ("*.p7b", "P7B"),
        ("*.p12", "P12"),
        ("*.jks", "JKS"),
    ]:
        files = list(build_path.glob(pattern))
        if not files:
            continue
        f = files[0]
        counts[label] = _count_certs_in_file(f)

    if not counts:
        print("[INFO] No outputs found for count comparison.")
        return

    canonical = counts.get("PEM", max(counts.values()))
    print(f"[INFO] Certificate count summary: {counts}")

    for fmt, count in counts.items():
        if count != canonical:
            print(f"[WARN] {fmt} count mismatch: {count} vs {canonical} (PEM)")
        else:
            print(f"[INFO] {fmt} count OK: {count}")


def _count_certs_in_file(file_path: Path) -> int:
    ext = file_path.suffix.lower()
    try:
        if ext == ".pem":
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            return text.count("-----BEGIN CERTIFICATE-----")
        if ext == ".p7b":
            # Use cryptography module to load and count PKCS#7 certificates
            from cryptography.hazmat.primitives.serialization import pkcs7

            data = file_path.read_bytes()
            try:
                # Try DER format first (most common for .p7b)
                certs = pkcs7.load_der_pkcs7_certificates(data)
            except ValueError:
                # Fallback to PEM format
                certs = pkcs7.load_pem_pkcs7_certificates(data)
            return len(certs)
        if ext == ".p12":
            # Use cryptography module to load and count PKCS#12 certificates
            from cryptography.hazmat.primitives.serialization import pkcs12

            data = file_path.read_bytes()
            password = os.environ.get("TRUST_P12_PASSWORD", "changeit")
            # Try with password, then without
            try:
                pkey, cert, addl = pkcs12.load_key_and_certificates(
                    data, password=password.encode()
                )
            except Exception:
                # Try with empty password
                try:
                    pkey, cert, addl = pkcs12.load_key_and_certificates(data, password=None)
                except Exception:
                    # Last attempt with different password
                    pkey, cert, addl = pkcs12.load_key_and_certificates(data, password=b"")

            count = 0
            if cert:
                count += 1
            if addl:
                count += len(addl)
            return count
        if ext == ".jks":
            import jks

            storepass = os.environ.get("TRUST_JKS_PASSWORD", "changeit")
            keystore = jks.KeyStore.load(str(file_path), storepass)
            count = 0
            for _alias, entry in keystore.entries.items():
                if isinstance(entry, jks.TrustedCertEntry):
                    count += 1
                elif isinstance(entry, jks.PrivateKeyEntry):
                    # Count certificates in the certificate chain
                    count += len(entry.cert_chain)
            return count
    except Exception as e:
        print(f"[WARN] Could not count certs in {file_path}: {e}")
        return 0
    return 0
