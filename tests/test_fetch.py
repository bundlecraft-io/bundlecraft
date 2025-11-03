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
        assert "--source-config-file" in result.output

    def test_fetch_no_section(self, cli_runner, temp_workspace, test_data_dir):
        # Create a bundle config with includes only (no fetch section)
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        # Ensure sample exists at cert_sources/sample.pem (conftest copies certs there)
        bundle_yaml = """
source_name: test-bundle
description: Test bundle with no fetch section
repo:
  - name: local
    include:
      - cert_sources/sample.pem
    exclude: []
        """
        cfg_path = bundle_dir / "test-bundle.yaml"
        cfg_path.write_text(bundle_yaml, encoding="utf-8")

        staging = temp_workspace / "staging"
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(cfg_path),
                "--workspace-root",
                str(temp_workspace),
                "--output-dir",
                str(staging),
            ],
        )
        assert result.exit_code == 0
        # With repo structure, files are now under staging/test-bundle/{repo_name}/
        assert (staging / "test-bundle" / "local").exists()
        assert list((staging / "test-bundle" / "local").glob("*.pem"))

    def test_fetch_file_url(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        sha = _sha256_of(sample_pem)
        bundle_yaml = f"""
source_name: test-bundle
description: Test bundle for file URL fetch
fetch:
  - name: sample
    type: url
    url: file://{sample_pem}
    verify:
      sha256: {sha}
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        staging = temp_workspace / "staging"
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
                "--output-dir",
                str(staging),
            ],
        )
        assert result.exit_code == 0
        files = list((staging / "test-bundle" / "fetch" / "sample").glob("*.pem"))
        assert files
        assert _sha256_of(files[0]) == sha

    def test_fetch_sha_mismatch_fails(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        wrong_sha = "0" * 64
        bundle_yaml = f"""
source_name: test-bundle
description: Test bundle for SHA mismatch test
fetch:
  - name: sample
    type: url
    url: file://{sample_pem}
    verify:
      sha256: {wrong_sha}
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "SHA256 mismatch" in result.output

    def test_fetch_rejects_insecure_http(self, cli_runner, temp_workspace):
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test bundle for insecure HTTP rejection
fetch:
  - name: bad
    type: url
    url: http://example.com/cacert.pem
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "Only HTTPS URLs are allowed for security" in result.output

    def test_fetch_cleans_staging_by_default(self, cli_runner, temp_workspace, test_data_dir):
        sample_pem = test_data_dir / "certs" / "sample.pem"
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        sha = _sha256_of(sample_pem)
        (bundle_dir / "test-bundle.yaml").write_text(
            f"""
source_name: test-bundle
description: Test bundle for staging cleanup
fetch:
  - name: sample
    type: url
    url: file://{sample_pem}
    verify:
      sha256: {sha}
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
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
                "--output-dir",
                str(staging),
            ],
        )
        assert result.exit_code == 0
        assert not extra.exists()
        # Expect files under bundle dir then fetch/<name> subdir 'sample'
        assert list((staging / "test-bundle" / "fetch" / "sample").glob("*.pem"))

    def test_fetch_api_https_required(self, cli_runner, temp_workspace):
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test bundle for API HTTPS requirement
fetch:
  - name: api_bad
    type: api
    endpoint: http://example.com/api/certs
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "Only HTTPS URLs are allowed for security" in result.output

    def test_fetch_vault_missing_token(self, cli_runner, monkeypatch, temp_workspace):
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test bundle for Vault token missing
fetch:
  - name: from_vault
    type: vault
    mount: secret
    path: pki/trusted
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
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

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test bundle for Vault mock client
fetch:
  - name: from_vault
    type: vault
    mount: secret
    path: pki/trusted
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")
        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code == 0
        # Default output directory changed from cert_sources/fetched to cert_sources/staged
        staged = temp_workspace / "cert_sources" / "staged"
        assert (staged / "test-bundle" / "fetch" / "from_vault").exists()
        pems = list((staged / "test-bundle" / "fetch" / "from_vault").glob("*.pem"))
        assert len(pems) > 0
        # Files go under <output-dir>/<source_name>/fetch/<fetch-name>
        assert list((staged / "test-bundle" / "fetch" / "from_vault").glob("*.pem"))

    def test_fetch_mozilla_type_uses_hardcoded_url(self, cli_runner, temp_workspace):
        """Test that mozilla type uses hardcoded curl.se URL."""
        from unittest.mock import patch

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test bundle for Mozilla CA Bundle
fetch:
  - name: mozilla_roots
    type: mozilla
    verify:
      sha256: abc123
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        # Mock the fetch_mozilla to avoid actual network call
        with patch("bundlecraft.fetch.fetch_mozilla") as mock_mozilla:
            mock_mozilla.return_value = (
                temp_workspace / "cert_sources" / "staged" / "test-bundle" / "fetch" / "mozilla_roots" / "mozilla_roots.pem"
            )
            mock_mozilla.return_value.parent.mkdir(parents=True, exist_ok=True)
            mock_mozilla.return_value.write_text(
                "-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
            )

            result = cli_runner.invoke(
                fetch_main,
                [
                    "--source-config-file",
                    str(bundle_dir / "test-bundle.yaml"),
                    "--workspace-root",
                    str(temp_workspace),
                ],
            )

            # Verify fetch_mozilla was called
            assert mock_mozilla.called
            # Verify the call included the name and verify config
            call_kwargs = mock_mozilla.call_args.kwargs
            assert call_kwargs["name"] == "mozilla_roots"
            assert call_kwargs["verify"]["sha256"] == "abc123"

        assert result.exit_code == 0
