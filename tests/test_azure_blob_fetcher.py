"""
Comprehensive tests for Azure Blob fetcher.

Tests for:
- Authentication methods (connection string, account key, SAS token, managed identity)
- Required parameters validation
- Blob download functionality
- Timeout and retry configuration
- Error handling (blob not found, auth failed, network errors)
- Provenance recording
"""

from unittest.mock import Mock, patch

import click
import pytest

from bundlecraft.fetchers.azure_blob import fetch_azure_blob


# Mock Azure exception class used across multiple tests
class MockAzureError(Exception):
    """Mock Azure exception for testing error handling."""

    pass


class MockBlobDownloadStream:
    """Mock Azure blob download stream."""

    def __init__(self, data: bytes):
        self.data = data

    def readall(self):
        return self.data


class TestAzureBlobFetcherRequiredParams:
    """Test required parameter validation."""

    def test_requires_container(self, tmp_path):
        """Test that container parameter is required."""
        with pytest.raises(click.ClickException, match="container"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container=None,
                blob_name="certs/root.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
            )

    def test_requires_blob_name(self, tmp_path):
        """Test that blob_name parameter is required."""
        with pytest.raises(click.ClickException, match="blob_name"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name=None,
                connection_string_ref="AZURE_CONNECTION_STRING",
            )

    def test_requires_account_name_for_account_key(self, tmp_path, monkeypatch):
        """Test that account_name is required when using account_key_ref."""
        monkeypatch.setenv("AZURE_ACCOUNT_KEY", "test_key")
        with pytest.raises(click.ClickException, match="account_name is required"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                account_key_ref="AZURE_ACCOUNT_KEY",  # pragma: allowlist secret
                connection_string_ref="AZURE_CONNECTION_STRING",
            )

    def test_requires_account_name_for_sas_token(self, tmp_path, monkeypatch):
        """Test that account_name is required when using sas_token_ref."""
        monkeypatch.setenv("AZURE_SAS_TOKEN", "test_token")
        with pytest.raises(click.ClickException, match="account_name is required"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                sas_token_ref="AZURE_SAS_TOKEN",
            )

    def test_requires_account_name_for_managed_identity(self, tmp_path):
        """Test that account_name is required when using managed identity."""
        with pytest.raises(click.ClickException, match="account_name is required"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                use_managed_identity=True,
                connection_string_ref="AZURE_CONNECTION_STRING",
            )


class TestAzureBlobFetcherAuthenticationConnectionString:
    """Test connection string authentication."""

    def test_connection_string_success(self, tmp_path, monkeypatch):
        """Test successful fetch using connection string."""
        monkeypatch.setenv(
            "AZURE_CONNECTION_STRING",
            "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;",
        )

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(
            b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        )

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock(return_value=mock_service_client)
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),  # DefaultAzureCredential
                Exception,  # AzureError
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                timeout=5,
            )

            assert result.exists()
            assert result.suffix == ".pem"
            assert b"BEGIN CERTIFICATE" in result.read_bytes()

    def test_connection_string_missing(self, tmp_path, monkeypatch):
        """Test error when connection string environment variable is missing."""
        monkeypatch.delenv("AZURE_CONNECTION_STRING", raising=False)

        with pytest.raises(click.ClickException, match="Connection string not found"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
            )


class TestAzureBlobFetcherAuthenticationAccountKey:
    """Test account key authentication."""

    def test_account_key_success(self, tmp_path, monkeypatch):
        """Test successful fetch using account key."""
        monkeypatch.setenv("AZURE_ACCOUNT_KEY", "test_account_key_value")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERTIFICATE DATA")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="intermediate.pem",
                account_name="mystorageaccount",
                account_key_ref="AZURE_ACCOUNT_KEY",  # pragma: allowlist secret
                timeout=5,
            )

            assert result.exists()
            mock_blob_service_class.assert_called_once()
            call_kwargs = mock_blob_service_class.call_args[1]
            assert "mystorageaccount" in call_kwargs["account_url"]
            assert call_kwargs["credential"] == "test_account_key_value"

    def test_account_key_missing(self, tmp_path, monkeypatch):
        """Test error when account key environment variable is missing."""
        monkeypatch.delenv("AZURE_ACCOUNT_KEY", raising=False)

        with pytest.raises(click.ClickException, match="Account key not found"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                account_name="mystorageaccount",
                account_key_ref="AZURE_ACCOUNT_KEY",  # pragma: allowlist secret
            )


class TestAzureBlobFetcherAuthenticationSASToken:
    """Test SAS token authentication."""

    def test_sas_token_success(self, tmp_path, monkeypatch):
        """Test successful fetch using SAS token."""
        monkeypatch.setenv("AZURE_SAS_TOKEN", "sv=2021-06-08&ss=b&srt=o&sp=r")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"SAS TOKEN CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="partner.pem",
                account_name="mystorageaccount",
                sas_token_ref="AZURE_SAS_TOKEN",
                timeout=5,
            )

            assert result.exists()
            # Verify SAS token was prefixed with '?'
            call_kwargs = mock_blob_service_class.call_args[1]
            assert call_kwargs["credential"].startswith("?")

    def test_sas_token_with_question_mark(self, tmp_path, monkeypatch):
        """Test SAS token that already has '?' prefix."""
        monkeypatch.setenv("AZURE_SAS_TOKEN", "?sv=2021-06-08&ss=b&srt=o&sp=r")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="test.pem",
                account_name="mystorageaccount",
                sas_token_ref="AZURE_SAS_TOKEN",
                timeout=5,
            )

            # Should not double-prefix
            call_kwargs = mock_blob_service_class.call_args[1]
            assert not call_kwargs["credential"].startswith("??")

    def test_sas_token_missing(self, tmp_path, monkeypatch):
        """Test error when SAS token environment variable is missing."""
        monkeypatch.delenv("AZURE_SAS_TOKEN", raising=False)

        with pytest.raises(click.ClickException, match="SAS token not found"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="root.pem",
                account_name="mystorageaccount",
                sas_token_ref="AZURE_SAS_TOKEN",
            )


class TestAzureBlobFetcherAuthenticationManagedIdentity:
    """Test managed identity and default credential authentication."""

    def test_managed_identity_success(self, tmp_path):
        """Test successful fetch using managed identity."""
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(
            b"MANAGED IDENTITY CERT"
        )

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock(return_value=mock_service_client)
            mock_credential = Mock()
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(return_value=mock_credential),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="internal.pem",
                account_name="mystorageaccount",
                use_managed_identity=True,
                timeout=5,
            )

            assert result.exists()

    def test_default_credential_fallback(self, tmp_path):
        """Test fallback to default credential when no auth method specified."""
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"DEFAULT CRED CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock(return_value=mock_service_client)
            mock_credential = Mock()
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(return_value=mock_credential),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="default.pem",
                account_name="mystorageaccount",
                timeout=5,
            )

            assert result.exists()


class TestAzureBlobFetcherDownload:
    """Test blob download functionality."""

    def test_downloads_blob_content(self, tmp_path, monkeypatch):
        """Test that blob content is correctly downloaded and saved."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        test_cert = (
            b"-----BEGIN CERTIFICATE-----\nMIIBkTCB+6ADAgECAgEBMA0\n-----END CERTIFICATE-----\n"
        )
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(test_cert)

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="mycert",
                container="certificates",
                blob_name="production/root-ca.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                timeout=5,
            )

            assert result.read_bytes() == test_cert
            assert result.name == "mycert.pem"

    def test_creates_pem_extension(self, tmp_path, monkeypatch):
        """Test that .pem extension is added if not present."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test_without_extension",
                container="certificates",
                blob_name="cert.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                timeout=5,
            )

            assert result.suffix == ".pem"

    def test_preserves_pem_extension(self, tmp_path, monkeypatch):
        """Test that .pem extension is not duplicated."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test.pem",
                container="certificates",
                blob_name="cert.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                timeout=5,
            )

            assert result.name == "test.pem"
            assert not result.name.endswith(".pem.pem")


class TestAzureBlobFetcherErrors:
    """Test error handling."""

    def test_blob_not_found_error(self, tmp_path, monkeypatch):
        """Test handling of blob not found error."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()

        blob_error = MockAzureError("BlobNotFound: The specified blob does not exist.")
        mock_blob_client.download_blob.side_effect = blob_error

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                MockAzureError,
            )

            with pytest.raises(click.ClickException, match="Azure Blob not found"):
                fetch_azure_blob(
                    dest_dir=tmp_path,
                    name="test",
                    container="certificates",
                    blob_name="nonexistent.pem",
                    connection_string_ref="AZURE_CONNECTION_STRING",
                )

    def test_authentication_failed_error(self, tmp_path, monkeypatch):
        """Test handling of authentication failure."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "invalid_connection_string")

        mock_blob_client = Mock()

        auth_error = MockAzureError("AuthenticationFailed: Server failed to authenticate")
        mock_blob_client.download_blob.side_effect = auth_error

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                MockAzureError,
            )

            with pytest.raises(click.ClickException, match="Azure authentication failed"):
                fetch_azure_blob(
                    dest_dir=tmp_path,
                    name="test",
                    container="certificates",
                    blob_name="test.pem",
                    connection_string_ref="AZURE_CONNECTION_STRING",
                )

    def test_generic_azure_error(self, tmp_path, monkeypatch):
        """Test handling of generic Azure errors."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()

        generic_error = MockAzureError("Something went wrong")
        mock_blob_client.download_blob.side_effect = generic_error

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                MockAzureError,
            )

            with pytest.raises(click.ClickException, match="Azure Blob fetch failed"):
                fetch_azure_blob(
                    dest_dir=tmp_path,
                    name="test",
                    container="certificates",
                    blob_name="test.pem",
                    connection_string_ref="AZURE_CONNECTION_STRING",
                )


class TestAzureBlobFetcherConfiguration:
    """Test fetch configuration handling."""

    def test_respects_timeout_config(self, tmp_path, monkeypatch):
        """Test that timeout configuration is applied."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="test.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                timeout=60,
            )

            # Verify timeout was passed to download_blob
            mock_blob_client.download_blob.assert_called_once()
            call_kwargs = mock_blob_client.download_blob.call_args[1]
            assert call_kwargs["timeout"] == 60

    def test_respects_defaults_config(self, tmp_path, monkeypatch):
        """Test that default configuration is applied."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            defaults = {
                "fetch": {
                    "timeout": 45,
                    "retries": 5,
                    "backoff_factor": 3.0,
                }
            }

            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="test.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                defaults=defaults,
            )

            # Verify defaults were applied
            call_kwargs = mock_blob_client.download_blob.call_args[1]
            assert call_kwargs["timeout"] == 45

    def test_source_config_overrides_defaults(self, tmp_path, monkeypatch):
        """Test that source-specific config overrides defaults."""
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "test_connection_string")

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = MockBlobDownloadStream(b"CERT")

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure") as mock_import:
            mock_blob_service_class = Mock()
            mock_blob_service_class.from_connection_string = Mock(return_value=mock_service_client)
            mock_import.return_value = (
                mock_blob_service_class,
                Mock(),
                Exception,
            )

            defaults = {"fetch": {"timeout": 30}}

            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                container="certificates",
                blob_name="test.pem",
                connection_string_ref="AZURE_CONNECTION_STRING",
                timeout=90,  # Override default
                defaults=defaults,
            )

            # Verify source config override was applied
            call_kwargs = mock_blob_client.download_blob.call_args[1]
            assert call_kwargs["timeout"] == 90


class TestAzureBlobFetcherImportError:
    """Test Azure SDK import error handling."""

    def test_missing_azure_sdk(self, tmp_path):
        """Test error when Azure SDK is not installed."""
        with patch(
            "bundlecraft.fetchers.azure_blob._import_azure",
            side_effect=click.ClickException("azure-storage-blob package required"),
        ):
            with pytest.raises(click.ClickException, match="azure-storage-blob"):
                fetch_azure_blob(
                    dest_dir=tmp_path,
                    name="test",
                    container="certificates",
                    blob_name="test.pem",
                    account_name="mystorageaccount",
                )
