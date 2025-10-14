#!/usr/bin/env python3
"""
convert_format.py
Standalone CLI utility for converting PEM certificate bundles into alternate formats.

Usage:
    python scripts/convert_format.py <pem_file> <output_dir> [formats...]

Examples:
    # Convert a PEM bundle to P7B, JKS, and PKCS#12
    python scripts/convert_format.py build/prod/internal/ca-trust.pem build/prod/internal/ p7b jks p12

    # Convert only to JKS and P7B
    python scripts/convert_format.py build/dev/internal/ca-trust.pem build/dev/internal/ jks p7b

    # Use default formats (p7b, jks, p12)
    python scripts/convert_format.py build/dev/internal/ca-trust.pem build/dev/internal/

Notes:
    • Requires OpenSSL and keytool to be installed and available on PATH.
    • Environment variables TRUST_JKS_PASSWORD and TRUST_P12_PASSWORD are used if needed.
    • The conversion logic is implemented in helpers/converters.py.
"""

import sys
import argparse
from pathlib import Path

# Allow relative imports from the helpers directory
CURRENT_DIR = Path(__file__).resolve().parent
HELPERS_DIR = CURRENT_DIR / "helpers"
sys.path.insert(0, str(HELPERS_DIR))

from converters import convert_to_formats


def main():
    parser = argparse.ArgumentParser(
        description="Convert PEM bundles into other trust store formats."
    )
    parser.add_argument(
        "pem_file",
        help="Path to the input PEM file containing one or more certificates.",
    )
    parser.add_argument(
        "output_dir",
        help="Directory where converted formats will be written.",
    )
    parser.add_argument(
        "formats",
        nargs="*",
        default=["p7b", "jks", "p12"],
        help="Output formats to produce (default: p7b jks p12).",
    )

    args = parser.parse_args()
    pem_path = Path(args.pem_file).resolve()
    out_dir = Path(args.output_dir).resolve()
    formats = [fmt.lower() for fmt in args.formats]

    if not pem_path.exists():
        print(f"[ERROR] Input PEM file not found: {pem_path}", file=sys.stderr)
        sys.exit(5)
    if not out_dir.exists():
        print(f"[INFO] Creating output directory: {out_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)

    try:
        convert_to_formats(pem_path, out_dir, formats, fmt_overrides={})
        print(f"[SUCCESS] Conversion complete → {out_dir}")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Conversion failed: {e}", file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()
