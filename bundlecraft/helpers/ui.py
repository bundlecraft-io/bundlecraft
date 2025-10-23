#!/usr/bin/env python3
"""
ui.py
Shared UI helpers for consistent CLI output formatting across BundleCraft tools.

Currently provides a unified banner printer with consistent icon, color, and
underline length that matches the visible title text.
"""
from __future__ import annotations

import click


def print_banner(tool_name: str, color: str = "cyan") -> None:
    """Print a standardized cyan banner for BundleCraft CLIs.

    Example:
        >>> print_banner("Builder")

        (prints)
        \n🔐 BundleCraft Builder
        ---------------------

    Args:
        tool_name: The component/tool display name (e.g., "Builder", "Fetcher").
        color: Click color for the banner text (default: "cyan").
    """
    title = f"BundleCraft {tool_name}"
    # Leading newline for visual spacing before the banner
    click.secho(f"\n🔐 {title}", fg=color)
    click.secho("-" * len(title), fg=color)
