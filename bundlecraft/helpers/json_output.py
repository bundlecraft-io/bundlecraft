#!/usr/bin/env python3
"""
json_output.py
Helper utilities for machine-readable JSON output across all BundleCraft commands.

This module provides consistent JSON schemas for all BundleCraft commands
to support CI/CD automation and scripting use cases.
"""

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


def emit_json(data: dict[str, Any], *, file=None) -> None:
    """Emit JSON data to stdout or specified file.

    Args:
        data: Dictionary to serialize as JSON
        file: Optional file object to write to (defaults to stdout)
    """
    output = json.dumps(data, indent=2, sort_keys=True, default=str)
    if file is None:
        print(output)
    else:
        file.write(output)
        file.write("\n")


def create_base_response(success: bool, command: str, **kwargs) -> dict[str, Any]:
    """Create a base JSON response structure.

    Args:
        success: Whether the operation succeeded
        command: Name of the command being executed
        **kwargs: Additional fields to include in the response

    Returns:
        Base response dictionary with timestamp and version
    """
    from bundlecraft import __version__

    response = {
        "success": success,
        "command": command,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
    }
    response.update(kwargs)
    return response


def create_build_response(
    success: bool,
    environment: str,
    bundles: list[dict[str, Any]],
    errors: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a JSON response for the build command.

    Schema:
        {
            "success": bool,
            "command": "build",
            "timestamp": str (ISO 8601),
            "version": str,
            "environment": str,
            "bundles": [
                {
                    "name": str,
                    "certificate_count": int,
                    "output_formats": [str],
                    "output_path": str,
                    "sources": [str],
                    "verification": {
                        "passed": bool,
                        "errors": [str],
                        "warnings": [str]
                    }
                }
            ],
            "errors": [str] (optional)
        }
    """
    response = create_base_response(
        success=success, command="build", environment=environment, bundles=bundles, **kwargs
    )
    if errors:
        response["errors"] = errors
    return response


def create_verify_response(
    success: bool,
    target_path: str,
    verified_files: int = 0,
    skipped_files: int = 0,
    total_certificates: int = 0,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a JSON response for the verify command.

    Schema:
        {
            "success": bool,
            "command": "verify",
            "timestamp": str (ISO 8601),
            "version": str,
            "target_path": str,
            "verified_files": int,
            "skipped_files": int,
            "total_certificates": int,
            "errors": [str] (optional),
            "warnings": [str] (optional)
        }
    """
    response = create_base_response(
        success=success,
        command="verify",
        target_path=target_path,
        verified_files=verified_files,
        skipped_files=skipped_files,
        total_certificates=total_certificates,
        **kwargs,
    )
    if errors:
        response["errors"] = errors
    if warnings:
        response["warnings"] = warnings
    return response


def create_convert_response(
    success: bool,
    input_path: str,
    output_dir: str,
    output_format: str,
    certificate_count: int = 0,
    errors: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a JSON response for the convert command.

    Schema:
        {
            "success": bool,
            "command": "convert",
            "timestamp": str (ISO 8601),
            "version": str,
            "input_path": str,
            "output_dir": str,
            "output_format": str,
            "certificate_count": int,
            "errors": [str] (optional)
        }
    """
    response = create_base_response(
        success=success,
        command="convert",
        input_path=input_path,
        output_dir=output_dir,
        output_format=output_format,
        certificate_count=certificate_count,
        **kwargs,
    )
    if errors:
        response["errors"] = errors
    return response


def create_fetch_response(
    success: bool,
    source_name: str,
    staging_path: str,
    fetched_sources: int = 0,
    local_sources: int = 0,
    total_files: int = 0,
    errors: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a JSON response for the fetch command.

    Schema:
        {
            "success": bool,
            "command": "fetch",
            "timestamp": str (ISO 8601),
            "version": str,
            "source_name": str,
            "staging_path": str,
            "fetched_sources": int,
            "local_sources": int,
            "total_files": int,
            "errors": [str] (optional)
        }
    """
    response = create_base_response(
        success=success,
        command="fetch",
        source_name=source_name,
        staging_path=staging_path,
        fetched_sources=fetched_sources,
        local_sources=local_sources,
        total_files=total_files,
        **kwargs,
    )
    if errors:
        response["errors"] = errors
    return response


@contextmanager
def suppress_output():
    """Context manager to suppress stdout (for JSON mode).

    Temporarily redirects stdout to devnull to suppress print statements
    while preserving stderr for error messages.

    Example:
        with suppress_output():
            # All print() calls are suppressed here
            print("This won't appear")
    """
    old_stdout = sys.stdout
    try:
        with open(os.devnull, "w") as devnull:
            sys.stdout = devnull
            yield
    finally:
        sys.stdout = old_stdout
