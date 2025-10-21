#!/usr/bin/env python3
"""
build_info.py
Utilities for capturing build metadata: tool version, git state, and source versions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from bundlecraft import __version__


def get_bundlecraft_version() -> str:
    """Return the bundlecraft version string."""
    return __version__


def get_git_info(repo_path: Path | None = None) -> dict[str, Any] | None:
    """Capture git repository information.

    Returns None if not in a git repository or git is not available.
    Returns a dict with commit, branch, and dirty state if successful.

    Args:
        repo_path: Path to the repository (defaults to current directory)

    Returns:
        dict with keys: commit, branch, dirty
        None if not in a git repository
    """
    if repo_path is None:
        repo_path = Path.cwd()

    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        # Get commit hash
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None

        # Get branch name
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

        # Check for uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty = bool(status_result.stdout.strip()) if status_result.returncode == 0 else False

        return {"commit": commit, "branch": branch, "dirty": dirty}

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # git not available or timeout
        return None


def get_source_versions(
    staging_dirs: list[Path], repo_root: Path | None = None
) -> dict[str, str]:
    """Extract source versions from fetch provenance files.

    Looks for provenance.fetch.json files in staging directories and extracts
    version information from source metadata.

    Args:
        staging_dirs: List of staging directory paths
        repo_root: Repository root path for relative path resolution

    Returns:
        Dictionary mapping source names to version strings
    """
    import json

    source_versions: dict[str, str] = {}

    for staging_dir in staging_dirs:
        if not staging_dir.exists():
            continue

        # Check for provenance file
        provenance_file = staging_dir / "provenance.fetch.json"
        if not provenance_file.exists():
            continue

        try:
            provenance_data = json.loads(provenance_file.read_text(encoding="utf-8"))
            items = provenance_data.get("items", [])

            for item in items:
                name = item.get("name")
                origin = item.get("origin", {})

                # Try to extract version from various sources
                version = None

                # Check for explicit version in origin metadata
                if "version" in origin:
                    version = str(origin["version"])
                elif "metadata" in origin and isinstance(origin["metadata"], dict):
                    meta = origin["metadata"]
                    if "version" in meta:
                        version = str(meta["version"])
                    elif "date" in meta:
                        version = str(meta["date"])

                # For URL sources, try to extract version from the URL
                if not version and "url" in origin:
                    url = str(origin["url"])
                    # Look for version patterns in the URL
                    # Example: https://example.com/ca/2025-10-01/bundle.pem
                    import re

                    # Try to find date-like patterns (YYYY-MM-DD)
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", url)
                    if date_match:
                        version = date_match.group(1)
                    else:
                        # Try semantic version patterns (v1.2.3 or 1.2.3)
                        semver_match = re.search(r"v?(\d+\.\d+\.\d+)", url)
                        if semver_match:
                            version = semver_match.group(1)

                if name and version:
                    source_versions[name] = version

        except (json.JSONDecodeError, OSError):
            # Skip this provenance file if it can't be read
            continue

    return source_versions


def generate_build_info(
    repo_root: Path | None = None, staging_dirs: list[Path] | None = None
) -> dict[str, Any]:
    """Generate complete build_info metadata.

    Args:
        repo_root: Repository root path (for git detection)
        staging_dirs: List of staging directories (for source version extraction)

    Returns:
        Dictionary containing build_info with version, git, and source version data
    """
    build_info: dict[str, Any] = {
        "bundlecraft_version": get_bundlecraft_version(),
    }

    # Add git info if available
    git_info = get_git_info(repo_root)
    if git_info:
        build_info["git_commit"] = git_info.get("commit")
        build_info["git_branch"] = git_info.get("branch")
        build_info["git_dirty"] = git_info.get("dirty", False)

    # Add source versions if staging dirs provided
    if staging_dirs:
        source_versions = get_source_versions(staging_dirs, repo_root)
        if source_versions:
            build_info["source_versions"] = source_versions

    return build_info
