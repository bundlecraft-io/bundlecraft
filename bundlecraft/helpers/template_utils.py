#!/usr/bin/env python3
"""
template_utils.py
Helper functions for expanding template variables in output metadata.

Supported template variables:
- {{bundle}} - Bundle name
- {{env}} - Environment name
- {{timestamp}} - ISO 8601 timestamp (UTC)
- {{date}} - Date in YYYY-MM-DD format
- {{git_commit}} - Git commit hash (short form)
"""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from typing import Any


def get_git_commit() -> str:
    """Get current git commit hash (short form).

    Returns:
        Short git commit hash (7 chars) or 'unknown' if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "unknown"


def expand_template_variables(
    template: str,
    bundle: str = "",
    env: str = "",
    timestamp_utc: str | None = None,
) -> str:
    """Expand template variables in a string.

    Args:
        template: String with template variables (e.g., "{{bundle}}-{{env}}")
        bundle: Bundle name
        env: Environment/env name
        timestamp_utc: Optional ISO 8601 timestamp (UTC), generated if not provided

    Returns:
        String with template variables expanded

    Example:
        >>> expand_template_variables("{{bundle}}-{{env}}-{{date}}", "prod", "internal")
        "prod-internal-2025-10-21"
    """
    if not template:
        return template

    # Generate timestamp if not provided
    if timestamp_utc is None:
        now = dt.datetime.now(dt.timezone.utc)
        timestamp_utc = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # Parse timestamp to extract date
        try:
            now = dt.datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            now = dt.datetime.now(dt.timezone.utc)

    date_str = now.strftime("%Y-%m-%d")
    git_commit = get_git_commit()

    # Template variable mapping
    variables = {
        "bundle": bundle,
        "env": env,
        "timestamp": timestamp_utc,
        "date": date_str,
        "git_commit": git_commit,
    }

    # Replace template variables using regex
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    # Pattern: {{variable_name}}
    result = re.sub(r"\{\{(\w+)\}\}", replace_var, template)
    return result


def expand_metadata_dict(
    metadata: dict[str, str],
    bundle: str = "",
    env: str = "",
    timestamp_utc: str | None = None,
) -> dict[str, str]:
    """Expand template variables in all values of a metadata dictionary.

    Args:
        metadata: Dictionary with template variables in values
        bundle: Bundle name
        env: Environment/env name
        timestamp_utc: Optional ISO 8601 timestamp (UTC)

    Returns:
        Dictionary with expanded values
    """
    return {
        key: expand_template_variables(value, bundle, env, timestamp_utc)
        for key, value in metadata.items()
    }


def expand_output_metadata(
    output_metadata: dict[str, Any] | None,
    bundle: str = "",
    env: str = "",
    timestamp_utc: str | None = None,
) -> dict[str, Any] | None:
    """Expand template variables in output_metadata structure.

    Args:
        output_metadata: Output metadata dict with 'annotations' and 'labels' keys
        bundle: Bundle name
        env: Environment/env name
        timestamp_utc: Optional ISO 8601 timestamp (UTC)

    Returns:
        Output metadata dict with expanded template variables
    """
    if not output_metadata:
        return None

    result = {}

    if "annotations" in output_metadata and output_metadata["annotations"]:
        result["annotations"] = expand_metadata_dict(
            output_metadata["annotations"], bundle, env, timestamp_utc
        )

    if "labels" in output_metadata and output_metadata["labels"]:
        result["labels"] = expand_metadata_dict(
            output_metadata["labels"], bundle, env, timestamp_utc
        )

    return result if result else None
