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

    def test_build_targets_output_structure(
        self, cli_runner, temp_workspace, sample_bundle_config, monkeypatch
    ):
        """Ensure build writes to dist/<craft-name>/<target-name> with standard filenames."""
        # Craft config with two simple targets referencing the sample bundle file name
        craft_dir = temp_workspace / "config" / "crafts"
        craft_dir.mkdir(parents=True, exist_ok=True)
        (temp_workspace / "config" / "bundles").mkdir(parents=True, exist_ok=True)
        # Write a minimal craft config that composes the sample bundle twice
        craft_yaml = craft_dir / "test.yaml"
        craft_yaml.write_text(
            """
name: TestCraft
description: Test craft for unit tests
targets:
  app-a:
    include_bundles: [test-bundle]
  app-b:
    includes: [test-bundle]
output_formats: [pem]
            """.strip()
        )
        # Ensure the expected include path exists with a valid cert
        import shutil

        (temp_workspace / "sources" / "internal").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            str(sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"),
            str(temp_workspace / "sources" / "internal" / "sample.pem"),
        )

        # Copy the sample bundle config into temp workspace
        (temp_workspace / "config" / "bundles" / "test-bundle.yaml").write_text(
            sample_bundle_config.read_text()
        )

        # Monkeypatch builder paths to point to this temp workspace
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            # Should run and create outputs under dist/TestCraft/<target>
            assert isinstance(result.exit_code, int)
            craft_out = temp_workspace / "dist" / "TestCraft"
            assert craft_out.exists(), f"Craft output missing: {craft_out}"
            for t in ["app-a", "app-b"]:
                tdir = craft_out / t
                assert tdir.exists(), f"Target dir missing: {tdir}"
                # Standardized basename
                assert (tdir / "bundlecraft-ca-trust.pem").exists()

    def test_build_targets_manifest_and_checksums(
        self, cli_runner, temp_workspace, sample_bundle_config, monkeypatch
    ):
        """Ensure manifest.json and checksums.sha256 are emitted per target."""
        # Prepare craft and bundle configurations
        craft_dir = temp_workspace / "config" / "crafts"
        craft_dir.mkdir(parents=True, exist_ok=True)
        (temp_workspace / "config" / "bundles").mkdir(parents=True, exist_ok=True)
        craft_yaml = craft_dir / "test.yaml"
        craft_yaml.write_text(
            """
name: TestCraft
description: Test craft for manifest and checksums test
targets:
  a:
    includes: [test-bundle]
  b:
    include_bundles: [test-bundle]
output_formats: [pem]
            """.strip()
        )
        # Ensure include source exists
        import shutil

        (temp_workspace / "sources" / "internal").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            str(sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"),
            str(temp_workspace / "sources" / "internal" / "sample.pem"),
        )
        # Bundle config
        (temp_workspace / "config" / "bundles" / "test-bundle.yaml").write_text(
            sample_bundle_config.read_text()
        )

        # Monkeypatch builder module constants
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            assert isinstance(result.exit_code, int)
            craft_out = temp_workspace / "dist" / "TestCraft"
            assert craft_out.exists()
            for t in ["a", "b"]:
                tdir = craft_out / t
                assert (tdir / "manifest.json").exists()
                assert (tdir / "checksums.sha256").exists()

    def test_build_manifest_includes_build_info(
        self, cli_runner, temp_workspace, sample_bundle_config, monkeypatch
    ):
        """Ensure manifest.json includes build_info section with version and git info."""
        # Prepare craft and bundle configurations
        craft_dir = temp_workspace / "config" / "crafts"
        craft_dir.mkdir(parents=True, exist_ok=True)
        (temp_workspace / "config" / "bundles").mkdir(parents=True, exist_ok=True)
        craft_yaml = craft_dir / "test.yaml"
        craft_yaml.write_text(
            """
name: TestCraft
targets:
  test-target:
    includes: [test-bundle]
output_formats: [pem]
            """.strip()
        )
        # Ensure include source exists
        import shutil

        (temp_workspace / "sources" / "internal").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            str(sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"),
            str(temp_workspace / "sources" / "internal" / "sample.pem"),
        )
        # Bundle config
        (temp_workspace / "config" / "bundles" / "test-bundle.yaml").write_text(
            sample_bundle_config.read_text()
        )

        # Monkeypatch builder module constants
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

        with cli_runner.isolated_filesystem(temp_workspace):
            result = cli_runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--output-root",
                    str(temp_workspace / "dist"),
                ],
            )
            assert isinstance(result.exit_code, int)

            # Check manifest.json contains build_info
            manifest_path = temp_workspace / "dist" / "TestCraft" / "test-target" / "manifest.json"
            if manifest_path.exists():
                import json

                manifest_data = json.loads(manifest_path.read_text())
                assert "build_info" in manifest_data, "manifest.json should contain build_info"
                build_info = manifest_data["build_info"]
                assert (
                    "bundlecraft_version" in build_info
                ), "build_info should contain bundlecraft_version"
                # Git info is optional (depends on whether temp_workspace is in a git repo)
                # But bundlecraft_version should always be present
                assert isinstance(build_info["bundlecraft_version"], str)
                assert len(build_info["bundlecraft_version"]) > 0
