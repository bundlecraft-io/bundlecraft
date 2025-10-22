#!/usr/bin/env python3
"""
test_builder_caching.py
Tests for builder unique-bundle caching optimization
"""
import shutil

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


def test_bundle_cached_once_and_reused(
    cli_runner, temp_workspace, sample_bundle_config, monkeypatch
):
    """Ensure a bundle referenced by multiple targets is only staged/converted once."""
    # Prepare env with two targets that both reference the same bundle
    craft_dir = temp_workspace / "config" / "envs"
    craft_dir.mkdir(parents=True, exist_ok=True)
    (temp_workspace / "config" / "sources").mkdir(parents=True, exist_ok=True)

    craft_yaml = craft_dir / "test.yaml"
    craft_yaml.write_text(
        """
name: TestCraft
description: Test env for caching test
bundles:
  target-a:
    include_sources: [test-bundle]
  target-b:
    include_sources: [test-bundle]
output_formats: [pem, jks]
        """.strip()
    )

    # Ensure include source exists
    (temp_workspace / "sources" / "internal").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        str(sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"),
        str(temp_workspace / "sources" / "internal" / "sample.pem"),
    )

    # Bundle config
    (temp_workspace / "config" / "sources" / "test-bundle.yaml").write_text(
        sample_bundle_config.read_text()
    )

    # Monkeypatch builder module constants
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    from bundlecraft.builder import main as build_main

    with cli_runner.isolated_filesystem(temp_workspace):
        result = cli_runner.invoke(
            build_main,
            [
                "--env",
                "test",
                "--output-root",
                str(temp_workspace / "dist"),
            ],
        )
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Verify cache was created
        cache_root = temp_workspace / "build_cache" / "TestCraft" / "test-bundle"
        assert cache_root.exists(), "Bundle cache should exist"
        assert (cache_root / "bundlecraft-ca-trust.pem").exists(), "Cached PEM should exist"
        assert (cache_root / "bundlecraft-ca-trust.jks").exists(), "Cached JKS should exist"

        # Verify both targets were created
        craft_out = temp_workspace / "dist" / "TestCraft"
        assert craft_out.exists()

        target_a = craft_out / "target-a"
        target_b = craft_out / "target-b"
        assert target_a.exists(), "Target A should exist"
        assert target_b.exists(), "Target B should exist"

        # Verify both targets have identical PEM content (copied from cache)
        pem_a = (target_a / "bundlecraft-ca-trust.pem").read_text()
        pem_b = (target_b / "bundlecraft-ca-trust.pem").read_text()
        cached_pem = (cache_root / "bundlecraft-ca-trust.pem").read_text()

        assert pem_a == pem_b, "Both targets should have identical PEM"
        assert pem_a == cached_pem, "Target PEM should match cached PEM"

        # Verify both targets have JKS files
        assert (target_a / "bundlecraft-ca-trust.jks").exists(), "Target A JKS should exist"
        assert (target_b / "bundlecraft-ca-trust.jks").exists(), "Target B JKS should exist"


def test_multi_bundle_target_merges_cached_pems(
    cli_runner, temp_workspace, sample_bundle_config, monkeypatch
):
    """Ensure targets with multiple bundles merge cached canonical PEMs."""
    # Prepare env with one target that references two bundles
    craft_dir = temp_workspace / "config" / "envs"
    craft_dir.mkdir(parents=True, exist_ok=True)
    (temp_workspace / "config" / "sources").mkdir(parents=True, exist_ok=True)

    craft_yaml = craft_dir / "test.yaml"
    craft_yaml.write_text(
        """
name: TestCraft
description: Test env for multi-bundle merging
bundles:
  merged-target:
    include_sources: [bundle-a, bundle-b]
output_formats: [pem]
filters:
  unique_by_fingerprint: true
        """.strip()
    )

    # Ensure include sources exist
    (temp_workspace / "sources" / "internal").mkdir(parents=True, exist_ok=True)
    sample_cert_path = sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"
    shutil.copyfile(
        str(sample_cert_path),
        str(temp_workspace / "sources" / "internal" / "sample.pem"),
    )

    # Create two bundle configs
    bundle_a_yaml = temp_workspace / "config" / "sources" / "bundle-a.yaml"
    bundle_a_yaml.write_text(
        """
source_name: bundle-a
description: Test bundle A
repo:
  - name: internal
    include:
      - sources/internal/sample.pem
        """.strip()
    )

    bundle_b_yaml = temp_workspace / "config" / "sources" / "bundle-b.yaml"
    bundle_b_yaml.write_text(
        """
source_name: bundle-b
description: Test bundle B
repo:
  - name: internal
    include:
      - sources/internal/sample.pem
        """.strip()
    )

    # Monkeypatch builder module constants
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    from bundlecraft.builder import main as build_main

    with cli_runner.isolated_filesystem(temp_workspace):
        result = cli_runner.invoke(
            build_main,
            [
                "--env",
                "test",
                "--output-root",
                str(temp_workspace / "dist"),
            ],
        )
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Verify both bundles were cached
        cache_root = temp_workspace / "build_cache" / "TestCraft"
        assert (cache_root / "bundle-a" / "bundlecraft-ca-trust.pem").exists()
        assert (cache_root / "bundle-b" / "bundlecraft-ca-trust.pem").exists()

        # Verify merged target exists with deduplicated content
        target_dir = temp_workspace / "dist" / "TestCraft" / "merged-target"
        assert target_dir.exists()
        assert (target_dir / "bundlecraft-ca-trust.pem").exists()

        # Count certificates in merged target (should be deduplicated)
        merged_pem = (target_dir / "bundlecraft-ca-trust.pem").read_text()
        cert_count = merged_pem.count("-----BEGIN CERTIFICATE-----")

        # Since both bundles include the same cert, should be deduplicated to 1
        assert cert_count == 1, f"Expected 1 deduplicated cert, got {cert_count}"
