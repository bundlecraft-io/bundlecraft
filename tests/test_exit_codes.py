"""
Test suite for exit codes across all BundleCraft commands.

This test suite validates that all BundleCraft commands exit with the correct
standardized exit codes for various success and failure scenarios.

Exit code reference (from bundlecraft/helpers/exit_codes.py):
    0   - SUCCESS
    1   - GENERAL_ERROR
    2   - CONFIG_ERROR
    3   - CONFIG_NOT_FOUND
    10  - INPUT_ERROR
    11  - OUTPUT_ERROR
    20  - NETWORK_ERROR
    21  - AUTH_ERROR
    22  - FETCH_ERROR
    30  - VALIDATION_ERROR
    31  - EXPIRED_CERT
    32  - INVALID_CERT
    40  - BUILD_ERROR
    41  - CONVERSION_ERROR
    50  - DEPENDENCY_ERROR
    51  - PERMISSION_ERROR
"""

import pytest
from click.testing import CliRunner

from bundlecraft.builder import main as build_main
from bundlecraft.cli import cli
from bundlecraft.converter import main as convert_main
from bundlecraft.fetch import main as fetch_main
from bundlecraft.helpers.exit_codes import ExitCode, get_exit_code_description
from bundlecraft.verifier import main as verify_main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_pem_file(tmp_path):
    """Create a sample PEM certificate file for testing."""
    pem_content = """-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJAKHHCgVZU1UXMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl
c3RDQTAeFw0yNDAxMDEwMDAwMDBaFw0zNDAxMDEwMDAwMDBaMBExDzANBgNVBAMM
BnRlc3RDQTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEArKJi0kU5lFLYhKf6
b0FJYNGvVlJvFyf3oe0ZH0/6iQzKGq6l0L7BXlLlPvZxF5cEUVLLJdCYsLvHnZYj
Y8pTiLjQhXXc5kv5tLlC7Y3kRp9YQF3pQYH8p5V8hGLl0h3mFH8lQ8/w3mLG9Xh6
0/Vv9Ye5UvGQqF9YXU1P0KlJ8pkCAwEAATANBgkqhkiG9w0BAQsFAAOBgQBEZQ3P
9jKk6fVLfWZ8WdVvHhVZrEcPfPqFqP+7a9P3jqQvTKTzQxCLmHzXpZVxHqJTXLAo
O6lY9kU8xPmV5YPbYfUd1JHqYdQ0z8R5cH5vN5PpJ9R1L0vKvYq3pN5A9L5yQ+Hp
ZG3L1YpQpZVLpLvFzQ5R2H9K5PqYvFmZ5KVHAA==
-----END CERTIFICATE-----
"""
    pem_file = tmp_path / "test-cert.pem"
    pem_file.write_text(pem_content)
    return pem_file


@pytest.fixture
def valid_bundle_config(tmp_path):
    """Create a valid bundle configuration file."""
    config_content = """
name: test-bundle
description: Test bundle for exit code testing
repos:
  test-repo:
    path: ./test-certs
"""
    config_file = tmp_path / "bundle.yaml"
    config_file.write_text(config_content)

    # Create the repo directory with a cert
    repo_dir = tmp_path / "test-certs"
    repo_dir.mkdir()
    cert_file = repo_dir / "test.pem"
    cert_file.write_text(
        """-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJAKHHCgVZU1UXMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl
c3RDQTAeFw0yNDAxMDEwMDAwMDBaFw0zNDAxMDEwMDAwMDBaMBExDzANBgNVBAMM
BnRlc3RDQTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEArKJi0kU5lFLYhKf6
b0FJYNGvVlJvFyf3oe0ZH0/6iQzKGq6l0L7BXlLlPvZxF5cEUVLLJdCYsLvHnZYj
Y8pTiLjQhXXc5kv5tLlC7Y3kRp9YQF3pQYH8p5V8hGLl0h3mFH8lQ8/w3mLG9Xh6
0/Vv9Ye5UvGQqF9YXU1P0KlJ8pkCAwEAATANBgkqhkiG9w0BAQsFAAOBgQBEZQ3P
9jKk6fVLfWZ8WdVvHhVZrEcPfPqFqP+7a9P3jqQvTKTzQxCLmHzXpZVxHqJTXLAo
O6lY9kU8xPmV5YPbYfUd1JHqYdQ0z8R5cH5vN5PpJ9R1L0vKvYq3pN5A9L5yQ+Hp
ZG3L1YpQpZVLpLvFzQ5R2H9K5PqYvFmZ5KVHAA==
-----END CERTIFICATE-----
"""
    )
    return config_file


class TestExitCodeConstants:
    """Test that exit code constants are properly defined."""

    def test_exit_code_values(self):
        """Verify all exit code constants have expected values."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.GENERAL_ERROR == 1
        assert ExitCode.CONFIG_ERROR == 2
        assert ExitCode.CONFIG_NOT_FOUND == 3
        assert ExitCode.INPUT_ERROR == 10
        assert ExitCode.OUTPUT_ERROR == 11
        assert ExitCode.NETWORK_ERROR == 20
        assert ExitCode.AUTH_ERROR == 21
        assert ExitCode.FETCH_ERROR == 22
        assert ExitCode.VALIDATION_ERROR == 30
        assert ExitCode.EXPIRED_CERT == 31
        assert ExitCode.INVALID_CERT == 32
        assert ExitCode.BUILD_ERROR == 40
        assert ExitCode.CONVERSION_ERROR == 41
        assert ExitCode.DEPENDENCY_ERROR == 50
        assert ExitCode.PERMISSION_ERROR == 51

    def test_exit_code_descriptions(self):
        """Verify that all exit codes have descriptions."""
        assert get_exit_code_description(ExitCode.SUCCESS) == "Success"
        assert get_exit_code_description(ExitCode.CONFIG_ERROR) == "Configuration error"
        assert get_exit_code_description(ExitCode.EXPIRED_CERT) == "Expired certificate"
        assert "Unknown" in get_exit_code_description(999)


class TestBuildCommandExitCodes:
    """Test exit codes for the build command."""

    def test_build_missing_config(self, cli_runner, tmp_path):
        """Test build command with missing config file."""
        result = cli_runner.invoke(
            build_main,
            [
                "--env-config-file",
                str(tmp_path / "nonexistent.yaml"),
            ],
        )
        assert result.exit_code == ExitCode.CONFIG_ERROR

    def test_build_invalid_config(self, cli_runner, tmp_path):
        """Test build command with invalid config file."""
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content:")

        result = cli_runner.invoke(
            build_main,
            [
                "--env-config-file",
                str(invalid_config),
            ],
        )
        assert result.exit_code == ExitCode.CONFIG_ERROR


class TestFetchCommandExitCodes:
    """Test exit codes for the fetch command."""

    def test_fetch_missing_config(self, cli_runner, tmp_path):
        """Test fetch command with missing config file."""
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(tmp_path / "nonexistent.yaml"),
            ],
        )
        assert result.exit_code == ExitCode.CONFIG_ERROR

    def test_fetch_invalid_config(self, cli_runner, tmp_path):
        """Test fetch command with invalid config file."""
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content:")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(invalid_config),
            ],
        )
        assert result.exit_code == ExitCode.FETCH_ERROR


class TestConverterCommandExitCodes:
    """Test exit codes for the converter command."""

    def test_convert_missing_input(self, cli_runner, tmp_path):
        """Test convert command with missing input file.

        Note: Click validates --input with exists=True, so it exits with code 2
        before our code runs. This is acceptable as it's a usage error.
        """
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(tmp_path / "nonexistent.pem"),
                "--output-dir",
                str(tmp_path / "output"),
                "--output-format",
                "p7b",
            ],
        )
        # Click's path validation exits with 2 (usage error)
        assert result.exit_code == 2

    def test_convert_invalid_output_dir(self, cli_runner, sample_pem_file, tmp_path):
        """Test convert command with invalid output directory."""
        # Create a file where a directory should be
        invalid_dir = tmp_path / "invalid_dir"
        invalid_dir.write_text("this is a file, not a directory")

        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_pem_file),
                "--output-dir",
                str(invalid_dir / "subdir"),
                "--output-format",
                "p7b",
            ],
        )
        # This should fail with an error (could be OUTPUT_ERROR or CONVERSION_ERROR)
        assert result.exit_code != ExitCode.SUCCESS

    def test_convert_success_dry_run(self, cli_runner, sample_pem_file, tmp_path):
        """Test convert command succeeds with dry-run."""
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_pem_file),
                "--output-dir",
                str(tmp_path / "output"),
                "--output-format",
                "p7b",
                "--dry-run",
            ],
        )
        assert result.exit_code == ExitCode.SUCCESS


class TestVerifierCommandExitCodes:
    """Test exit codes for the verifier command."""

    def test_verify_missing_target(self, cli_runner, tmp_path):
        """Test verify command with missing target."""
        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(tmp_path / "nonexistent"),
            ],
        )
        # Should fail because target doesn't exist
        assert result.exit_code != ExitCode.SUCCESS

    def test_verify_success_dry_run(self, cli_runner, sample_pem_file):
        """Test verify command succeeds with dry-run on valid file."""
        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(sample_pem_file),
                "--dry-run",
            ],
        )
        # Dry run should succeed
        assert result.exit_code == ExitCode.SUCCESS


class TestCLIIntegrationExitCodes:
    """Test exit codes through the main CLI interface."""

    def test_cli_help_success(self, cli_runner):
        """Test that CLI --help exits with success."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == ExitCode.SUCCESS

    def test_cli_version_success(self, cli_runner):
        """Test that CLI --version exits with success."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == ExitCode.SUCCESS

    def test_build_help_success(self, cli_runner):
        """Test that build --help exits with success."""
        result = cli_runner.invoke(cli, ["build", "--help"])
        assert result.exit_code == ExitCode.SUCCESS

    def test_verify_help_success(self, cli_runner):
        """Test that verify --help exits with success."""
        result = cli_runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == ExitCode.SUCCESS

    def test_convert_help_success(self, cli_runner):
        """Test that convert --help exits with success."""
        result = cli_runner.invoke(cli, ["convert", "--help"])
        assert result.exit_code == ExitCode.SUCCESS

    def test_fetch_help_success(self, cli_runner):
        """Test that fetch --help exits with success."""
        result = cli_runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == ExitCode.SUCCESS

    def test_diff_help_success(self, cli_runner):
        """Test that diff --help exits with success."""
        result = cli_runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == ExitCode.SUCCESS


class TestExitCodeConsistency:
    """Test exit code consistency across different scenarios."""

    def test_no_magic_numbers(self):
        """Verify that all defined exit codes are valid integers."""
        exit_codes = [
            ExitCode.SUCCESS,
            ExitCode.GENERAL_ERROR,
            ExitCode.CONFIG_ERROR,
            ExitCode.CONFIG_NOT_FOUND,
            ExitCode.INPUT_ERROR,
            ExitCode.OUTPUT_ERROR,
            ExitCode.NETWORK_ERROR,
            ExitCode.AUTH_ERROR,
            ExitCode.FETCH_ERROR,
            ExitCode.VALIDATION_ERROR,
            ExitCode.EXPIRED_CERT,
            ExitCode.INVALID_CERT,
            ExitCode.BUILD_ERROR,
            ExitCode.CONVERSION_ERROR,
            ExitCode.DEPENDENCY_ERROR,
            ExitCode.PERMISSION_ERROR,
        ]

        for code in exit_codes:
            assert isinstance(code, int)
            assert 0 <= code <= 255  # Valid exit code range

    def test_exit_codes_unique(self):
        """Verify that all exit codes are unique."""
        exit_codes = [
            ExitCode.SUCCESS,
            ExitCode.GENERAL_ERROR,
            ExitCode.CONFIG_ERROR,
            ExitCode.CONFIG_NOT_FOUND,
            ExitCode.INPUT_ERROR,
            ExitCode.OUTPUT_ERROR,
            ExitCode.NETWORK_ERROR,
            ExitCode.AUTH_ERROR,
            ExitCode.FETCH_ERROR,
            ExitCode.VALIDATION_ERROR,
            ExitCode.EXPIRED_CERT,
            ExitCode.INVALID_CERT,
            ExitCode.BUILD_ERROR,
            ExitCode.CONVERSION_ERROR,
            ExitCode.DEPENDENCY_ERROR,
            ExitCode.PERMISSION_ERROR,
        ]

        # Check that all codes are unique
        assert len(exit_codes) == len(set(exit_codes))

    def test_exit_code_ranges(self):
        """Verify that exit codes follow the documented ranges."""
        # Success
        assert ExitCode.SUCCESS == 0

        # General errors (1)
        assert 1 <= ExitCode.GENERAL_ERROR <= 1

        # Configuration errors (2-9)
        assert 2 <= ExitCode.CONFIG_ERROR <= 9
        assert 2 <= ExitCode.CONFIG_NOT_FOUND <= 9

        # Input/Output errors (10-19)
        assert 10 <= ExitCode.INPUT_ERROR <= 19
        assert 10 <= ExitCode.OUTPUT_ERROR <= 19

        # Network/fetch errors (20-29)
        assert 20 <= ExitCode.NETWORK_ERROR <= 29
        assert 20 <= ExitCode.AUTH_ERROR <= 29
        assert 20 <= ExitCode.FETCH_ERROR <= 29

        # Validation errors (30-39)
        assert 30 <= ExitCode.VALIDATION_ERROR <= 39
        assert 30 <= ExitCode.EXPIRED_CERT <= 39
        assert 30 <= ExitCode.INVALID_CERT <= 39

        # Build/conversion errors (40-49)
        assert 40 <= ExitCode.BUILD_ERROR <= 49
        assert 40 <= ExitCode.CONVERSION_ERROR <= 49

        # Runtime errors (50-59)
        assert 50 <= ExitCode.DEPENDENCY_ERROR <= 59
        assert 50 <= ExitCode.PERMISSION_ERROR <= 59
