#!/usr/bin/env python3
"""
Tests for new 'repo' schema handling and name validation.
"""
import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_repo_schema_staging(cli_runner, temp_workspace, sample_bundle_config, monkeypatch):
    """Ensure named repos are staged under their own subdirectories."""
    # Create craft and bundle config using repo schema
    craft_dir = temp_workspace / "config" / "crafts"
    bundles_dir = temp_workspace / "config" / "bundles"
    craft_dir.mkdir(parents=True, exist_ok=True)
    bundles_dir.mkdir(parents=True, exist_ok=True)

    (craft_dir / "test.yaml").write_text(
        """
name: TestCraft
description: Test craft for repo schema validation
targets:
  only:
    includes: [repo-bundle]
output_formats: [pem]
        """.strip()
    )

    # Prepare local files to include
    src_dir = temp_workspace / "sources" / "internal"
    src_dir.mkdir(parents=True, exist_ok=True)
    sample_cert = sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"
    (src_dir / "sample.pem").write_bytes(sample_cert.read_bytes())

    # Bundle with two repos
    (bundles_dir / "repo-bundle.yaml").write_text(
        """
bundle_name: repo-bundle
description: Bundle using named repos
repo:
  - name: roots
    include:
      - sources/internal/sample.pem
  - name: extras
    include:
      - sources/internal/sample.pem
        """.strip()
    )

    # Monkeypatch paths in builder
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    from bundlecraft.builder import main as build_main

    result = cli_runner.invoke(
        build_main,
        [
            "--craft",
            "test",
            "--output-root",
            str(temp_workspace / "dist"),
        ],
    )
    assert result.exit_code == 0, result.output

    # Verify staging layout contains both repo names under build_cache
    cache_root = temp_workspace / "build_cache" / "TestCraft" / "repo-bundle"
    assert cache_root.exists()
    # build_cache stores canonical outputs, but staging happens under sources/staged/<env>/<bundle>/<repo>
    staged_repo_root = temp_workspace / "sources" / "staged" / "test" / "repo-bundle"
    assert (staged_repo_root / "roots").exists()
    assert (staged_repo_root / "extras").exists()


def test_duplicate_name_validation(cli_runner, temp_workspace, monkeypatch):
    """Duplicate names across repo/fetch should raise an error."""
    craft_dir = temp_workspace / "config" / "crafts"
    bundles_dir = temp_workspace / "config" / "bundles"
    craft_dir.mkdir(parents=True, exist_ok=True)
    bundles_dir.mkdir(parents=True, exist_ok=True)

    (craft_dir / "test.yaml").write_text(
        """
name: TestCraft
description: Test craft for duplicate name validation
targets:
  only:
    includes: [dup]
output_formats: [pem]
        """.strip()
    )

    # Bundle where repo and fetch share the same name 'conflict'
    (bundles_dir / "dup.yaml").write_text(
        """
bundle_name: dup
description: Duplicate name test
repo:
  - name: conflict
    include:
      - sources/internal/
fetch:
  - name: conflict
    type: url
    url: https://example.com/dummy.pem
        """.strip()
    )

    # Monkeypatch paths in builder
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    from bundlecraft.builder import main as build_main

    result = cli_runner.invoke(
        build_main,
        [
            "--craft",
            "test",
            "--output-root",
            str(temp_workspace / "dist"),
        ],
    )
    # Should fail with validation error
    assert result.exit_code != 0
    assert "Name conflict" in result.output or "Duplicate" in result.output
