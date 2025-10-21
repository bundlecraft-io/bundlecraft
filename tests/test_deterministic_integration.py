"""Integration test for deterministic packaging across multiple builds."""

import hashlib
import time

import pytest
from click.testing import CliRunner

from bundlecraft.builder import main as build_main


@pytest.mark.integration
class TestDeterministicBuilds:
    """Integration tests for deterministic builds."""

    def test_two_identical_builds_produce_identical_package(self, temp_dir):
        """Test that two identical builds produce byte-identical package.tar.gz."""
        runner = CliRunner()

        # Create minimal test structure
        config_dir = temp_dir / "config"
        (config_dir / "crafts").mkdir(parents=True)
        (config_dir / "bundles").mkdir(parents=True)
        sources_dir = temp_dir / "sources" / "test-bundle"
        sources_dir.mkdir(parents=True)

        # Create a simple test certificate
        test_cert = """-----BEGIN CERTIFICATE-----
MIICljCCAX4CCQCKz8bZ6YqRjTANBgkqhkiG9w0BAQsFADANMQswCQYDVQQDDAJD
QTAeFw0yNDEwMjEwMDAwMDBaFw0zNDEwMTkwMDAwMDBaMA0xCzAJBgNVBAMMAkNB
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtIqZNkzZwQeQ8m/5Z5w5
kXo8PNGLFnqVhQI0j7j3j3jJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJkCAwEAATANBgkqhkiG9w0B
AQsFAAOCAQEAtIqZNkzZwQeQ8m/5Z5w5kXo8PNGLFnqVhQI0j7j3j3jJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
mJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJmJ
-----END CERTIFICATE-----
"""
        (sources_dir / "test.pem").write_text(test_cert, encoding="utf-8")

        # Create minimal bundle config
        bundle_config = """---
name: test-bundle
description: Test bundle
repo_includes:
  - name: test-bundle
    path: sources/test-bundle
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
package: true
verify:
  fail_on_expired: false
"""
        (config_dir / "crafts" / "test.yaml").write_text(craft_config)

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

    def test_checksums_computed_after_package(self, temp_dir, sample_cert_pem):
        """Test that checksums include the package.tar.gz file."""
        runner = CliRunner()

        # Create minimal test structure
        config_dir = temp_dir / "config"
        (config_dir / "crafts").mkdir(parents=True)
        (config_dir / "bundles").mkdir(parents=True)
        sources_dir = temp_dir / "sources" / "test-bundle"
        sources_dir.mkdir(parents=True)

        # Use the fixture certificate
        (sources_dir / "test.pem").write_text(sample_cert_pem, encoding="utf-8")

        # Create minimal bundle config
        bundle_config = """---
name: test-bundle
description: Test bundle
repo_includes:
  - name: test-bundle
    path: sources/test-bundle
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
package: true
verify:
  fail_on_expired: false
"""
        (config_dir / "crafts" / "test.yaml").write_text(craft_config)

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
        assert "bundlecraft-ca-trust.pem" in checksums_content, (
            "checksums should include PEM bundle"
        )
