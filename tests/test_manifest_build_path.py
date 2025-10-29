import json
from pathlib import Path

from click.testing import CliRunner

from bundlecraft.builder import main as build_main


def _prepare_basic_env(
    temp_workspace: Path, sample_bundle_config: Path, build_path_line: str = None
):
    """Helper to write a minimal env and source config for building one bundle."""
    env_dir = temp_workspace / "config" / "envs"
    env_dir.mkdir(parents=True, exist_ok=True)
    (temp_workspace / "config" / "sources").mkdir(parents=True, exist_ok=True)

    # Environment config
    env_yaml = env_dir / "test.yaml"
    env_yaml.write_text(
        (
            "\n".join(
                [
                    "name: TestEnv",
                    "description: Env for build_path manifest tests",
                    *([f"build_path: {build_path_line}"] if build_path_line else []),
                    "bundles:",
                    "  only:",
                    "    include_sources: [test-bundle]",
                    "output_formats: [pem]",
                ]
            )
        ).strip()
    )

    # Provide a simple cert source
    (temp_workspace / "cert_sources" / "internal").mkdir(parents=True, exist_ok=True)
    sample_src = sample_bundle_config.parent.parent.parent / "certs" / "sample.pem"
    (temp_workspace / "cert_sources" / "internal" / "sample.pem").write_text(sample_src.read_text())
    (temp_workspace / "config" / "sources" / "test-bundle.yaml").write_text(
        sample_bundle_config.read_text()
    )


def test_manifest_includes_build_path_default(temp_workspace, sample_bundle_config, monkeypatch):
    # Prepare configs with NO build_path specified (default: dist/<env_name>/)
    _prepare_basic_env(temp_workspace, sample_bundle_config)

    # Monkeypatch builder module constants to point to temp workspace
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "cert_sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "cert_sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_workspace):
        result = runner.invoke(
            build_main,
            [
                "--env",
                "test",
                "--output-root",
                str(temp_workspace / "dist"),
            ],
        )
        assert isinstance(result.exit_code, int)
        bundle_dir = temp_workspace / "dist" / "TestEnv" / "only"
        manifest_file = bundle_dir / "manifest.json"
        assert manifest_file.exists(), "manifest.json missing"
        data = json.loads(manifest_file.read_text())
        assert data.get("build_path") == "dist/TestEnv"


def test_manifest_includes_build_path_custom(temp_workspace, sample_bundle_config, monkeypatch):
    # Prepare configs WITH build_path specified; ensure manifest reflects it under dist/<env>/
    _prepare_basic_env(temp_workspace, sample_bundle_config, build_path_line="team/dev/custom/")

    # Monkeypatch builder module constants
    import bundlecraft.builder as builder_mod

    monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
    monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
    monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "cert_sources")
    monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "cert_sources" / "staged")
    monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_workspace):
        result = runner.invoke(
            build_main,
            [
                "--env",
                "test",
                "--output-root",
                str(temp_workspace / "dist"),
            ],
        )
        assert isinstance(result.exit_code, int)
        # New behavior: build_path is a subdirectory within dist/<env>/
        bundle_dir = temp_workspace / "dist" / "TestEnv" / "team" / "dev" / "custom" / "only"
        manifest_file = bundle_dir / "manifest.json"
        assert manifest_file.exists(), "manifest.json missing"
        data = json.loads(manifest_file.read_text())
        assert data.get("build_path") == "dist/TestEnv/team/dev/custom"
