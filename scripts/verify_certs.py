#!/usr/bin/env python3
"""
verify_certs.py
Standalone verifier for PEM bundles produced by pki-ca-trust.
Checks for expiration, soon-to-expire certificates, and prints a summary.
"""

from __future__ import annotations
import argparse, sys, datetime as dt
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.backends import default_backend

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Verify certificates in a PEM bundle.")
    ap.add_argument("--file", required=True, help="Path to PEM bundle (e.g., build/prod/internal/ca-trust.pem)")
    ap.add_argument("--warn-days", type=int, default=30, help="Days before expiry to warn")
    ap.add_argument("--fail-on-expired", action="store_true", help="Exit non-zero if any expired certs found")
    return ap.parse_args()

def read_pem_blocks(path: Path):
    start, end = "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"
    blocks, text = [], path.read_text(encoding="utf-8", errors="ignore")
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

def verify_bundle(pem_path: Path, warn_days: int = 30, fail_on_expired: bool = False) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    soon_cutoff = now + dt.timedelta(days=warn_days)
    blocks = read_pem_blocks(pem_path)
    if not blocks:
        print("[ERROR] No certificates found in file.")
        return 3

    expired, expiring, valid = [], [], []

    for blk in blocks:
        try:
            cert = x509.load_pem_x509_certificate(blk.encode("utf-8"), default_backend())
            subject = cert.subject.rfc4514_string()
            exp = cert.not_valid_after_utc
            if exp < now:
                expired.append((subject, exp.date()))
            elif exp < soon_cutoff:
                expiring.append((subject, exp.date()))
            else:
                valid.append((subject, exp.date()))
        except Exception as e:
            print(f"[WARN] Parse error: {e}")

    for subj, date in expired:
        print(f"[ERROR] Expired: {subj} (expired {date})")
    for subj, date in expiring:
        days = (dt.datetime.combine(date, dt.time.min, tzinfo=dt.timezone.utc) - now).days
        print(f"[WARN] Expiring soon: {subj} ({days} days left, expires {date})")

    print("\n[SUMMARY]")
    print(f"Total certs: {len(blocks)}")
    print(f"  Valid:         {len(valid)}")
    print(f"  Expiring soon: {len(expiring)} (<= {warn_days} days)")
    print(f"  Expired:       {len(expired)}")

    if expired and fail_on_expired:
        print("[ERROR] One or more certificates are expired. Exiting non-zero.")
        return 5
    return 0

def main():
    args = parse_args()
    code = verify_bundle(Path(args.file), args.warn_days, args.fail_on_expired)
    sys.exit(code)

if __name__ == "__main__":
    main()
