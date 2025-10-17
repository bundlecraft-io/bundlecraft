"""Tests for BundleCraft builder module."""

import pytest
from click.testing import CliRunner

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

    def test_build_basic_bundle(self, temp_workspace, sample_cert_path, sample_bundle_config):
        """Test building a basic bundle with minimal configuration."""
        pytest.skip("TODO: Refactor to use CLI runner instead of build_trust_store function")
        # result = build_trust_store(
        #     env="test",
        #     bundle="test-bundle",
        #     workspace=temp_workspace,
        #     package=False,
        # )
        # assert result.success
        # assert (temp_workspace / "build/test/test-bundle/ca-trust.pem").exists()
        # assert (temp_workspace / "build/test/test-bundle/manifest.json").exists()

    def test_build_with_packaging(self, temp_workspace, sample_cert_path, sample_bundle_config):
        """Test building a bundle with packaging enabled."""
        pytest.skip("TODO: Refactor to use CLI runner instead of build_trust_store function")
        # result = build_trust_store(
        #     env="test",
        #     bundle="test-bundle",
        #     workspace=temp_workspace,
        #     package=True,
        # )
        # assert result.success
        # assert (temp_workspace / "build/test/test-bundle/package.tar.gz").exists()

    @pytest.mark.parametrize("format", ["p7b", "jks", "p12"])
    def test_build_different_formats(
        self, temp_workspace, sample_cert_path, sample_bundle_config, format
    ):
        """Test building bundles in different output formats."""
        pytest.skip("TODO: Refactor to use CLI runner instead of build_trust_store function")
        # result = build_trust_store(
        #     env="test",
        #     bundle="test-bundle",
        #     workspace=temp_workspace,
        #     formats=[format],
        # )
        # assert result.success
        # assert (
        #     temp_workspace / f"build/test/test-bundle/ca-trust.{format}"
        # ).exists()

    def test_build_missing_config(self, temp_workspace):
        """Test that build fails gracefully with missing config."""
        pytest.skip("TODO: Refactor to use CLI runner instead of build_trust_store function")
        # with pytest.raises(FileNotFoundError):
        #     build_trust_store(
        #         env="nonexistent",
        #         bundle="nonexistent",
        #         workspace=temp_workspace,
        #     )

    def test_build_expired_cert(self, temp_workspace, sample_cert_path, sample_bundle_config):
        """Test build behavior with expired certificates."""
        # This test needs a known-expired certificate in test data
        pass  # TODO: Implement with expired cert fixture

    def test_build_empty_sources(self, temp_workspace, sample_bundle_config):
        """Test build behavior with no certificate sources."""
        pytest.skip("TODO: Refactor to use CLI runner instead of build_trust_store function")
        # Create empty sources directory
        # (temp_workspace / "sources/internal").mkdir(parents=True, exist_ok=True)
        # with pytest.raises(ValueError) as exc_info:
        #     build_trust_store(
        #         env="test",
        #         bundle="test-bundle",
        #         workspace=temp_workspace,
        #     )
        # assert "No certificate sources found" in str(exc_info.value)
