#!/usr/bin/env python3
"""
🔐 BundleCraft CLI
Unified interface for building, verifying, and converting trust bundles.

Subcommands:
  build      Build CA trust stores from sources and configs.
  verify     Verify integrity and consistency of built bundles.
  convert    Convert PEM bundles into alternate formats.

Usage:
  bundlecraft <command> [options]
"""

import click
from bundlecraft.builder import main as build_main
from bundlecraft.verifier import main as verify_main
from bundlecraft.converter import main as convert_main

@click.group(help="🔐 BundleCraft — build, convert, and verify CA trust bundles.")
def cli():
    pass

# Attach subcommands
cli.add_command(build_main, name="build")
cli.add_command(verify_main, name="verify")
cli.add_command(convert_main, name="convert")

if __name__ == "__main__":
    cli()
