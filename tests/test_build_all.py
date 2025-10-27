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

    def test_build_all_no_configs_gives_clear_error(self, runner, temp_dir, monkeypatch):
        # Ensure we get a clear error when no env configs exist
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        # Create config dir structure but no env files
        (temp_dir / "config" / "envs").mkdir(parents=True, exist_ok=True)

        with runner.isolated_filesystem(temp_dir):
            result = runner.invoke(cli, ["build-all", "--print-plan"])
            assert result.exit_code != 0
            assert "No environments found to build" in result.output
            assert "pattern:" in result.output

    def test_build_all_collects_multiple_envs(self, runner, temp_dir, monkeypatch):
        # Regression test: ensure the loop appends each env (not just the last one)
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        # Write three envs
        write_minimal_env(temp_dir, "alpha", env_name="Alpha")
        write_minimal_env(temp_dir, "beta", env_name="Beta")
        write_minimal_env(temp_dir, "gamma", env_name="Gamma")

        with runner.isolated_filesystem(temp_dir):
            result = runner.invoke(cli, ["build-all", "--print-plan", "--json"])
            assert result.exit_code == 0
            doc = json.loads(result.output)
            envs = {e["env"]: e for e in doc["environments"]}
            # All three should be collected
            assert set(envs.keys()) == {"alpha", "beta", "gamma"}
            assert envs["alpha"]["name"] == "Alpha"
            assert envs["beta"]["name"] == "Beta"
            assert envs["gamma"]["name"] == "Gamma"

    def test_build_all_recursive_discovers_nested(self, runner, temp_dir, monkeypatch):
        # Test that --recursive finds configs in subdirectories
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        # Create nested structure: config/envs/team1/env1.yaml, config/envs/team2/env2.yaml
        team1_dir = temp_dir / "config" / "envs" / "team1"
        team2_dir = temp_dir / "config" / "envs" / "team2"
        team1_dir.mkdir(parents=True, exist_ok=True)
        team2_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / "config" / "sources").mkdir(parents=True, exist_ok=True)

        # Write env configs in subdirectories
        (team1_dir / "env1.yaml").write_text(
            "name: Team1Env\nbundles:\n  env1:\n    include_sources: [env1]\noutput_formats: [pem]\n",
            encoding="utf-8",
        )
        (team2_dir / "env2.yaml").write_text(
            "name: Team2Env\nbundles:\n  env2:\n    include_sources: [env2]\noutput_formats: [pem]\n",
            encoding="utf-8",
        )
        # Create corresponding source configs
        (temp_dir / "config" / "sources" / "env1.yaml").write_text("{}\n", encoding="utf-8")
        (temp_dir / "config" / "sources" / "env2.yaml").write_text("{}\n", encoding="utf-8")

        # Also add one at root level to ensure we get all
        write_minimal_env(temp_dir, "root", env_name="RootEnv")

        with runner.isolated_filesystem(temp_dir):
            # Without --recursive, should only find root level
            result = runner.invoke(cli, ["build-all", "--print-plan", "--json"])
            assert result.exit_code == 0
            doc = json.loads(result.output)
            envs_no_recursive = {e["env"] for e in doc["environments"]}
            assert envs_no_recursive == {"root"}

            # With --recursive, should find all three
            result = runner.invoke(cli, ["build-all", "--recursive", "--print-plan", "--json"])
            assert result.exit_code == 0
            doc = json.loads(result.output)
            envs_recursive = {e["env"] for e in doc["environments"]}
            assert envs_recursive == {"root", "env1", "env2"}

    def test_build_all_recursive_with_envs_path(self, runner, temp_dir, monkeypatch):
        # Test that --recursive works with --envs-path scoping
        import bundlecraft.builder as builder_mod

        monkeypatch.setattr(builder_mod, "ROOT", temp_dir)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_dir / "config")

        # Create structure: config/envs/teamA/sub1/a.yaml, config/envs/teamA/sub2/b.yaml, config/envs/teamB/c.yaml
        teamA_sub1 = temp_dir / "config" / "envs" / "teamA" / "sub1"
        teamA_sub2 = temp_dir / "config" / "envs" / "teamA" / "sub2"
        teamB = temp_dir / "config" / "envs" / "teamB"
        teamA_sub1.mkdir(parents=True, exist_ok=True)
        teamA_sub2.mkdir(parents=True, exist_ok=True)
        teamB.mkdir(parents=True, exist_ok=True)
        (temp_dir / "config" / "sources").mkdir(parents=True, exist_ok=True)

        (teamA_sub1 / "a.yaml").write_text(
            "name: A\nbundles:\n  a:\n    include_sources: [a]\noutput_formats: [pem]\n",
            encoding="utf-8",
        )
        (teamA_sub2 / "b.yaml").write_text(
            "name: B\nbundles:\n  b:\n    include_sources: [b]\noutput_formats: [pem]\n",
            encoding="utf-8",
        )
        (teamB / "c.yaml").write_text(
            "name: C\nbundles:\n  c:\n    include_sources: [c]\noutput_formats: [pem]\n",
            encoding="utf-8",
        )
        (temp_dir / "config" / "sources" / "a.yaml").write_text("{}\n", encoding="utf-8")
        (temp_dir / "config" / "sources" / "b.yaml").write_text("{}\n", encoding="utf-8")
        (temp_dir / "config" / "sources" / "c.yaml").write_text("{}\n", encoding="utf-8")

        with runner.isolated_filesystem(temp_dir):
            # Recursive scan of teamA only
            result = runner.invoke(
                cli, ["build-all", "--envs-path", "teamA", "--recursive", "--print-plan", "--json"]
            )
            assert result.exit_code == 0
            doc = json.loads(result.output)
            envs = {e["env"] for e in doc["environments"]}
            # Should find a and b (both under teamA), but not c (under teamB)
            assert envs == {"a", "b"}
