"""Tests for BundleCraft verifier module."""

import pytest
from click.testing import CliRunner

from bundlecraft.verifier import main as verify_main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.mark.verifier
class TestVerifier:
    """Test suite for the verifier module."""

    def test_verifier_help(self, cli_runner):
        """Test that verifier --help works."""
        result = cli_runner.invoke(verify_main, ["--help"])
        assert result.exit_code == 0
        assert "--target" in result.output

    def test_verifier_missing_required_args(self, cli_runner):
        """Test that verifier fails without required arguments."""
        result = cli_runner.invoke(verify_main, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

    def test_verifier_with_nonexistent_path(self, cli_runner):
        """Test verifier with nonexistent target path."""
        result = cli_runner.invoke(verify_main, ["--target", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_verify_valid_bundle(self, temp_workspace):
        """Test verification of a valid bundle."""
        pytest.skip("TODO: Refactor to use verify_directory or CLI runner")
        # bundle_dir = temp_workspace / "build/test/test-bundle"
        # bundle_dir.mkdir(parents=True)
        # # Create test files
        # (bundle_dir / "ca-trust.pem").write_text(
        #     "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
        # )  # PEM block, no UTC string needed
        # (bundle_dir / "manifest.json").write_text("{}")
        # result = verify_bundle(bundle_dir)
        # assert result.success
        # assert result.warnings == []

    def test_verify_missing_files(self, temp_workspace):
        """Test verification of a bundle with missing files."""
        pytest.skip("TODO: Refactor to use verify_directory or CLI runner")
        # bundle_dir = temp_workspace / "build/test/test-bundle"
        # bundle_dir.mkdir(parents=True)
        # with pytest.raises(FileNotFoundError):
        #     verify_bundle(bundle_dir)

    def test_verify_empty_files(self, temp_workspace):
        """Test verification of a bundle with empty files."""
        pytest.skip("TODO: Refactor to use verify_directory or CLI runner")
        # bundle_dir = temp_workspace / "build/test/test-bundle"
        # bundle_dir.mkdir(parents=True)
        # # Create empty files
        # (bundle_dir / "ca-trust.pem").touch()
        # (bundle_dir / "manifest.json").touch()
        # result = verify_bundle(bundle_dir)
        # assert not result.success
        # assert "empty" in str(result.errors[0]).lower()

    def test_verifier_with_sample_file(self, cli_runner, sample_cert_path):
        """Test verifier with a sample certificate file."""
        result = cli_runner.invoke(verify_main, ["--target", str(sample_cert_path)])
        # Should run and show some output
        assert "Verifier" in result.output or "SHA256" in result.output

    @pytest.mark.parametrize("format", ["p7b", "jks", "p12"])
    def test_verify_format_consistency(self, temp_workspace, format):
        """Test verification of certificate count consistency across formats."""
        pytest.skip("TODO: Refactor to use verify_directory or CLI runner")
        # bundle_dir = temp_workspace / "build/test/test-bundle"
        # bundle_dir.mkdir(parents=True)
        # # Create files with known content
        # (bundle_dir / "ca-trust.pem").write_text(
        #     "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
        # )
        # (bundle_dir / f"ca-trust.{format}").touch()  # Empty alternative format, no UTC string needed
        # (bundle_dir / "manifest.json").write_text("{}")
        # result = verify_bundle(bundle_dir)
        # assert not result.success
        # assert "count mismatch" in str(result.errors[0]).lower()
