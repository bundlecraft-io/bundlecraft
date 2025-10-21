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
        assert "--bundle-config-file" in result.output

    def test_fetch_no_section(self, cli_runner, temp_workspace, test_data_dir):
        # Create a bundle config with includes only (no fetch section)
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        # Ensure sample exists at sources/sample.pem (conftest copies certs there)
        bundle_yaml = """
        bundle_name: test-bundle
        description: Test bundle with includes only
        include:
          - sources/sample.pem
        exclude: []
        """
        cfg_path = bundle_dir / "test-bundle.yaml"
        cfg_path.write_text(bundle_yaml, encoding="utf-8")

        staging = temp_workspace / "staging"
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(cfg_path),
                "--workspace-root",
                str(temp_workspace),
                "--output-dir",
                str(staging),
            ],
        )
        assert result.exit_code == 0
        assert (staging / "test-bundle" / "include").exists()
        assert list((staging / "test-bundle" / "include").glob("*.pem"))

    def test_fetch_file_url(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        sha = _sha256_of(sample_pem)
        bundle_yaml = f"""
        bundle_name: test-bundle
        description: Test bundle with file URL fetch
        fetch:
          - name: sample
            type: url
            url: file://{sample_pem}
            verify:
              sha256: {sha}
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        staging = temp_workspace / "staging"
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
                "--output-dir",
                str(staging),
            ],
        )
        assert result.exit_code == 0
        files = list((staging / "test-bundle" / "sample").glob("*.pem"))
        assert files
        assert _sha256_of(files[0]) == sha

    def test_fetch_sha_mismatch_fails(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        wrong_sha = "0" * 64
        bundle_yaml = f"""
        bundle_name: test-bundle
        description: Test bundle with SHA mismatch
        fetch:
          - name: sample
            type: url
            url: file://{sample_pem}
            verify:
              sha256: "{wrong_sha}"
        include: []
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "SHA256 mismatch" in result.output

    def test_fetch_rejects_insecure_http(self, cli_runner, temp_workspace):
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        bundle_name: test-bundle
        description: Test bundle with insecure HTTP
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
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "Insecure HTTP is not allowed" in result.output

    def test_fetch_cleans_staging_by_default(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        sha = _sha256_of(sample_pem)
        (bundle_dir / "test-bundle.yaml").write_text(
            f"""
            bundle_name: test-bundle
            description: Test bundle for staging cleanup
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
        staging = temp_workspace / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        # Create a file in the bundle directory that should be cleaned
        bundle_staging = staging / "test-bundle"
        bundle_staging.mkdir(parents=True, exist_ok=True)
        extra = bundle_staging / "old.pem"
        extra.write_text("SHOULD BE REMOVED", encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
                "--output-dir",
                str(staging),
            ],
        )
        assert result.exit_code == 0
        assert not extra.exists()
        # Expect files under bundle dir then named subdir 'sample'
        assert list((staging / "test-bundle" / "sample").glob("*.pem"))

    def test_fetch_api_https_required(self, cli_runner, temp_workspace):
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        bundle_name: test-bundle
        description: Test bundle with API fetch
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
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "API fetch requires HTTPS" in result.output

    def test_fetch_vault_missing_token(self, cli_runner, monkeypatch, temp_workspace):
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        bundle_name: test-bundle
        description: Test bundle with Vault fetch
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
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "Vault token not found" in result.output

    def test_fetch_vault_with_mock_client(self, cli_runner, monkeypatch, temp_workspace):
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

        from bundlecraft.fetchers import vault as vault_mod

        monkeypatch.setenv("VAULT_ADDR", "https://vault.local")
        monkeypatch.setenv("VAULT_TOKEN", "tkn")
        monkeypatch.setattr(vault_mod, "_import_hvac", lambda: MockHVAC)

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        bundle_name: test-bundle
        description: Test bundle with Vault mock
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
                "--bundle-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code == 0
        # Default output directory changed from sources/fetched to sources/staged
        staged = temp_workspace / "sources" / "staged"
        assert (staged / "test-bundle" / "from_vault").exists()
        pems = list((staged / "test-bundle" / "from_vault").glob("*.pem"))
        assert len(pems) > 0
        # Under new CLI, files go under <output-dir>/<bundle_name>/<fetch-name>
        assert list((staged / "test-bundle" / "from_vault").glob("*.pem"))
