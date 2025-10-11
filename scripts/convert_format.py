#!/usr/bin/env python3
"""
convert_format.py
CLI wrapper for converting a canonical PEM bundle into other formats.

Usage:
  python scripts/convert_format.py --input build/prod/internal/ca-trust.pem --format jks --output build/prod/internal/ca-trust.jks --password changeit
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path

# Local helper
from helpers.converters import convert_to_formats

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Convert PEM bundle to other formats.")
    ap.add_argument("--input", required=True, help="Path to PEM bundle")
    ap.add_argument("--format", required=True, help="Target format (e.g., jks, p7b, der). Comma-separated allowed.")
    ap.add_argument("--output", help="Explicit output file (optional; if omitted, standard name is used)")
    ap.add_argument("--password", help="Password (used for formats like JKS)")
    return ap.parse_args()

def main() -> None:
    args = parse_args()
    inp = Path(args.input).resolve()
    if not inp.exists():
        print(f"[ERROR] Input not found: {inp}", file=sys.stderr)
        sys.exit(2)

    out_dir = inp.parent
    overrides = {}
    if args.password:
        overrides["jks"] = {"keystore_password": args.password}

    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    # If explicit output provided with single format, honor it by mapping name
    if args.output and len(formats) == 1:
        # We’ll ask converters to write its standard name, then rename here:
        convert_to_formats(inp, out_dir, formats, overrides)
        std_name = {
            "jks": "ca-trust.jks",
            "p7b": "ca-trust.p7b",
            "der": "ca-trust.der",
        }.get(formats[0].lower())
        if std_name:
            (out_dir / std_name).rename(Path(args.output))
        print(f"[INFO] Wrote: {args.output}")
    else:
        convert_to_formats(inp, out_dir, formats, overrides)

if __name__ == "__main__":
    main()
