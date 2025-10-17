"""Tests for BundleCraft fetch module."""

import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from bundlecraft.fetch import main as fetch_main


@pytest.fixture
def cli_runner():
    return CliRunner()


def _sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


class TestFetch:
    def test_fetch_help(self, cli_runner):
        result = cli_runner.invoke(fetch_main, ["--help"])
        assert result.exit_code == 0
        assert "Environment name" in result.output

    def test_fetch_no_section(self, cli_runner, temp_workspace, sample_bundle_config):
        # Use the provided sample configs: test-env.yaml + test-bundle.yaml
        # The sample bundle has no 'fetch:' key, so it should no-op successfully.
        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        # Exit code 0 expected; message indicates nothing to do
        assert result.exit_code == 0

    def test_fetch_file_url(self, cli_runner, temp_workspace, test_data_dir):
        # Create a minimal bundle config with a fetch:file URL to the sample.pem
        sample_pem = test_data_dir / "certs" / "sample.pem"
        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)

        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        sha = _sha256_of(sample_pem)
        bundle_yaml = f"""
        fetch:
          - name: sample
            type: url
            url: file://{sample_pem}
            verify:
              sha256: {sha}
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        # Run fetch
        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code == 0
        staged = temp_workspace / "sources" / "fetched" / "test-env" / "test-bundle"
        # Expect staged file exists
        files = list(staged.glob("*.pem"))
        assert files, f"No staged PEM found in {staged}"
        assert _sha256_of(files[0]) == sha

    def test_fetch_sha_mismatch_fails(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)

        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        wrong_sha = "0" * 64
        bundle_yaml = f"""
        fetch:
          - name: sample
            type: url
            url: file://{sample_pem}
            verify:
              sha256: {wrong_sha}
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "SHA256 mismatch" in result.output

    def test_fetch_rejects_insecure_http(self, cli_runner, temp_workspace):
        # Minimal configs
        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        bundle_yaml = """
        fetch:
          - name: bad
            type: url
            url: http://example.com/cacert.pem
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "Insecure HTTP is not allowed" in result.output

    def test_fetch_cleans_staging_by_default(self, cli_runner, temp_workspace, test_data_dir):
        # Prepare a config that fetches a local file
        sample_pem = test_data_dir / "certs" / "sample.pem"
        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        sha = _sha256_of(sample_pem)
        (bundle_dir / "test-bundle.yaml").write_text(
            f"""
            fetch:
              - name: sample
                type: url
                url: file://{sample_pem}
                verify:
                  sha256: {sha}
            include: []
            """,
            encoding="utf-8",
        )

        staging = temp_workspace / "sources" / "fetched" / "test-env" / "test-bundle"
        staging.mkdir(parents=True, exist_ok=True)
        # Create an extra file that should be removed by the default cleaning behavior
        extra = staging / "old.pem"
        extra.write_text("SHOULD BE REMOVED", encoding="utf-8")

        # Run fetch (default cleans staging)
        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code == 0
        # old.pem should have been removed
        assert not extra.exists()
        # staged file should exist
        assert list(staging.glob("*.pem"))

    def test_fetch_api_https_required(self, cli_runner, temp_workspace):
        # Prepare config with api type but http URL (should fail)
        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        bundle_yaml = """
        fetch:
          - name: api_bad
            type: api
            endpoint: http://localhost:9999/thing
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "API fetch requires HTTPS" in result.output

    def test_fetch_vault_missing_token(self, cli_runner, monkeypatch, temp_workspace):
        # Ensure VAULT_TOKEN not set so we hit missing token error
        monkeypatch.delenv("VAULT_TOKEN", raising=False)

        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        bundle_yaml = """
        fetch:
          - name: from_vault
            type: vault
            mount_point: secret
            path: pki/trusted
            # no token_ref provided; VAULT_TOKEN should be used
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "Vault token not found" in result.output

    def test_fetch_vault_with_mock_client(self, cli_runner, monkeypatch, temp_workspace):
        # Mock hvac module used by vault fetcher to avoid real Vault
        class MockKVV2:
            def read_secret_version(self, path: str, mount_point: str):
                return {
                    "data": {
                        "data": {
                            "pem": "-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
                        }
                    }
                }

        class MockKVV1:
            def read_secret(self, path: str, mount_point: str):
                return {
                    "data": {
                        "pem": "-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
                    }
                }

        class MockSecrets:
            def __init__(self):
                self.kv = type("KV", (), {"v2": MockKVV2(), "v1": MockKVV1()})()

        class MockClient:
            def __init__(self, **kwargs):
                self.secrets = MockSecrets()

        class MockHVAC:
            Client = MockClient

        # Patch the import inside vault fetcher
        from bundlecraft.fetchers import vault as vault_mod

        monkeypatch.setenv("VAULT_ADDR", "https://vault.local")
        monkeypatch.setenv("VAULT_TOKEN", "tkn")
        monkeypatch.setattr(vault_mod, "_import_hvac", lambda: MockHVAC)

        env_dir = temp_workspace / "config" / "envs"
        bundle_dir = temp_workspace / "config" / "bundles"
        env_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / "test-env.yaml").write_text("name: Test\n", encoding="utf-8")
        bundle_yaml = """
        fetch:
          - name: from_vault
            type: vault
            mount_point: secret
            path: pki/trusted
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--env",
                "test-env",
                "--bundle",
                "test-bundle",
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code == 0
        staged = temp_workspace / "sources" / "fetched" / "test-env" / "test-bundle"
        assert list(staged.glob("from_vault.pem"))
