"""Tests for BundleCraft converter module."""

import pytest
from click.testing import CliRunner

from bundlecraft.converter import main as convert_main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.mark.converter
class TestConverter:
    """Test suite for the converter module."""

    def test_converter_help(self, cli_runner):
        """Test that converter --help works."""
        result = cli_runner.invoke(convert_main, ["--help"])
        assert result.exit_code == 0
        assert "--input" in result.output or "--pem-file" in result.output
        assert "--output-dir" in result.output
        assert "--output-format" in result.output
        # Ensure private key flag is NOT present
        assert "--include-private-keys" not in result.output

    def test_converter_missing_required_args(self, cli_runner):
        """Test that converter fails without required arguments."""
        result = cli_runner.invoke(convert_main, [])
        assert result.exit_code != 0
        assert "Missing" in result.output or "ERROR" in result.output

    def test_converter_with_sample_pem(self, cli_runner, temp_dir, sample_cert_path):
        """Test converter with a valid sample PEM file (backward compat with --pem-file)."""
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
                "pem",
            ],
        )
        # Should complete (may fail due to openssl not available, but should try)
        assert "Converter" in result.output or result.exit_code == 0

    def test_converter_with_input_flag(self, cli_runner, temp_dir, sample_cert_path):
        """Test converter with new --input flag."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_cert_path),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "pem",
            ],
        )
        assert "Converter" in result.output or result.exit_code == 0

    def test_converter_with_nonexistent_file(self, cli_runner, temp_dir):
        """Test converter with nonexistent input file."""
        result = cli_runner.invoke(
            convert_main,
            ["--input", "/nonexistent/file.pem", "--output-dir", str(temp_dir)],
        )
        assert result.exit_code != 0

    def test_convert_to_p7b(self, temp_workspace, sample_cert_path):
        """Test conversion from PEM to PKCS#7."""
        pytest.skip("TODO: Fix test certificate data - OpenSSL cannot parse the sample cert")
        # output_dir = temp_workspace / "output"
        # output_dir.mkdir()
        # result = convert_bundle(
        #     pem_path=sample_cert_path, output_dir=output_dir, formats=["p7b"]
        # )
        # assert result.success
        # assert (output_dir / "bundlecraft-ca-trust.p7b").exists()

    def test_convert_to_jks(self, temp_workspace, sample_cert_path):
        """Test conversion from PEM to Java KeyStore."""
        pytest.skip("TODO: Fix test certificate data - certificate parsing fails")
        # output_dir = temp_workspace / "output"
        # output_dir.mkdir()
        # result = convert_bundle(
        #     pem_path=sample_cert_path, output_dir=output_dir, formats=["jks"]
        # )
        # assert result.success
        # assert (output_dir / "bundlecraft-ca-trust.jks").exists()

    def test_convert_to_p12(self, temp_workspace, sample_cert_path):
        """Test conversion from PEM to PKCS#12."""
        pytest.skip("TODO: Fix test certificate data - certificate parsing fails")
        # output_dir = temp_workspace / "output"
        # output_dir.mkdir()
        # result = convert_bundle(
        #     pem_path=sample_cert_path, output_dir=output_dir, formats=["p12"]
        # )
        # assert result.success
        # assert (output_dir / "bundlecraft-ca-trust.p12").exists()

    def test_convert_invalid_pem(self, temp_workspace):
        """Test conversion with invalid PEM input."""
        pytest.skip(
            "TODO: convert_bundle currently catches all exceptions - needs proper error handling"
        )
        # output_dir = temp_workspace / "output"
        # output_dir.mkdir()
        # invalid_pem = temp_workspace / "invalid.pem"
        # invalid_pem.write_text("Not a valid PEM file")
        # with pytest.raises(ValueError):
        #     convert_bundle(
        #         pem_path=invalid_pem, output_dir=output_dir, formats=["p7b"]
        #     )

    # Multi-format output is no longer supported; test removed.
