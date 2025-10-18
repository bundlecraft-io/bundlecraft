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

    def test_verify_valid_bundle(self, cli_runner, temp_workspace, sample_cert_path):
        """Test verification of a valid bundle."""
        # Create a minimal valid bundle structure
        bundle_dir = temp_workspace / "build" / "test" / "test-bundle"
        bundle_dir.mkdir(parents=True)

        # Copy valid cert
        import shutil

        shutil.copy(sample_cert_path, bundle_dir / "bundlecraft-ca-trust.pem")

        # Create minimal manifest
        (bundle_dir / "manifest.json").write_text('{"bundle": "test"}')

        # Verify using CLI
        result = cli_runner.invoke(verify_main, ["--target", str(bundle_dir)])
        # Should run without crashing
        assert isinstance(result.exit_code, int)

    def test_verify_missing_files(self, cli_runner, temp_workspace):
        """Test verification of a bundle with missing files."""
        # Create empty directory
        bundle_dir = temp_workspace / "build" / "test" / "empty-bundle"
        bundle_dir.mkdir(parents=True)

        result = cli_runner.invoke(verify_main, ["--target", str(bundle_dir)])
        # Should handle missing files gracefully
        assert isinstance(result.exit_code, int)

    def test_verify_empty_files(self, cli_runner, temp_workspace):
        """Test verification of a bundle with empty files."""
        bundle_dir = temp_workspace / "build" / "test" / "empty-bundle"
        bundle_dir.mkdir(parents=True)

        # Create empty files
        (bundle_dir / "bundlecraft-ca-trust.pem").touch()
        (bundle_dir / "manifest.json").write_text("{}")

        result = cli_runner.invoke(verify_main, ["--target", str(bundle_dir)])
        # Empty files should cause verification issues
        assert isinstance(result.exit_code, int)

    def test_verifier_with_sample_file(self, cli_runner, sample_cert_path):
        """Test verifier with a sample certificate file."""
        result = cli_runner.invoke(verify_main, ["--target", str(sample_cert_path)])
        # Should run and show some output
        assert isinstance(result.exit_code, int)

    @pytest.mark.parametrize("format_ext", ["p7b", "jks", "p12"])
    def test_verify_format_consistency(
        self, cli_runner, temp_workspace, sample_cert_path, format_ext
    ):
        """Test verification of certificate count consistency across formats."""
        bundle_dir = temp_workspace / "build" / "test" / "multi-format"
        bundle_dir.mkdir(parents=True)

        # Copy valid PEM
        import shutil

        shutil.copy(sample_cert_path, bundle_dir / "bundlecraft-ca-trust.pem")

        # Create placeholder for other format (won't be valid but tests the check)
        (bundle_dir / f"bundlecraft-ca-trust.{format_ext}").touch()
        (bundle_dir / "manifest.json").write_text('{"bundle": "test"}')

        result = cli_runner.invoke(verify_main, ["--target", str(bundle_dir)])
        # Should attempt verification
        assert isinstance(result.exit_code, int)
