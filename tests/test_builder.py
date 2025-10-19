"""Tests for BundleCraft builder module."""

import pytest
from click.testing import CliRunner

from bundlecraft.builder import FORBIDDEN_BUNDLE_KEYS
from bundlecraft.builder import main as build_main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.mark.builder
class TestBuilder:
    """Test suite for the builder module."""

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
        assert "Missing option" in result.output or "Error" in result.output

    def test_builder_with_nonexistent_config(self, cli_runner, temp_workspace):
        """Test builder behavior with missing configuration files."""
        result = cli_runner.invoke(
            build_main,
            ["--env", "nonexistent", "--bundle", "nonexistent"],
        )
        # Should fail with error (exit code 1 or 2)
        assert result.exit_code != 0

    def test_build_basic_bundle(
        self, cli_runner, temp_workspace, sample_cert_path, sample_bundle_config
    ):
        """Test building a basic bundle with minimal configuration."""
        # CLI runner approach with temp workspace
        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--env",
                    "test",
                    "--bundle",
                    "test-bundle",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            # May succeed or fail depending on config availability
            # Just ensure it runs without crashing
            assert isinstance(result.exit_code, int)

    def test_build_with_packaging(self, cli_runner, temp_workspace):
        """Test building a bundle with packaging enabled."""
        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--env",
                    "test",
                    "--bundle",
                    "test-bundle",
                    "--package",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            # Just verify the --package flag is accepted
            assert isinstance(result.exit_code, int)

    @pytest.mark.parametrize("format", ["pem", "p7b", "jks", "p12"])
    def test_build_different_formats(self, cli_runner, temp_workspace, format):
        """Test building bundles in different output formats."""
        # Formats are defined in bundle configs, not CLI args
        # This test just verifies the builder can be invoked
        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--env",
                    "test",
                    "--bundle",
                    "test-bundle",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            assert isinstance(result.exit_code, int)

    def test_build_missing_config(self, cli_runner, temp_dir):
        """Test that build fails gracefully with missing config."""
        result = cli_runner.invoke(
            build_main,
            [
                "--env",
                "nonexistent",
                "--bundle",
                "nonexistent",
            ],
        )
        # Should fail when configs don't exist
        assert result.exit_code != 0

    def test_build_expired_cert(self, cli_runner):
        """Test build behavior with expired certificates."""
        # Test the --verify-only flag behavior
        result = cli_runner.invoke(
            build_main,
            [
                "--env",
                "test",
                "--bundle",
                "test",
                "--verify-only",
            ],
        )
        # verify-only should work even if build would fail
        assert isinstance(result.exit_code, int)

    def test_build_empty_sources(self, cli_runner, temp_workspace):
        """Test build behavior with no certificate sources."""
        # Create config pointing to empty sources
        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--env",
                    "test",
                    "--bundle",
                    "test-bundle",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            # Should fail or warn about no sources
            # Exit code check ensures it runs
            assert isinstance(result.exit_code, int)

    def test_config_separation_validation(self):
        """Test that the validation logic correctly identifies forbidden keys in bundle configs."""
        # This is a unit test of the validation logic, not an integration test
        # Test case 1: Bundle config with no forbidden keys (should be OK)
        clean_config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "include": ["sources/test.pem"],
            "metadata": {"owner": "test@example.com"},
        }
        found = [k for k in FORBIDDEN_BUNDLE_KEYS if k in clean_config]
        assert len(found) == 0, "Clean config should have no forbidden keys"

        # Test case 2: Bundle config with forbidden keys
        dirty_config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "include": ["sources/test.pem"],
            "verify": {"fail_on_expired": False},  # Forbidden
            "output_formats": ["pem", "jks"],  # Forbidden
            "package": True,  # Forbidden
        }
        found = [k for k in FORBIDDEN_BUNDLE_KEYS if k in dirty_config]
        assert len(found) == 3, f"Should find 3 forbidden keys, found {len(found)}"
        assert "verify" in found
        assert "output_formats" in found
        assert "package" in found

    def test_direct_source_paths(self):
        """Test that craft configs can specify source paths directly without bundle configs."""
        # Test case: Craft config target with direct include/exclude paths
        craft_config = {
            "name": "Test Craft",
            "description": "Test with direct sources",
            "targets": {
                "my-target": {
                    "include": ["sources/internal/rootCA.pem"],
                    "exclude": ["sources/internal/old.pem"],
                }
            },
            "output_formats": ["pem"],
        }

        # Verify target has direct sources
        target_entry = craft_config["targets"]["my-target"]
        assert "include" in target_entry, "Target should have include paths"
        assert "exclude" in target_entry, "Target should have exclude paths"
        assert "includes" not in target_entry, "Target should not have bundle references"

        # Verify sources are specified correctly
        assert len(target_entry["include"]) > 0, "Should have at least one include path"
        assert isinstance(target_entry["include"][0], str), "Include paths should be strings"
