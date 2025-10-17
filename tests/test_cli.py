"""Tests for BundleCraft CLI module."""

import pytest
from click.testing import CliRunner

from bundlecraft.cli import cli


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestCLI:
    """Test suite for the main CLI interface."""

    def test_cli_help(self, cli_runner):
        """Test that --help output contains expected commands."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "verify" in result.output
        assert "convert" in result.output
        assert "fetch" in result.output

    def test_cli_version(self, cli_runner):
        """Test that --version outputs version string."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "BundleCraft" in result.output

    @pytest.mark.parametrize("command", ["build", "verify", "convert", "fetch"])
    def test_subcommand_help(self, cli_runner, command):
        """Test that each subcommand's --help output works."""
        result = cli_runner.invoke(cli, [command, "--help"])
        assert result.exit_code == 0
