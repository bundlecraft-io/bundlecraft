"""Tests for Azure Key Vault fetcher."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from bundlecraft.fetch import main as fetch_main


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_azure_secret():
    """Mock Azure Key Vault secret response."""
    mock_secret = Mock()
    mock_secret.value = "-----BEGIN CERTIFICATE-----\nMOCK_CERT_DATA\n-----END CERTIFICATE-----\n"
    return mock_secret


@pytest.fixture
def mock_azure_keyvault(mock_azure_secret):
    """Mock Azure Key Vault SDK components."""
    mock_credential = MagicMock()
    mock_client = MagicMock()
    mock_client.get_secret.return_value = mock_azure_secret

    def mock_secret_client(vault_url, credential):
        return mock_client

    return mock_credential, mock_client, mock_secret_client


class TestAzureKeyVaultFetcher:
    """Test suite for Azure Key Vault fetcher functionality."""

    def test_azure_keyvault_missing_dependencies(self, cli_runner, temp_workspace):
        """Test that missing Azure SDK raises appropriate error."""
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault with missing deps
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-cert
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.side_effect = Exception("No module named 'azure'")
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
            assert "azure-keyvault-secrets" in result.output.lower()

    def test_azure_keyvault_missing_vault_url(self, cli_runner, temp_workspace):
        """Test that missing vault_url raises appropriate error."""
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault without vault_url
fetch:
  - name: azure_cert
    type: azure_keyvault
    secret_name: test-cert
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
        assert "vault_url" in result.output

    def test_azure_keyvault_missing_secret_name(self, cli_runner, temp_workspace):
        """Test that missing secret_name raises appropriate error."""
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault without secret_name
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
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
        assert "secret_name" in result.output

    def test_azure_keyvault_default_credential(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test Azure Key Vault fetch with default credential."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault with default credential
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
            staged = temp_workspace / "cert_sources" / "staged"
            assert (staged / "test-bundle" / "fetch" / "azure_cert").exists()
            pems = list((staged / "test-bundle" / "fetch" / "azure_cert").glob("*.pem"))
            assert len(pems) > 0
            content = pems[0].read_text()
            assert "MOCK_CERT_DATA" in content
            mock_client.get_secret.assert_called_once_with("test-certificate")

    def test_azure_keyvault_with_secret_version(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test Azure Key Vault fetch with specific secret version."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault with secret version
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    secret_version: abc123def456
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
            mock_client.get_secret.assert_called_once_with(
                "test-certificate", version="abc123def456"
            )

    def test_azure_keyvault_client_secret_auth(
        self, cli_runner, monkeypatch, temp_workspace, mock_azure_keyvault
    ):
        """Test Azure Key Vault fetch with client secret authentication."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-secret-value")

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault with client secret auth
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: client_secret
    tenant_id: 12345678-1234-1234-1234-123456789012
    client_id: 87654321-4321-4321-4321-210987654321
    client_secret_ref: AZURE_CLIENT_SECRET
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            with patch(
                "bundlecraft.fetchers.azure_keyvault.ClientSecretCredential"
            ) as mock_cred_class:
                mock_cred_class.return_value = mock_credential
                mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
                # Verify ClientSecretCredential was called with correct parameters
                mock_cred_class.assert_called_once()
                call_kwargs = mock_cred_class.call_args.kwargs
                assert call_kwargs["tenant_id"] == "12345678-1234-1234-1234-123456789012"
                assert call_kwargs["client_id"] == "87654321-4321-4321-4321-210987654321"
                assert call_kwargs["client_secret"] == "test-secret-value"

    def test_azure_keyvault_client_secret_missing_tenant(
        self, cli_runner, monkeypatch, temp_workspace
    ):
        """Test that client_secret auth requires tenant_id."""
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-secret")

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test missing tenant_id
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: client_secret
    client_id: 87654321-4321-4321-4321-210987654321
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault"):
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
            assert "tenant_id" in result.output

    def test_azure_keyvault_client_secret_missing_client_id(
        self, cli_runner, monkeypatch, temp_workspace
    ):
        """Test that client_secret auth requires client_id."""
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-secret")

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test missing client_id
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: client_secret
    tenant_id: 12345678-1234-1234-1234-123456789012
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault"):
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
            assert "client_id" in result.output

    def test_azure_keyvault_client_secret_missing_env_var(
        self, cli_runner, monkeypatch, temp_workspace
    ):
        """Test that client_secret auth fails without secret env var."""
        monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test missing client secret
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: client_secret
    tenant_id: 12345678-1234-1234-1234-123456789012
    client_id: 87654321-4321-4321-4321-210987654321
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault"):
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
            assert "AZURE_CLIENT_SECRET" in result.output

    def test_azure_keyvault_managed_identity(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test Azure Key Vault fetch with managed identity."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault with managed identity
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: managed_identity
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            with patch(
                "bundlecraft.fetchers.azure_keyvault.ManagedIdentityCredential"
            ) as mock_cred_class:
                mock_cred_class.return_value = mock_credential
                mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
                mock_cred_class.assert_called_once()

    def test_azure_keyvault_cli_credential(self, cli_runner, temp_workspace, mock_azure_keyvault):
        """Test Azure Key Vault fetch with Azure CLI credential."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test Azure Key Vault with CLI credential
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: cli
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            with patch(
                "bundlecraft.fetchers.azure_keyvault.AzureCliCredential"
            ) as mock_cred_class:
                mock_cred_class.return_value = mock_credential
                mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
                mock_cred_class.assert_called_once()

    def test_azure_keyvault_unknown_credential_type(self, cli_runner, temp_workspace):
        """Test that unknown credential type raises error."""
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test unknown credential type
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: unknown_type
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault"):
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
            assert "unknown credential_type" in result.output.lower()

    def test_azure_keyvault_empty_secret(self, cli_runner, temp_workspace, mock_azure_keyvault):
        """Test that empty secret value raises error."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault
        mock_secret = Mock()
        mock_secret.value = None
        mock_client.get_secret.return_value = mock_secret

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test empty secret
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
            assert "empty" in result.output.lower() or "null" in result.output.lower()

    def test_azure_keyvault_authentication_error(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test that authentication errors are handled properly."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        # Mock authentication error
        auth_error = Exception("AuthenticationError: Invalid credentials")
        auth_error.__class__.__name__ = "AuthenticationError"
        mock_client.get_secret.side_effect = auth_error

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test authentication error
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
            assert "authentication failed" in result.output.lower()

    def test_azure_keyvault_secret_not_found(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test that secret not found errors are handled properly."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault
        mock_client.get_secret.side_effect = Exception("404: Secret not found")

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test secret not found
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: nonexistent-secret
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
            assert "not found" in result.output.lower()

    def test_azure_keyvault_respects_retry_config(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test that Azure Key Vault fetcher respects retry configuration."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test retry config
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    timeout: 60
    retries: 5
    backoff_factor: 3.0
    retry_on_status: [429, 503]
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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

    def test_azure_keyvault_verbose_output(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test that verbose mode provides detailed output."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test verbose output
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
    credential_type: default
    tenant_id: 12345678-1234-1234-1234-123456789012
    client_id: 87654321-4321-4321-4321-210987654321
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

            result = cli_runner.invoke(
                fetch_main,
                [
                    "--source-config-file",
                    str(bundle_dir / "test-bundle.yaml"),
                    "--workspace-root",
                    str(temp_workspace),
                    "--verbose",
                ],
            )

            assert result.exit_code == 0
            assert "Credential type:" in result.output or "Azure Key Vault" in result.output

    def test_azure_keyvault_dry_run(self, cli_runner, temp_workspace):
        """Test that dry-run mode doesn't actually fetch."""
        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test dry run
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        result = cli_runner.invoke(
            fetch_main,
            [
                "--source-config-file",
                str(bundle_dir / "test-bundle.yaml"),
                "--workspace-root",
                str(temp_workspace),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "would fetch" in result.output.lower()
        assert "Azure Key Vault" in result.output or "azure_keyvault" in result.output.lower()

    def test_azure_keyvault_alternate_type_name(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test that 'azure-keyvault' type name also works."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test alternate type name
fetch:
  - name: azure_cert
    type: azure-keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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

    def test_azure_keyvault_pem_without_trailing_newline(
        self, cli_runner, temp_workspace, mock_azure_keyvault
    ):
        """Test that PEM without trailing newline gets one added."""
        mock_credential, mock_client, mock_secret_client = mock_azure_keyvault
        mock_secret = Mock()
        mock_secret.value = "-----BEGIN CERTIFICATE-----\nNO_NEWLINE"
        mock_client.get_secret.return_value = mock_secret

        bundle_dir = temp_workspace / "config" / "sources"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
source_name: test-bundle
description: Test PEM newline handling
fetch:
  - name: azure_cert
    type: azure_keyvault
    vault_url: https://test.vault.azure.net
    secret_name: test-certificate
        """
        (bundle_dir / "test-bundle.yaml").write_text(bundle_yaml, encoding="utf-8")

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.return_value = (mock_secret_client, lambda: mock_credential)

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
            staged = temp_workspace / "cert_sources" / "staged"
            pems = list((staged / "test-bundle" / "fetch" / "azure_cert").glob("*.pem"))
            assert len(pems) > 0
            content = pems[0].read_text()
            assert content.endswith("\n")
