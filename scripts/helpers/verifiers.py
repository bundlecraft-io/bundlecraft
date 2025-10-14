#!/usr/bin/env python3
"""
verifiers.py
Verification utilities for PKI-CA-Trust.

verify_bundle():
  • Validates PEM blocks for expiry
  • Ensures generated P7B/P12 are non-empty
  • Compares certificate counts across PEM, P7B, P12, JKS

Requires:
  - openssl
  - keytool (for JKS counting)
"""

import os
import sys
import subprocess
import datetime as dt
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.backends import default_backend


# ---------------------------------------------------------------------
# Core verifier
# ---------------------------------------------------------------------

def verify_bundle(target: Path, warn_days: int = 30, fail_on_expired: bool = True) -> int:
    """
    Verify PEM certificates or built trust bundles.

    Args:
        target (Path): PEM file, directory of PEMs, or build folder
        warn_days (int): warn if cert expires within N days
        fail_on_expired (bool): treat expired certs as fatal

    Returns:
        int: exit code (0 = ok, 1 = warnings, 5 = fatal)
    """
    if not target.exists():
        print(f"[ERROR] Target not found: {target}", file=sys.stderr)
        return 5

    pem_files = []
    if target.is_dir():
        pem_files = list(target.rglob("*.pem"))
    elif target.suffix.lower() == ".pem":
        pem_files = [target]
    else:
        print(f"[ERROR] Unsupported file type: {target}", file=sys.stderr)
        return 5

    if not pem_files:
        print(f"[WARN] No PEM files found in {target}")
        return 0

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
                exp = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after.replace(tzinfo=dt.timezone.utc)

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

    # --- summary ---
    print(f"\n[SUMMARY] Verified {total} certificate(s):")
    print(f"          Expired = {expired}, Expiring Soon = {expiring}, Errors = {errors}")

    if errors or (expired and fail_on_expired):
        print("[RESULT] ❌ Verification failed.")
        return 5
    if expiring > 0:
        print("[RESULT] ⚠️  Certificates expiring soon.")
        # not fatal; return 1 at end if no other failures

    # --- Sanity check for generated outputs ---
    if target.is_dir():
        if not _check_output_files(target):
            print("[RESULT] ❌ Detected empty or invalid output files.")
            return 5
        _compare_output_counts(target)

    if expiring > 0:
        return 1

    print("[RESULT] ✅ All certificates valid.")
    return 0


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
    """Check for empty or missing P7B/P12 outputs."""
    valid = True
    for ext in ("*.p7b", "*.p12"):
        for f in build_path.glob(ext):
            if not f.exists() or f.stat().st_size == 0:
                print(f"[ERROR] Empty or missing output file: {f}")
                valid = False
    return valid


# ---------------------------------------------------------------------
# Consistency: compare number of certs across outputs
# ---------------------------------------------------------------------

def _compare_output_counts(build_path: Path):
    """Compare the number of certs in PEM, P7B, P12, and JKS outputs."""
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
        # Use the first match for each format in this build folder
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
    """Return the number of certificates contained in a given output file."""
    ext = file_path.suffix.lower()
    try:
        if ext == ".pem":
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            return text.count("-----BEGIN CERTIFICATE-----")

        if ext == ".p7b":
            # DER P7B → text via openssl
            cmd = ["openssl", "pkcs7", "-print_certs", "-in", str(file_path), "-inform", "DER"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Count BEGIN CERTIFICATE or 'subject=' lines
            out = res.stdout
            n = out.count("-----BEGIN CERTIFICATE-----")
            if n == 0:
                n = out.count("subject=")
            return n

        if ext == ".p12":
            # Print ALL certs (no -clcerts), no keys
            cmd = ["openssl", "pkcs12", "-in", str(file_path), "-nokeys", "-passin", "pass:changeit"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            out = res.stdout
            # Count either PEM blocks or subject lines
            n = out.count("-----BEGIN CERTIFICATE-----")
            if n == 0:
                n = out.count("subject=")
            return n

        if ext == ".jks":
            storepass = os.environ.get("TRUST_JKS_PASSWORD", "changeit")
            cmd = ["keytool", "-list", "-keystore", str(file_path), "-storepass", storepass]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            out = res.stdout
            # Robust: try "Alias name:" first; fallback to "Your keystore contains X entries"
            n = out.count("Alias name:")
            if n == 0:
                # Try to parse "... contains N entries"
                import re
                m = re.search(r"contains\s+(\d+)\s+entries", out, flags=re.I)
                if m:
                    n = int(m.group(1))
            return n
    except Exception as e:
        print(f"[WARN] Could not count certs in {file_path}: {e}")
        return 0

    return 0
