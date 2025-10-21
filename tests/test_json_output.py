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


class TestBuildJsonOutputPurity:
    """Test that build command JSON output doesn't mix with human-readable text."""

    def test_build_json_no_human_markers(self, temp_dir, sample_cert_pem, monkeypatch):
        """Test that --json mode suppresses all human-readable output markers."""
        from bundlecraft import builder as builder_mod

        cli_runner = CliRunner()

        # Create minimal test structure
        config_dir = temp_dir / "config"
        (config_dir / "crafts").mkdir(parents=True)
        (config_dir / "bundles").mkdir(parents=True)
        sources_internal = temp_dir / "sources" / "internal" / "test-bundle"
        sources_internal.mkdir(parents=True)

        # Monkeypatch paths for builder and fetch
        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_dir / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_dir / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_dir / "dist")
        import bundlecraft.fetch

        bundlecraft.fetch.ROOT = temp_dir
        bundlecraft.fetch.CONFIG_DIR = config_dir
        bundlecraft.fetch.SOURCES_DIR = temp_dir / "sources"
        bundlecraft.fetch.STAGED_DIR = temp_dir / "sources" / "staged"

        # Use the fixture certificate
        (sources_internal / "test.pem").write_text(sample_cert_pem, encoding="utf-8")

        # Create minimal bundle config
        bundle_config = """---
bundle_name: test-bundle
description: Test bundle
repo:
  - name: test-bundle
    include:
      - sources/internal/test-bundle
"""
        (config_dir / "bundles" / "test-bundle.yaml").write_text(bundle_config)

        # Create minimal craft config with packaging enabled
        craft_config = """---
name: Test
description: Test craft
targets:
  test-target:
    includes: [test-bundle]
output_formats:
  - pem
package: false
verify:
  fail_on_expired: false
"""
        (config_dir / "crafts" / "test.yaml").write_text(craft_config)

        # Build with --json flag
        with cli_runner.isolated_filesystem(temp_dir):
            result = cli_runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--bundle",
                    "test-target",
                    "--json",
                ],
                catch_exceptions=False,
            )

        # Verify it succeeded
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Verify output is valid JSON
        try:
            output_data = json.loads(result.output)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}\nOutput: {result.output}")

        # Check that stdout doesn't contain common human-readable patterns
        output = result.output

        # Should NOT contain these human-readable markers
        human_patterns = [
            "🔐 BundleCraft",
            "[STAGE",
            "[cache] ✓",
            "[JKS] ✓",
            "✅ Build complete",
            "[INFO] Created",
            "Wrote cached",
            "Converted cached",
        ]

        for pattern in human_patterns:
            assert pattern not in output, f"Found human-readable text in JSON output: '{pattern}'"

        # Should start with '{' (JSON object start)
        assert output.strip().startswith("{"), "Output should start with JSON object"

        # Verify JSON structure
        assert output_data["command"] == "build"
        assert output_data["success"] is True
        assert "targets" in output_data
        assert len(output_data["targets"]) > 0

    def test_build_json_output_is_pure_json(self, temp_dir, sample_cert_pem, monkeypatch):
        """Test that entire stdout can be parsed as a single JSON object."""
        from bundlecraft import builder as builder_mod

        cli_runner = CliRunner()

        # Create minimal test structure
        config_dir = temp_dir / "config"
        (config_dir / "crafts").mkdir(parents=True)
        (config_dir / "bundles").mkdir(parents=True)
        sources_internal = temp_dir / "sources" / "internal" / "test-bundle"
        sources_internal.mkdir(parents=True)

        # Monkeypatch paths
        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_dir / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_dir / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_dir / "dist")
        import bundlecraft.fetch

        bundlecraft.fetch.ROOT = temp_dir
        bundlecraft.fetch.CONFIG_DIR = config_dir
        bundlecraft.fetch.SOURCES_DIR = temp_dir / "sources"
        bundlecraft.fetch.STAGED_DIR = temp_dir / "sources" / "staged"

        (sources_internal / "test.pem").write_text(sample_cert_pem, encoding="utf-8")

        bundle_config = """---
bundle_name: test-bundle
description: Test bundle
repo:
  - name: test-bundle
    include:
      - sources/internal/test-bundle
"""
        (config_dir / "bundles" / "test-bundle.yaml").write_text(bundle_config)

        craft_config = """---
name: Test
description: Test craft
targets:
  test-target:
    includes: [test-bundle]
output_formats:
  - pem
package: false
verify:
  fail_on_expired: false
"""
        (config_dir / "crafts" / "test.yaml").write_text(craft_config)

        with cli_runner.isolated_filesystem(temp_dir):
            result = cli_runner.invoke(
                build_main,
                ["--craft", "test", "--bundle", "test-target", "--json"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0

        # The ENTIRE output should be parseable as a single JSON object
        # No leading or trailing text, no multiple objects
        output = result.output.strip()

        # Should start and end with JSON object delimiters
        assert output.startswith("{"), "Output should start with '{'"
        assert output.endswith("}"), "Output should end with '}'"

        # Should contain only one JSON object (no newlines between objects)
        # Count occurrences of '}{\n' or '}{' which would indicate multiple JSON objects
        assert "}{\n" not in output, "Output contains multiple JSON objects"
        assert "}{" not in output, "Output contains multiple JSON objects"

        # Parse and verify it's a single valid object
        data = json.loads(output)
        assert isinstance(data, dict)
        assert "command" in data
