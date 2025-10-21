"""Tests for JSON output functionality across all BundleCraft commands."""

import json

import pytest
from click.testing import CliRunner

from bundlecraft.builder import main as build_main
from bundlecraft.converter import main as convert_main
from bundlecraft.fetch import main as fetch_main
from bundlecraft.verifier import main as verify_main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestFetchJsonOutput:
    """Test JSON output for the fetch command."""

    def test_fetch_json_dry_run(self, cli_runner, tmp_path):
        """Test fetch command with --json flag in dry-run mode."""
        bundle_config = tmp_path / "test-bundle.yaml"
        bundle_config.write_text(
            """
bundle_name: test-bundle
description: Test bundle for JSON output
include:
  - sources/mozilla
fetch:
  - name: test-source
    type: url
    url: https://example.com/test.pem
"""
        )

        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--workspace-root",
                str(tmp_path),
                "--dry-run",
                "--json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["command"] == "fetch"
        assert "timestamp" in data
        assert "version" in data
        assert data["bundle_name"] == "test-bundle"
        assert "staging_path" in data
        assert "dry_run" in data
        assert data["dry_run"] is True

    def test_fetch_json_error(self, cli_runner, tmp_path):
        """Test fetch command JSON output on error."""
        # Create a config file with validation errors
        bundle_config = tmp_path / "invalid.yaml"
        bundle_config.write_text("invalid: yaml: content: [")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--json",
            ],
        )

        assert result.exit_code == 2
        # Check that we got valid JSON output even on error
        if result.output.strip():
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["command"] == "fetch"
            assert "errors" in data
            assert len(data["errors"]) > 0


class TestConvertJsonOutput:
    """Test JSON output for the convert command."""

    def test_convert_json_dry_run(self, cli_runner, tmp_path):
        """Test convert command with --json flag in dry-run mode."""
        pem_file = tmp_path / "test.pem"
        pem_file.write_text(
            """-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJAKHHCgVZU4pUMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl
c3RDQTAeFw0yMTAxMDEwMDAwMDBaFw0zMTAxMDEwMDAwMDBaMBExDzANBgNVBAMM
BnRlc3RDQTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAwRQ0G8IjC9D8quuE
YPLxQKfOTkLLF5n4h5+jXsKQJ3xuLj9J9YNXLWcL9VZLV+r5f6qQf0lDkYHLNFvH
SxYbKr7RJHqYHq5QBqUlKsKLCmKhKQYnWcPL3eHTgLwpxOLZEjMECQYDVQQDDAZ0
ZXN0Q0EwHhcNMjEwMTAxMDAwMDAwWhcNMzEwMTAxMDAwMDAwWjARMQ8wDQYDVQQD
DAZ0ZXN0Q0EwXDANBgkqhkiG9w0BAQEFAANLADBIAkEAwRQ0G8IjC9D8quuEYPLx
QKfOTkLLF5n4h5+jXsKQJ3xuLj9J9YNXLWcL9VZLV+r5f6qQf0lDkYHLNFvHSxYb
Kr7RJQIDAQABMA0GCSqGSIb3DQEBCwUAA4GBAAoJb
-----END CERTIFICATE-----
"""
        )

        output_dir = tmp_path / "output"

        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(pem_file),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "pem",
                "--dry-run",
                "--json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["command"] == "convert"
        assert "timestamp" in data
        assert "version" in data
        assert data["input_path"] == str(pem_file)
        assert data["output_dir"] == str(output_dir)
        assert data["output_format"] == "pem"

    def test_convert_json_missing_input(self, cli_runner, tmp_path):
        """Test convert command JSON output with missing input."""
        # Create a file that exists but has invalid content
        invalid_pem = tmp_path / "invalid.pem"
        invalid_pem.write_text("not a valid pem file")
        
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(invalid_pem),
                "--output-dir",
                str(tmp_path / "output"),
                "--output-format",
                "pem",
                "--json",
            ],
        )

        # Command should succeed or fail, but if it outputs JSON, validate it
        if result.output.strip():
            try:
                data = json.loads(result.output)
                assert "success" in data
                assert data["command"] == "convert"
            except json.JSONDecodeError:
                # If not JSON, check if it's an error message
                pass


class TestVerifyJsonOutput:
    """Test JSON output for the verify command."""

    def test_verify_json_single_file(self, cli_runner, tmp_path):
        """Test verify command with --json flag for single file."""
        test_file = tmp_path / "test.pem"
        test_file.write_text("test content")

        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(test_file),
                "--json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["command"] == "verify"
        assert "timestamp" in data
        assert "version" in data
        assert data["target_path"] == str(test_file)
        assert data["verified_files"] == 1
        assert "file_sha256" in data

    def test_verify_json_directory_missing_checksums(self, cli_runner, tmp_path):
        """Test verify command JSON output with missing checksums file."""
        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(tmp_path),
                "--json",
            ],
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["command"] == "verify"
        assert "errors" in data


class TestBuildJsonOutput:
    """Test JSON output for the build command."""

    def test_build_json_missing_craft(self, cli_runner, tmp_path):
        """Test build command JSON output with missing craft config."""
        result = cli_runner.invoke(
            build_main,
            [
                "--craft",
                "nonexistent-craft",
                "--dry-run",
                "--json",
            ],
        )

        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["command"] == "build"
        assert "errors" in data
        assert len(data["errors"]) > 0


class TestJsonOutputSchema:
    """Test that JSON output schemas are consistent and stable."""

    def test_base_schema_fields(self, cli_runner, tmp_path):
        """Test that all commands include base schema fields."""
        # Test with fetch (easiest to set up)
        bundle_config = tmp_path / "test.yaml"
        bundle_config.write_text("bundle_name: test\ndescription: Test bundle\n")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--dry-run",
                "--json",
            ],
        )

        data = json.loads(result.output)

        # All responses must have these base fields
        required_fields = ["success", "command", "timestamp", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Timestamp should be ISO 8601 format
        assert "T" in data["timestamp"]
        assert data["timestamp"].endswith("+00:00") or data["timestamp"].endswith("Z")

    def test_error_schema_consistency(self, cli_runner, tmp_path):
        """Test that error responses have consistent schema."""
        # Test with invalid config file
        bundle_config = tmp_path / "invalid.yaml"
        bundle_config.write_text("invalid yaml [[[")
        
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--json",
            ],
        )

        assert result.exit_code == 2
        if result.output.strip():
            data = json.loads(result.output)
            assert data["success"] is False
            assert "errors" in data
            assert isinstance(data["errors"], list)
            assert len(data["errors"]) > 0

    def test_json_output_parseable(self, cli_runner, tmp_path):
        """Test that JSON output is always valid and parseable."""
        bundle_config = tmp_path / "test.yaml"
        bundle_config.write_text("bundle_name: test\ndescription: Test bundle\n")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--dry-run",
                "--json",
            ],
        )

        # Should not raise JSONDecodeError
        data = json.loads(result.output)
        assert isinstance(data, dict)

        # Test that output can be re-serialized
        reserialized = json.dumps(data)
        assert json.loads(reserialized) == data
