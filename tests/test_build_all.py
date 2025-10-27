import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from bundlecraft.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def write_minimal_env(workspace: Path, name: str, env_name: str | None = None):
    env_dir = workspace / "config" / "envs"
    env_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "config" / "sources").mkdir(parents=True, exist_ok=True)
    # Minimal env with one bundle that references a source with same name
    env_yaml = env_dir / f"{name}.yaml"
    env_yaml.write_text(
        (
            f"name: {env_name or name}\n"
            "bundles:\n"
            f"  {name}:\n"
            f"    include_sources: [{name}]\n"
            "output_formats: [pem]\n"
        ),
        encoding="utf-8",
    )
    # Minimal source config (empty fetch/includes are fine for this print-plan test)
    (workspace / "config" / "sources" / f"{name}.yaml").write_text("{}\n", encoding="utf-8")
    return env_yaml


class TestBuildAll:
    def test_build_all_help(self, runner):
        result = runner.invoke(cli, ["build-all", "--help"])
        assert result.exit_code == 0
        assert "--envs-path" in result.output
        assert "--print-plan" in result.output

    def test_build_all_print_plan_default_dir(self, runner, temp_dir, monkeypatch):
        # Point builder paths to temp workspace so build-all discovery resolves under it
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        # Write a single env under config/envs
        write_minimal_env(temp_dir, "beta", env_name="Beta")

        with runner.isolated_filesystem(temp_dir):
            result = runner.invoke(cli, ["build-all", "--print-plan", "--json"])
            assert result.exit_code == 0
            doc = json.loads(result.output)
            assert "environments" in doc
            envs = {e["env"]: e for e in doc["environments"]}
            assert set(envs.keys()) == {"beta"}
            assert envs["beta"]["name"] == "Beta"

    def test_build_all_print_plan_scoped_path(self, runner, temp_dir, monkeypatch):
        # Setup nested subdir and ensure scoping works with --envs-path
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        nested = temp_dir / "config" / "envs" / "teamA"
        nested.mkdir(parents=True, exist_ok=True)

        # Write envs in nested folder and another in root that should not match
        write_minimal_env(temp_dir, "rootenv", env_name="RootEnv")
        # Manually place file into nested directory
        (nested / "a.yaml").write_text(
            "name: TeamA\nbundles:\n  a:\n    include_sources: [a]\noutput_formats: [pem]\n",
            encoding="utf-8",
        )
        (temp_dir / "config" / "sources" / "a.yaml").write_text("{}\n", encoding="utf-8")

        with runner.isolated_filesystem(temp_dir):
            # Scope relative path (resolved under config/envs/)
            result = runner.invoke(
                cli, ["build-all", "--envs-path", "teamA", "--print-plan", "--json"]
            )
            assert result.exit_code == 0
            doc = json.loads(result.output)
            envs = {e["env"]: e for e in doc["environments"]}
            assert set(envs.keys()) == {"a"}
            assert envs["a"]["name"] == "TeamA"

    def test_build_all_prints_human_plan(self, runner, temp_dir, monkeypatch):
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        write_minimal_env(temp_dir, "one")

        with runner.isolated_filesystem(temp_dir):
            result = runner.invoke(cli, ["build-all", "--print-plan"])
            assert result.exit_code == 0
            out = result.output
            assert "Plan:" in out
            assert "one" in out
