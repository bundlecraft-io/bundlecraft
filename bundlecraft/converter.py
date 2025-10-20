#!/usr/bin/env python3
"""
converter.py
CLI utility for converting certificate bundles between formats.

IMPORTANT: BundleCraft processes CERTIFICATES and PUBLIC KEYS ONLY.
           Private keys are NOT supported and will be ignored if encountered in input.
           If you need private keys in your bundles, add them securely via external tooling.

Notes:
  • Requires OpenSSL and keytool to be installed and available on PATH.
  • Environment variables TRUST_JKS_PASSWORD and TRUST_P12_PASSWORD are used if needed.
  • Conversion logic implemented in helpers/convert_utils.py.
  • CI/CD safe: will not prompt for passwords unless --prompt is provided.
"""

import os
import sys
from getpass import getpass
from pathlib import Path

import click

from bundlecraft.helpers.convert_utils import convert_from_any


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
# Back-compat: --pem-file maps to --input
@click.option(
    "--pem-file",
    "pem_file",
    required=False,
    type=click.Path(exists=True),
    help="[Deprecated] Path to input PEM bundle (use --input)",
)
@click.option(
    "--input",
    "input_path",
    required=False,
    type=click.Path(exists=True),
    help="Path to input file (PEM, DER, P7B, JKS, P12)",
)
@click.option(
    "--input-format",
    type=click.Choice(["pem", "der", "p7b", "jks", "p12", "pfx"], case_sensitive=False),
    help="Explicitly specify input format (optional; inferred from extension if omitted)",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(),
    help="Directory for converted outputs.",
)
@click.option(
    "--output-format",
    required=True,
    type=click.Choice(["pem", "p7b", "jks", "p12", "zip"], case_sensitive=False),
    help="Output format to produce (one of: pem, p7b, jks, p12, zip)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite output file(s) if they already exist.",
)
@click.option(
    "--password",
    help=(
        "Password for input if required. Prefer env vars TRUST_P12_PASSWORD/TRUST_JKS_PASSWORD. "
        "CI-safe: not prompted unless --prompt is used."
    ),
)
@click.option(
    "--prompt",
    is_flag=True,
    default=False,
    help="Prompt for password if required and not provided (use in interactive sessions only)",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging",
)
@click.option(
    "--output-basename",
    "output_basename",
    type=str,
    required=False,
    help="Base name for output files (default: inferred from input). Example: bundlecraft-ca-trust",
)
@click.option(
    "--output-root",
    type=str,
    default="dist",
    help="Root directory for build outputs (default: ./dist)",
)
def main(
    pem_file,
    input_path,
    input_format,
    output_dir,
    output_format,
    password,
    prompt,
    verbose,
    output_root,
    output_basename,
    force,
):
    """Convert certificate bundles between formats without losing certificates.

    IMPORTANT: Private keys are NOT processed. Only certificates are extracted and converted.
    Output files are always named 'bundlecraft-ca-trust.[FORMAT]'.
    Use --force to overwrite existing files.
    """
    click.secho("\n🔐 BundleCraft Converter\n---------------------------", fg="cyan")

    in_path = Path(input_path or pem_file).resolve() if (input_path or pem_file) else None
    if in_path is None:
        click.secho("[ERROR] Missing required input (--input or --pem-file)", fg="red", err=True)
        sys.exit(2)
    out_dir = Path(output_dir).resolve()

    fmt = output_format.lower()
    formats = [fmt]

    if not in_path.exists():
        click.secho(f"[ERROR] Input file not found: {in_path}", fg="red", err=True)
        sys.exit(2)

    if not out_dir.exists():
        click.secho(f"[INFO] Creating output directory: {out_dir}", fg="yellow")
        out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve password policy (CI/CD safe)
    resolved_password = password
    if resolved_password is None:
        # Try env vars according to input type
        ext = (input_format or in_path.suffix.lstrip(".")).lower()
        if ext in {"p12", "pfx", "pkcs12"}:
            resolved_password = os.environ.get("TRUST_P12_PASSWORD")
        elif ext in {"jks"}:
            resolved_password = os.environ.get("TRUST_JKS_PASSWORD")

    if resolved_password is None and prompt:
        resolved_password = getpass("Password: ")

    if resolved_password is None and (input_format or in_path.suffix.lstrip(".")).lower() in {
        "p12",
        "pfx",
        "pkcs12",
        "jks",
    }:
        click.secho(
            "[ERROR] Password required for protected input. Use env var or --password (or --prompt).",
            fg="red",
            err=True,
        )
        sys.exit(2)

    try:
        convert_from_any(
            in_path,
            out_dir,
            formats,
            input_format=input_format,
            password=resolved_password,
            verbose=verbose,
            force=force,
            output_basename=output_basename,
        )
        click.secho(f"[SUCCESS] Conversion complete → {out_dir}", fg="green")
        sys.exit(0)
    except Exception as e:
        click.secho(f"[ERROR] Conversion failed: {e}", fg="red", err=True)
        sys.exit(2)


# Back-compat function used by older tests


def convert_bundle(pem_path: Path, output_dir: Path, formats: list[str]):
    try:
        pem_path = Path(pem_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Reuse normalization no-op: PEM in → PEM out
        from bundlecraft.helpers.convert_utils import convert_to_formats

        convert_to_formats(pem_path, output_dir, formats, fmt_overrides={})

        class Result:
            success = True

        return Result()
    except Exception:
        import traceback

        traceback.print_exc()  # Print the error for debugging
        raise  # Re-raise for proper test failure

        class Result:
            success = False

        return Result()


if __name__ == "__main__":
    main()
