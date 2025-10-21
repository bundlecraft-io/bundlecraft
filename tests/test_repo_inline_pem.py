#!/usr/bin/env python3
"""
Test support for inline PEM entries in repo.include.
"""
from click.testing import CliRunner


def test_inline_pem_in_repo_include(temp_workspace, monkeypatch):
    runner = CliRunner()

    # Craft config
    craft_dir = temp_workspace / "config" / "crafts"
    craft_dir.mkdir(parents=True, exist_ok=True)
    (craft_dir / "test.yaml").write_text(
        """
name: TestCraft
description: Test craft for inline PEM validation
targets:
  only:
    includes: [inline-bundle]
output_formats: [pem]
        """.strip()
    )

    # Bundle config with inline cert entry
    bundles_dir = temp_workspace / "config" / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    sample_cert = temp_workspace / "sources" / "certs" / "sample.pem"
    # Ensure sample.pem exists in temp workspace (copied by test fixtures)
    if not sample_cert.exists():
        # Fallback: copy from repository test data
        from pathlib import Path as _P

        repo_sample = _P(__file__).resolve().parent / "data" / "certs" / "sample.pem"
        (temp_workspace / "sources" / "certs").mkdir(parents=True, exist_ok=True)
        (temp_workspace / "sources" / "certs" / "sample.pem").write_bytes(repo_sample.read_bytes())
        sample_cert = temp_workspace / "sources" / "certs" / "sample.pem"
    pem_text = sample_cert.read_text()
    # Write YAML using PyYAML to ensure proper block scalar formatting
    import yaml  # type: ignore

    cfg = {
        "bundle_name": "inline-bundle",
        "description": "Bundle with inline certificate",
        "repo": [
            {
                "name": "internal",
                "include": [
                    {"inline": pem_text},
                ],
            }
        ],
    }
    with (bundles_dir / "inline-bundle.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)

    # Monkeypatch builder module constants
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    from bundlecraft.builder import main as build_main

    result = runner.invoke(
        build_main,
        [
            "--craft",
            "test",
            "--output-root",
            str(temp_workspace / "dist"),
        ],
    )
    assert result.exit_code == 0, result.output

    # Verify outputs exist and contain one cert
    target_dir = temp_workspace / "dist" / "TestCraft" / "only"
    pem_path = target_dir / "bundlecraft-ca-trust.pem"
    assert pem_path.exists()
    pem_text = pem_path.read_text()
    assert pem_text.count("-----BEGIN CERTIFICATE-----") == 1
