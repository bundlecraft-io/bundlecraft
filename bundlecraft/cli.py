#!/usr/bin/env python3
"""
🔐 BundleCraft CLI
Unified interface for building, verifying, and converting trust bundles.

Usage:
  bundlecraft <command> [options]

Subcommands:
  build      Build CA trust stores from sources and configs.
  verify     Verify integrity and consistency of built bundles.
  convert    Convert PEM bundles into alternate formats.
"""

import click

from bundlecraft import __version__
from bundlecraft.build_all import main as build_all_main
from bundlecraft.builder import main as build_main
from bundlecraft.converter import main as convert_main
from bundlecraft.differ import main as diff_main
from bundlecraft.fetch import main as fetch_main
from bundlecraft.verifier import main as verify_main


@click.group(
    help=(
        "🔐 BundleCraft - Modern PKI Trust Store Builder.\n\n"
        "Run `bundlecraft <command> --help` for command-specific options."
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__, prog_name="BundleCraft")
def cli():
    """Top-level CLI group for BundleCraft."""
    pass


# Attach subcommands from the individual modules
cli.add_command(build_main, name="build")
cli.add_command(build_all_main, name="build-all")
cli.add_command(verify_main, name="verify")
cli.add_command(convert_main, name="convert")
cli.add_command(diff_main, name="diff")
cli.add_command(fetch_main, name="fetch")


if __name__ == "__main__":
    cli()
