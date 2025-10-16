#!/usr/bin/env python3
"""
converter.py
CLI utility for converting PEM certificate bundles into alternate formats.

Notes:
    • Requires OpenSSL and keytool to be installed and available on PATH.
    • Environment variables TRUST_JKS_PASSWORD and TRUST_P12_PASSWORD are used if needed.
    • Conversion logic implemented in helpers/convert_utils.py.
"""

import sys
from pathlib import Path
import click

CURRENT_DIR = Path(__file__).resolve().parent
HELPERS_DIR = CURRENT_DIR / "helpers"
sys.path.insert(0, str(HELPERS_DIR))

from convert_utils import convert_to_formats

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--pem-file", required=True, type=click.Path(exists=True), help="Path to input PEM bundle.")
@click.option("--output-dir", required=True, type=click.Path(), help="Directory for converted formats.")
@click.option("--formats", multiple=True, default=["p7b", "jks", "p12"], help="Output formats to produce (default: p7b jks p12).")
@click.option("--output-root", type=str, default="dist", help="Root directory for build outputs (default: ./dist)")
def main(pem_file, output_dir, formats, output_root):
    """Convert PEM certificate bundles into alternate formats."""
    click.secho(f"\n🔐 BundleCraft Converter\n---------------------------", fg="cyan")

    pem_path = Path(pem_file).resolve()
    out_dir = Path(output_dir).resolve()
    formats = [fmt.lower() for fmt in formats]

    if not pem_path.exists():
        click.secho(f"[ERROR] Input PEM file not found: {pem_path}", fg="red", err=True)
        sys.exit(5)

    if not out_dir.exists():
        click.secho(f"[INFO] Creating output directory: {out_dir}", fg="yellow")
        out_dir.mkdir(parents=True, exist_ok=True)

    try:
        convert_to_formats(pem_path, out_dir, formats, fmt_overrides={})
        click.secho(f"[SUCCESS] Conversion complete → {out_dir}", fg="green")
        sys.exit(0)
    except Exception as e:
        click.secho(f"[ERROR] Conversion failed: {e}", fg="red", err=True)
        sys.exit(5)


if __name__ == "__main__":
    main()
