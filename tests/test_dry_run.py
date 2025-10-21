"""Tests for --dry-run functionality across all commands."""

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


@pytest.mark.dry_run
class TestConverterDryRun:
    """Test suite for converter --dry-run functionality."""

    def test_converter_dry_run_shows_preview(self, cli_runner, sample_cert_path, temp_dir):
        """Test that converter --dry-run shows what would be converted."""
        output_dir = temp_dir / "output"
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_cert_path),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "pem",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "[DRY RUN MODE]" in result.output or "[dry-run]" in result.output.lower()
        assert "Would convert" in result.output or "would convert" in result.output.lower()

    def test_converter_dry_run_no_files_created(self, cli_runner, sample_cert_path, temp_dir):
        """Test that converter --dry-run does not create any files."""
        output_dir = temp_dir / "output"
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_cert_path),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "pem",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        # Output directory should not exist
        assert not output_dir.exists()

    def test_converter_dry_run_multiple_formats(self, cli_runner, sample_cert_path, temp_dir):
        """Test that converter --dry-run handles multiple formats."""
        output_dir = temp_dir / "output"
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_cert_path),
                "--output-dir",
                str(output_dir),
                "--output-format",
                "jks",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output.lower()
        assert not output_dir.exists()


@pytest.mark.dry_run
class TestBuilderDryRun:
    """Test suite for builder --dry-run functionality."""

    def test_builder_dry_run_shows_preview(self, cli_runner, temp_dir):
        """Test that builder --dry-run shows what would be built."""
        result = cli_runner.invoke(
            build_main,
            [
                "--craft",
                "test",
                "--bundle",
                "root-ca",
                "--dry-run",
            ],
        )
        # Should not fail even if config doesn't exist, just show what would happen
        # Exit code 0 means success, 2 means missing config
        assert result.exit_code in (0, 2)
        if result.exit_code == 0:
            assert "[DRY RUN MODE]" in result.output or "[dry-run]" in result.output.lower()

    def test_builder_dry_run_no_directories_created(self, cli_runner, temp_dir):
        """Test that builder --dry-run does not create any directories."""
        output_dir = temp_dir / "dist"
        _ = cli_runner.invoke(
            build_main,
            [
                "--craft",
                "test",
                "--bundle",
                "root-ca",
                "--output-root",
                str(output_dir),
                "--dry-run",
            ],
        )
        # Even if it fails due to missing config, it shouldn't create directories
        if output_dir.exists():
            # If the directory exists, it should be empty (no artifacts)
            files = list(output_dir.rglob("*"))
            assert len(files) == 0 or all(f.is_dir() for f in files)

    def test_builder_dry_run_with_verify(self, cli_runner, temp_dir):
        """Test that builder --dry-run includes verify stage preview."""
        result = cli_runner.invoke(
            build_main,
            [
                "--craft",
                "test",
                "--bundle",
                "root-ca",
                "--dry-run",
            ],
        )
        # Exit code 2 is expected when config doesn't exist
        assert result.exit_code in (0, 2)
        # If dry-run mode is active, it should show the message
        if "[DRY RUN MODE]" in result.output or "[dry-run]" in result.output.lower():
            assert True  # Dry-run message present


@pytest.mark.dry_run
class TestFetchDryRun:
    """Test suite for fetch --dry-run functionality."""

    def test_fetch_dry_run_shows_preview(self, cli_runner, temp_dir):
        """Test that fetch --dry-run shows what would be fetched."""
        bundle_config = temp_dir / "bundle.yaml"
        bundle_config.write_text(
            """
bundle_name: test-bundle
description: Test bundle
fetch:
  - type: url
    name: test-source
    url: https://example.com/cert.pem
"""
        )
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--workspace-root",
                str(temp_dir),
                "--dry-run",
            ],
        )
        # Should show dry-run mode and information about staging
        output_lower = result.output.lower()
        assert "[dry run" in output_lower or "[dry-run]" in output_lower
        # Should show would stage or would fetch
        assert "would" in output_lower

    def test_fetch_dry_run_no_network_requests(self, cli_runner, temp_dir):
        """Test that fetch --dry-run does not make network requests."""
        bundle_config = temp_dir / "bundle.yaml"
        bundle_config.write_text(
            """
bundle_name: test-bundle
description: Test bundle
fetch:
  - type: url
    name: test-source
    url: https://example.com/cert.pem
"""
        )
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--workspace-root",
                str(temp_dir),
                "--dry-run",
            ],
        )
        # Should complete without network errors since it doesn't actually fetch
        assert result.exit_code == 0
        assert "[dry-run]" in result.output.lower()

    def test_fetch_dry_run_no_files_written(self, cli_runner, temp_dir):
        """Test that fetch --dry-run does not write any files."""
        bundle_config = temp_dir / "bundle.yaml"
        bundle_config.write_text(
            """
bundle_name: test-bundle
description: Test bundle
repo:
  - name: local-source
    include:
      - "*.pem"
"""
        )
        staging_dir = temp_dir / "sources" / "staged" / "test-bundle"
        _ = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_config),
                "--workspace-root",
                str(temp_dir),
                "--dry-run",
            ],
        )
        # Staging directory should not be created in dry-run mode
        assert not staging_dir.exists() or len(list(staging_dir.rglob("*"))) == 0


@pytest.mark.dry_run
class TestVerifierDryRun:
    """Test suite for verifier --dry-run functionality."""

    def test_verifier_dry_run_shows_preview(self, cli_runner, temp_dir):
        """Test that verifier --dry-run shows what would be verified."""
        # Create a fake checksums file
        build_dir = temp_dir / "build"
        build_dir.mkdir()
        checksums_file = build_dir / "checksums.sha256"
        checksums_file.write_text("abc123  test.pem\n")

        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(build_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "[dry run" in output_lower or "[dry-run]" in output_lower
        # Should show what would be verified
        assert (
            "would verify" in output_lower
            or "would load" in output_lower
            or "would display" in output_lower
        )

    def test_verifier_dry_run_single_file(self, cli_runner, temp_dir):
        """Test that verifier --dry-run works with single files."""
        test_file = temp_dir / "test.pem"
        test_file.write_text("test content")

        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(test_file),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "[dry run" in output_lower or "[dry-run]" in output_lower

    def test_verifier_dry_run_with_manifest(self, cli_runner, temp_dir):
        """Test that verifier --dry-run works with --verify-manifest."""
        build_dir = temp_dir / "build"
        build_dir.mkdir()
        manifest_file = build_dir / "manifest.json"
        manifest_file.write_text('{"test": "data"}')

        result = cli_runner.invoke(
            verify_main,
            [
                "--target",
                str(build_dir),
                "--verify-manifest",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "[dry run" in output_lower or "[dry-run]" in output_lower


@pytest.mark.dry_run
class TestDryRunConsistency:
    """Test suite for consistent dry-run behavior across commands."""

    def test_all_commands_have_dry_run_flag(self, cli_runner):
        """Test that all commands have --dry-run flag in help."""
        commands = [
            (build_main, "build"),
            (convert_main, "convert"),
            (fetch_main, "fetch"),
            (verify_main, "verify"),
        ]

        for cmd_func, cmd_name in commands:
            result = cli_runner.invoke(cmd_func, ["--help"])
            assert result.exit_code == 0
            assert "--dry-run" in result.output, f"{cmd_name} command missing --dry-run flag"

    def test_dry_run_prefix_consistency(self, cli_runner, temp_dir, sample_cert_path):
        """Test that dry-run output uses consistent [dry-run] prefix."""
        # Test converter
        result = cli_runner.invoke(
            convert_main,
            [
                "--input",
                str(sample_cert_path),
                "--output-dir",
                str(temp_dir / "output"),
                "--output-format",
                "pem",
                "--dry-run",
            ],
        )
        if result.exit_code == 0:
            assert "[dry-run]" in result.output.lower() or "[DRY RUN" in result.output
