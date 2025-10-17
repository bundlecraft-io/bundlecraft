"""Tests for BundleCraft command modules (builder, converter, verifier)."""

import pytest
from click.testing import CliRunner

from bundlecraft.builder import main as build_main
from bundlecraft.converter import main as convert_main
from bundlecraft.verifier import main as verify_main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.mark.builder
class TestBuilder:
    """Test suite for the builder command."""

    def test_builder_help(self, cli_runner):
        """Test that builder --help works."""
        result = cli_runner.invoke(build_main, ["--help"])
        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--bundle" in result.output

    def test_builder_missing_required_args(self, cli_runner):
        """Test that builder fails without required arguments."""
        result = cli_runner.invoke(build_main, [])
        assert result.exit_code != 0


@pytest.mark.converter
class TestConverter:
    """Test suite for the converter command."""

    def test_converter_help(self, cli_runner):
        """Test that converter --help works."""
        result = cli_runner.invoke(convert_main, ["--help"])
        assert result.exit_code == 0
        assert "--pem-file" in result.output
        assert "--output-dir" in result.output

    def test_converter_missing_required_args(self, cli_runner):
        """Test that converter fails without required arguments."""
        result = cli_runner.invoke(convert_main, [])
        assert result.exit_code != 0

    def test_converter_with_sample_pem(self, cli_runner, temp_dir, sample_cert_path):
        """Test converter with a valid sample PEM file."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        result = cli_runner.invoke(
            convert_main,
            [
                "--pem-file",
                str(sample_cert_path),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "p7b",
            ],
        )

        # Should show converter output
        assert "Converter" in result.output


@pytest.mark.verifier
class TestVerifier:
    """Test suite for the verifier command."""

    def test_verifier_help(self, cli_runner):
        """Test that verifier --help works."""
        result = cli_runner.invoke(verify_main, ["--help"])
        assert result.exit_code == 0
        assert "--target" in result.output

    def test_verifier_missing_required_args(self, cli_runner):
        """Test that verifier fails without required arguments."""
        result = cli_runner.invoke(verify_main, [])
        assert result.exit_code != 0

    def test_verifier_with_sample_file(self, cli_runner, sample_cert_path):
        """Test verifier with a sample certificate file."""
        result = cli_runner.invoke(verify_main, ["--target", str(sample_cert_path)])
        # Should run and show verifier output
        assert "Verifier" in result.output or "SHA256" in result.output
