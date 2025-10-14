#!/usr/bin/env python3
"""
verify_bundle.py
Standalone CLI utility for verifying certificate bundles or source directories.

Usage:
    python scripts/verify_bundle.py <target_path> [--warn-days N] [--fail]

Examples:
    # Verify a built bundle PEM
    python scripts/verify_bundle.py build/prod/internal/ca-trust.pem

    # Verify all PEMs under a source directory (recursive)
    python scripts/verify_bundle.py sources/internal/ --warn-days 45

    # Fail the run if any certificate is expired
    python scripts/verify_bundle.py build/dev/internal/ --fail

Exit codes:
    0 = all certificates valid
    1 = warnings (expiring soon)
    5 = fatal error (expired certs, parse error, or missing target)
"""

import sys
import argparse
from pathlib import Path

# Allow relative imports from the helpers directory
CURRENT_DIR = Path(__file__).resolve().parent
HELPERS_DIR = CURRENT_DIR / "helpers"
sys.path.insert(0, str(HELPERS_DIR))

from verifiers import verify_bundle


def main():
    parser = argparse.ArgumentParser(
        description="Verify certificate bundles or source directories."
    )
    parser.add_argument(
        "target",
        help="Path to a PEM file, directory of PEMs, or built bundle folder.",
    )
    parser.add_argument(
        "--warn-days",
        type=int,
        default=30,
        help="Days before expiry to issue warnings (default: 30).",
    )
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Treat expired certificates as fatal errors (exit 5).",
    )

    args = parser.parse_args()
    target = Path(args.target).resolve()
    
    exit_code = verify_bundle(target, warn_days=args.warn_days, fail_on_expired=args.fail)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
