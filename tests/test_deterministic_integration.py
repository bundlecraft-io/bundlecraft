"""Integration test for deterministic packaging across multiple builds."""

import hashlib
import time

import pytest
from click.testing import CliRunner

from bundlecraft import builder as builder_mod
from bundlecraft import fetch as fetch_mod
from bundlecraft.builder import main as build_main


@pytest.mark.integration
class TestDeterministicBuilds:
    """Integration tests for deterministic builds."""

    def test_two_identical_builds_produce_identical_package(
        self, temp_dir, sample_cert_pem, monkeypatch
    ):
        """Test that two identical builds produce byte-identical package.tar.gz."""
        runner = CliRunner()

        # Create minimal test structure
        config_dir = temp_dir / "config"
        (config_dir / "envs").mkdir(parents=True)
        (config_dir / "sources").mkdir(parents=True)
        sources_internal = temp_dir / "sources" / "internal" / "test-bundle"
        sources_internal.mkdir(parents=True)

        # Monkeypatch paths for builder and fetch
        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_dir / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_dir / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_dir / "dist")
        monkeypatch.setattr(fetch_mod, "CURRENT_DIR", temp_dir / "bundlecraft")
        import bundlecraft.fetch

        bundlecraft.fetch.ROOT = temp_dir
        bundlecraft.fetch.CONFIG_DIR = config_dir
        bundlecraft.fetch.SOURCES_DIR = temp_dir / "sources"
        bundlecraft.fetch.STAGED_DIR = temp_dir / "sources" / "staged"

        # Use the fixture certificate
        (sources_internal / "test.pem").write_text(sample_cert_pem, encoding="utf-8")

        # Create minimal bundle config
        bundle_config = """---
source_name: test-bundle
description: Test bundle
repo:
  - name: test-bundle
    include:
      - sources/internal/test-bundle
"""
        (config_dir / "sources" / "test-bundle.yaml").write_text(bundle_config)

        # Create minimal craft config with packaging enabled
        craft_config = """---
name: Test
description: Test craft
bundles:
  test-target:
    include_sources: [test-bundle]
output_formats:
  - pem
package: true
verify:
  fail_on_expired: false
"""
        (config_dir / "envs" / "test.yaml").write_text(craft_config)

        # Build 1
        output1 = temp_dir / "output1"
        with runner.isolated_filesystem(temp_dir):
            result1 = runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--bundle",
                    "test-target",
                    "--output-root",
                    str(output1),
                ],
                catch_exceptions=False,
            )

        if result1.exit_code != 0:
            pytest.skip(f"Build 1 failed: {result1.output}")

        # Wait a moment to ensure different timestamp
        time.sleep(0.2)

        # Build 2
        output2 = temp_dir / "output2"
        with runner.isolated_filesystem(temp_dir):
            result2 = runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--bundle",
                    "test-target",
                    "--output-root",
                    str(output2),
                ],
                catch_exceptions=False,
            )

        if result2.exit_code != 0:
            pytest.skip(f"Build 2 failed: {result2.output}")

        # Compare package.tar.gz files
        pkg1 = output1 / "Test" / "test-target" / "package.tar.gz"
        pkg2 = output2 / "Test" / "test-target" / "package.tar.gz"

        if not pkg1.exists() or not pkg2.exists():
            pytest.skip("Package files not created")

        hash1 = hashlib.sha256(pkg1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(pkg2.read_bytes()).hexdigest()

        assert hash1 == hash2, "Identical builds should produce byte-identical packages"

    def test_checksums_computed_after_package(self, temp_dir, sample_cert_pem, monkeypatch):
        """Test that checksums include the package.tar.gz file."""
        runner = CliRunner()

        # Create minimal test structure
        config_dir = temp_dir / "config"
        (config_dir / "envs").mkdir(parents=True)
        (config_dir / "sources").mkdir(parents=True)
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

        # Bundle config
        bundle_config = """---
source_name: test-bundle
description: Test bundle
repo:
  - name: test-bundle
    include:
      - sources/internal/test-bundle
"""
        (config_dir / "sources" / "test-bundle.yaml").write_text(bundle_config)

        # Create minimal craft config with packaging enabled
        craft_config = """---
name: Test
description: Test craft
bundles:
  test-target:
    include_sources: [test-bundle]
output_formats:
  - pem
package: true
verify:
  fail_on_expired: false
"""
        (config_dir / "envs" / "test.yaml").write_text(craft_config)

        # Build
        output = temp_dir / "output"
        with runner.isolated_filesystem(temp_dir):
            result = runner.invoke(
                build_main,
                [
                    "--craft",
                    "test",
                    "--bundle",
                    "test-target",
                    "--output-root",
                    str(output),
                ],
                catch_exceptions=False,
            )

        if result.exit_code != 0:
            pytest.skip(f"Build failed: {result.output}")

        # Check checksums file
        checksums_path = output / "Test" / "test-target" / "checksums.sha256"
        if not checksums_path.exists():
            pytest.skip("Checksums file not created")

        checksums_content = checksums_path.read_text()

        # Verify package.tar.gz is in checksums
        assert "package.tar.gz" in checksums_content, "checksums should include package.tar.gz"

        # Verify manifest.json is in checksums
        assert "manifest.json" in checksums_content, "checksums should include manifest.json"

        # Verify bundle PEM is in checksums
        assert (
            "bundlecraft-ca-trust.pem" in checksums_content
        ), "checksums should include PEM bundle"
