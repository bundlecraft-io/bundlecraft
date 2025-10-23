#!/usr/bin/env python3
"""
differ.py
Compare two bundle builds and generate diff reports (human-readable and JSON).

Usage:
  bundlecraft diff --from <path1> --to <path2> [--output-format {human|json}]

Features:
  - Compares certificates between two bundle directories
  - Identifies added, removed, and changed certificates
  - Outputs human-readable report or structured JSON
  - Uses SHA256 fingerprints for certificate identification
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

import click
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from bundlecraft.helpers.exit_codes import ExitCode
from bundlecraft.helpers.ui import print_banner


def _extract_cert_info(pem_block: str) -> dict[str, any] | None:
    """Extract certificate information from PEM block.

    Returns:
        Dictionary with fingerprint, subject, issuer, not_before, not_after, serial
        or None if parse fails
    """
    try:
        cert = x509.load_pem_x509_certificate(pem_block.encode("utf-8"), default_backend())

        # Compute SHA256 fingerprint
        b64re = re.compile(
            r"-----BEGIN CERTIFICATE-----\s*([A-Za-z0-9+/=\s]+)-----END CERTIFICATE-----",
            re.S,
        )
        m = b64re.search(pem_block)
        if not m:
            return None
        der = base64.b64decode("".join(m.group(1).split()))
        fingerprint = hashlib.sha256(der).hexdigest()

        # Extract certificate details
        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        serial = hex(cert.serial_number)

        # Handle timezone-aware dates
        not_before = getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before
        not_after = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after

        return {
            "fingerprint": fingerprint,
            "subject": subject,
            "issuer": issuer,
            "serial": serial,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
        }
    except Exception:
        return None


def _load_certs_from_pem(pem_path: Path) -> dict[str, dict[str, any]]:
    """Load certificates from PEM file and return dict keyed by fingerprint.

    Returns:
        Dictionary mapping fingerprint -> cert_info
    """
    if not pem_path.exists():
        return {}

    content = pem_path.read_text(encoding="utf-8")

    # Split into individual certificates
    cert_re = re.compile(r"(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)", re.S)
    pem_blocks = cert_re.findall(content)

    certs = {}
    for pem_block in pem_blocks:
        cert_info = _extract_cert_info(pem_block)
        if cert_info:
            certs[cert_info["fingerprint"]] = cert_info

    return certs


def _load_manifest(manifest_path: Path) -> dict[str, any] | None:
    """Load manifest.json if it exists."""
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def compare_bundles(from_dir: Path, to_dir: Path) -> dict[str, any]:
    """Compare two bundle directories and generate diff.

    Args:
        from_dir: Path to the first (old) bundle directory
        to_dir: Path to the second (new) bundle directory

    Returns:
        Dictionary with diff results including added, removed, and unchanged counts
    """
    # Find PEM files
    from_pem = from_dir / "bundlecraft-ca-trust.pem"
    to_pem = to_dir / "bundlecraft-ca-trust.pem"

    # Load certificates
    from_certs = _load_certs_from_pem(from_pem)
    to_certs = _load_certs_from_pem(to_pem)

    # Load manifests for metadata
    from_manifest = _load_manifest(from_dir / "manifest.json")
    to_manifest = _load_manifest(to_dir / "manifest.json")

    # Compute differences
    from_fps = set(from_certs.keys())
    to_fps = set(to_certs.keys())

    added_fps = to_fps - from_fps
    removed_fps = from_fps - to_fps
    unchanged_fps = from_fps & to_fps

    # Collect detailed info
    added = [to_certs[fp] for fp in sorted(added_fps)]
    removed = [from_certs[fp] for fp in sorted(removed_fps)]
    unchanged = [from_certs[fp] for fp in sorted(unchanged_fps)]

    return {
        "from": {
            "path": str(from_dir),
            "manifest": from_manifest,
            "certificate_count": len(from_certs),
        },
        "to": {
            "path": str(to_dir),
            "manifest": to_manifest,
            "certificate_count": len(to_certs),
        },
        "diff": {
            "added": added,
            "removed": removed,
            "unchanged": unchanged,
            "summary": {
                "added_count": len(added),
                "removed_count": len(removed),
                "unchanged_count": len(unchanged),
                "total_changes": len(added) + len(removed),
            },
        },
    }


def format_human_readable(diff_result: dict[str, any]) -> str:
    """Format diff result as human-readable text.

    Args:
        diff_result: Result from compare_bundles()

    Returns:
        Formatted string for human consumption
    """
    lines = []

    lines.append("=" * 25)
    lines.append("🔐 BundleCraft Differ")
    lines.append("=" * 25)
    lines.append("")

    # From/To paths
    lines.append(f"FROM: {diff_result['from']['path']}")
    if diff_result["from"]["manifest"]:
        fm = diff_result["from"]["manifest"]
        lines.append(f"  Env: {fm.get('env', 'N/A')}")
        lines.append(f"  Bundle: {fm.get('bundle', 'N/A')}")
        lines.append(f"  Timestamp: {fm.get('timestamp_utc', 'N/A')}")
    lines.append(f"  Certificates: {diff_result['from']['certificate_count']}")
    lines.append("")

    lines.append(f"TO: {diff_result['to']['path']}")
    if diff_result["to"]["manifest"]:
        tm = diff_result["to"]["manifest"]
        lines.append(f"  Env: {tm.get('env', 'N/A')}")
        lines.append(f"  Bundle: {tm.get('bundle', 'N/A')}")
        lines.append(f"  Timestamp: {tm.get('timestamp_utc', 'N/A')}")
    lines.append(f"  Certificates: {diff_result['to']['certificate_count']}")
    lines.append("")

    # Summary
    summary = diff_result["diff"]["summary"]
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"  Added:     {summary['added_count']}")
    lines.append(f"  Removed:   {summary['removed_count']}")
    lines.append(f"  Unchanged: {summary['unchanged_count']}")
    lines.append(f"  Total Changes: {summary['total_changes']}")
    lines.append("")

    # Added certificates
    if diff_result["diff"]["added"]:
        lines.append("-" * 80)
        lines.append(f"ADDED CERTIFICATES ({summary['added_count']})")
        lines.append("-" * 80)
        for cert in diff_result["diff"]["added"]:
            lines.append(f"  Subject: {cert['subject']}")
            lines.append(f"    Fingerprint: {cert['fingerprint']}")
            lines.append(f"    Issuer: {cert['issuer']}")
            lines.append(f"    Valid: {cert['not_before']} to {cert['not_after']}")
            lines.append("")

    # Removed certificates
    if diff_result["diff"]["removed"]:
        lines.append("-" * 80)
        lines.append(f"REMOVED CERTIFICATES ({summary['removed_count']})")
        lines.append("-" * 80)
        for cert in diff_result["diff"]["removed"]:
            lines.append(f"  Subject: {cert['subject']}")
            lines.append(f"    Fingerprint: {cert['fingerprint']}")
            lines.append(f"    Issuer: {cert['issuer']}")
            lines.append(f"    Valid: {cert['not_before']} to {cert['not_after']}")
            lines.append("")

    # If no changes
    if summary["total_changes"] == 0:
        lines.append("-" * 80)
        lines.append("NO CHANGES DETECTED")
        lines.append("-" * 80)
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def format_json(diff_result: dict[str, any]) -> str:
    """Format diff result as JSON.

    Args:
        diff_result: Result from compare_bundles()

    Returns:
        JSON string
    """
    return json.dumps(diff_result, indent=2, sort_keys=True)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--from",
    "from_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to the first (old) bundle directory",
)
@click.option(
    "--to",
    "to_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to the second (new) bundle directory",
)
@click.option(
    "--output-format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    help="Output format: human-readable or JSON (default: human)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write output to file instead of stdout",
)
def main(from_path: Path, to_path: Path, output_format: str, output: Path | None):
    """Compare two bundle builds and generate diff reports.

    This command compares certificate bundles to identify added, removed, and
    unchanged certificates between two builds. It's useful for:

    \b
    - Auditing bundle changes between releases
    - Verifying expected certificate additions/removals
    - Tracking trust store evolution over time

    The comparison uses SHA256 fingerprints to uniquely identify certificates.

    Examples:

    \b
      # Compare two bundle builds (human-readable)
      bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal

    \b
      # Generate JSON diff report
      bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal --output-format json

    \b
      # Save diff to file
      bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal -o diff-report.txt
    """
    try:
        # Compare bundles
        diff_result = compare_bundles(from_path, to_path)

        # Format output
        if output_format.lower() == "json":
            formatted = format_json(diff_result)
        else:
            formatted = format_human_readable(diff_result)

        # Write to file or stdout
        if output:
            output.write_text(formatted, encoding="utf-8")
            click.secho(f"✓ Diff report written to: {output}", fg="green")
        else:
            # Cyan banner for human-readable stdout (keeps in-report title for backward compatibility)
            if output_format.lower() == "human":
                print_banner("Differ")
            click.echo(formatted)

        # Exit code based on changes
        summary = diff_result["diff"]["summary"]
        if summary["total_changes"] > 0:
            sys.exit(ExitCode.SUCCESS)  # Changes detected, but not an error
        else:
            sys.exit(ExitCode.SUCCESS)  # No changes

    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(ExitCode.GENERAL_ERROR)


if __name__ == "__main__":
    main()
