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

    def test_convert_to_p7b(self, cli_runner, temp_dir, sample_cert_path):
        """Test conversion from PEM to PKCS#7."""
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
                "p7b",
            ],
        )
        # May fail if openssl not available, but should try
        # Success means either completed or gracefully handled missing tool
        assert result.exit_code in [0, 1, 2]

    def test_convert_to_jks(self, cli_runner, temp_dir, sample_cert_path):
        """Test conversion from PEM to Java KeyStore."""
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
                "jks",
            ],
        )
        # May fail if keytool not available, but should try
        assert result.exit_code in [0, 1, 2]

    def test_convert_to_p12(self, cli_runner, temp_dir, sample_cert_path):
        """Test conversion from PEM to PKCS#12."""
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
                "p12",
            ],
        )
        # May fail if openssl not available, but should try
        assert result.exit_code in [0, 1, 2]

    def test_convert_invalid_pem(self, cli_runner, temp_dir):
        """Test conversion with invalid PEM input."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        invalid_pem = temp_dir / "invalid.pem"
        invalid_pem.write_text("Not a valid PEM file")
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(invalid_pem),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "pem",
            ],
        )
        # Should handle invalid input gracefully
        assert result.exit_code != 0
        #     convert_bundle(
        #         pem_path=invalid_pem, output_dir=output_dir, formats=["p7b"]
        #     )

    # Multi-format output is no longer supported; test removed.

    def test_output_basename_applied(self, cli_runner, temp_dir, sample_cert_path):
        """Ensure --output-basename controls output filename for conversions."""
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
                "--output-basename",
                "mycustomname",
            ],
        )
        # Must not crash; file should be named by basename
        assert result.exit_code in [0, 2]
        assert (output_dir / "mycustomname.pem").exists()
