#!/usr/bin/env python3
"""
converter.py
CLI utility for converting certificate bundles between formats.

IMPORTANT: BundleCraft processes CERTIFICATES and PUBLIC KEYS ONLY.
           Private keys are NOT supported and will be ignored if encountered in input.
           If you need private keys in your bundles, add them securely via external tooling.

Notes:
  • Requires OpenSSL for P7B and P12 conversions.
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
from bundlecraft.helpers.exit_codes import ExitCode
from bundlecraft.helpers.ui import print_banner


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
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually converting or writing any files",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit machine-readable JSON output (suppresses human-readable output)",
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
    dry_run,
    json_output,
):
    """Convert certificates between different formats.

    IMPORTANT: Private keys are NOT processed. Only certificates are extracted and converted.
    Output files are always named 'bundlecraft-ca-trust.[FORMAT]'.
    Use --force to overwrite existing files.
        Use --dry-run to preview what would be converted without making any changes.
    """
    json_errors = []
    cert_count = 0

    if not json_output:
        # Unified banner
        print_banner("Converter")

        if dry_run:
            click.secho(
                "[DRY RUN MODE] No files will be converted or written\n", fg="yellow", bold=True
            )

    in_path = Path(input_path or pem_file).resolve() if (input_path or pem_file) else None
    if in_path is None:
        error_msg = "Missing required input (--input or --pem-file)"
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_convert_response, emit_json

            emit_json(
                create_convert_response(
                    success=False,
                    input_path="",
                    output_dir="",
                    output_format=output_format,
                    errors=json_errors,
                )
            )
        else:
            click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
        sys.exit(ExitCode.INPUT_ERROR)
    out_dir = Path(output_dir).resolve()

    fmt = output_format.lower()
    formats = [fmt]

    if not in_path.exists():
        error_msg = f"Input file not found: {in_path}"
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_convert_response, emit_json

            emit_json(
                create_convert_response(
                    success=False,
                    input_path=str(in_path),
                    output_dir=str(out_dir),
                    output_format=output_format,
                    errors=json_errors,
                )
            )
        else:
            click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
        sys.exit(ExitCode.INPUT_ERROR)

    if not dry_run and not out_dir.exists():
        if not json_output:
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
        error_msg = (
            "Password required for protected input. Use env var or --password (or --prompt)."
        )
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_convert_response, emit_json

            emit_json(
                create_convert_response(
                    success=False,
                    input_path=str(in_path),
                    output_dir=str(out_dir),
                    output_format=output_format,
                    errors=json_errors,
                )
            )
        else:
            click.secho(
                f"[ERROR] {error_msg}",
                fg="red",
                err=True,
            )
        sys.exit(ExitCode.OUTPUT_ERROR)

    try:
        if dry_run:
            if not json_output:
                click.secho(f"[dry-run] Would convert from: {in_path}", fg="yellow")
                click.secho(f"[dry-run] Would write to: {out_dir}", fg="yellow")
                click.secho(f"[dry-run] Bundle format(s): {', '.join(formats)}", fg="yellow")
                if output_basename:
                    click.secho(f"[dry-run] Output basename: {output_basename}", fg="yellow")
                click.secho("\n[SUCCESS] [dry-run] Conversion simulation complete", fg="yellow")
            else:
                from bundlecraft.helpers.json_output import create_convert_response, emit_json

                emit_json(
                    create_convert_response(
                        success=True,
                        input_path=str(in_path),
                        output_dir=str(out_dir),
                        output_format=output_format,
                        certificate_count=0,
                        dry_run=True,
                    )
                )
            sys.exit(ExitCode.SUCCESS)

        # Suppress stdout when using JSON output
        if json_output:
            import contextlib
            import io

            with contextlib.redirect_stdout(io.StringIO()):
                convert_from_any(
                    in_path,
                    out_dir,
                    formats,
                    input_format=input_format,
                    password=resolved_password,
                    verbose=False,  # Suppress verbose output in JSON mode
                    force=force,
                    output_basename=output_basename,
                )
        else:
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

        # Count certificates in output
        # Try to read the output file to count certs
        output_file = out_dir / f"{output_basename or 'bundlecraft-ca-trust'}.{fmt}"
        if output_file.exists() and fmt == "pem":
            import re

            text = output_file.read_text(encoding="utf-8", errors="ignore")
            cert_count = len(re.findall(r"-----BEGIN CERTIFICATE-----", text))

        if json_output:
            from bundlecraft.helpers.json_output import create_convert_response, emit_json

            emit_json(
                create_convert_response(
                    success=True,
                    input_path=str(in_path),
                    output_dir=str(out_dir),
                    output_format=output_format,
                    certificate_count=cert_count,
                )
            )
        else:
            # Uniform success icon and color
            click.secho(f"✅ Conversion complete → {out_dir}", fg="green")
        sys.exit(ExitCode.SUCCESS)
    except Exception as e:
        error_msg = f"Conversion failed: {e}"
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_convert_response, emit_json

            emit_json(
                create_convert_response(
                    success=False,
                    input_path=str(in_path),
                    output_dir=str(out_dir),
                    output_format=output_format,
                    errors=json_errors,
                )
            )
        else:
            click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
        sys.exit(ExitCode.CONVERSION_ERROR)


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
