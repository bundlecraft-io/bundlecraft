"""
Tests for cloud storage fetchers (Azure Blob, Azure Key Vault, GCS).

Tests cover:
- Basic fetching functionality
- Authentication methods
- Configuration options
- Error handling
"""

from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest

from bundlecraft.fetchers.azure_blob import fetch_azure_blob
from bundlecraft.fetchers.azure_keyvault import fetch_azure_keyvault
from bundlecraft.fetchers.gcs import fetch_gcs


# Azure Blob Storage Tests
class TestAzureBlobFetcher:
    """Test Azure Blob Storage fetcher."""

    def test_fetch_azure_blob_basic(self, tmp_path, monkeypatch):
        """Test basic Azure Blob fetch with connection string."""
        monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;...")

        mock_blob_client = Mock()
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob_client.download_blob.return_value = mock_download_stream

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure_storage") as mock_import:
            mock_BlobServiceClient = Mock()
            mock_BlobServiceClient.from_connection_string.return_value = mock_service_client
            mock_import.return_value = mock_BlobServiceClient

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test-cert",
                account_name="myaccount",
                container="certificates",
                blob_name="ca.pem",
            )

            assert result.exists()
            assert result.name == "test-cert.pem"
            content = result.read_text()
            assert "BEGIN CERTIFICATE" in content

    def test_fetch_azure_blob_with_account_key(self, tmp_path, monkeypatch):
        """Test Azure Blob fetch with account key."""
        monkeypatch.setenv("AZURE_STORAGE_KEY", "account_key_value")

        mock_blob_client = Mock()
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b"CERT_DATA"
        mock_blob_client.download_blob.return_value = mock_download_stream

        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        with patch("bundlecraft.fetchers.azure_blob._import_azure_storage") as mock_import:
            mock_BlobServiceClient = Mock()
            mock_BlobServiceClient.return_value = mock_service_client
            mock_import.return_value = mock_BlobServiceClient

            result = fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                account_name="myaccount",
                container="certs",
                blob_name="cert.pem",
            )

            assert result.exists()

    def test_fetch_azure_blob_missing_params(self, tmp_path):
        """Test that missing required parameters raises error."""
        with pytest.raises(click.ClickException, match="requires 'account_name', 'container', and 'blob_name'"):
            fetch_azure_blob(
                dest_dir=tmp_path,
                name="test",
                account_name="account",
                container="",
                blob_name="blob",
            )

    def test_fetch_azure_blob_client_error(self, tmp_path, monkeypatch):
        """Test handling of Azure Blob client creation errors."""
        monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "invalid")

        with patch("bundlecraft.fetchers.azure_blob._import_azure_storage") as mock_import:
            mock_BlobServiceClient = Mock()
            mock_BlobServiceClient.from_connection_string.side_effect = Exception("Auth failed")
            mock_import.return_value = mock_BlobServiceClient

            with pytest.raises(click.ClickException, match="Failed to create Azure Blob client"):
                fetch_azure_blob(
                    dest_dir=tmp_path,
                    name="test",
                    account_name="account",
                    container="container",
                    blob_name="blob",
                )

    def test_import_azure_storage_missing(self, tmp_path):
        """Test that missing azure-storage-blob raises helpful error."""
        with patch("bundlecraft.fetchers.azure_blob._import_azure_storage") as mock_import:
            mock_import.side_effect = click.ClickException(
                "Azure Blob fetcher requires 'azure-storage-blob' package"
            )

            with pytest.raises(click.ClickException, match="azure-storage-blob"):
                fetch_azure_blob(
                    dest_dir=tmp_path,
                    name="test",
                    account_name="account",
                    container="container",
                    blob_name="blob",
                )


# Google Cloud Storage Tests
class TestGCSFetcher:
    """Test Google Cloud Storage fetcher."""

    def test_fetch_gcs_basic(self, tmp_path, monkeypatch):
        """Test basic GCS fetch with default credentials."""
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/creds.json")

        mock_blob = Mock()
        mock_blob.download_as_bytes.return_value = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"

        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob

        mock_client = Mock()
        mock_client.bucket.return_value = mock_bucket

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = Mock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            with patch("bundlecraft.fetchers.gcs.service_account"):
                result = fetch_gcs(
                    dest_dir=tmp_path,
                    name="test-cert",
                    bucket="my-bucket",
                    blob_name="certs/ca.pem",
                )

                assert result.exists()
                assert result.name == "test-cert.pem"
                content = result.read_text()
                assert "BEGIN CERTIFICATE" in content

    def test_fetch_gcs_with_project_id(self, tmp_path):
        """Test GCS fetch with explicit project ID."""
        mock_blob = Mock()
        mock_blob.download_as_bytes.return_value = b"CERT_DATA"

        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob

        mock_client = Mock()
        mock_client.bucket.return_value = mock_bucket

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = Mock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="bucket",
                blob_name="blob",
                project_id="my-project-123",
            )

            # Verify project_id was passed to Client
            call_kwargs = mock_storage.Client.call_args[1]
            assert call_kwargs["project"] == "my-project-123"

    def test_fetch_gcs_missing_params(self, tmp_path):
        """Test that missing required parameters raises error."""
        with pytest.raises(click.ClickException, match="requires 'bucket' and 'blob_name'"):
            fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="",
                blob_name="blob",
            )

    def test_fetch_gcs_client_error(self, tmp_path):
        """Test handling of GCS client creation errors."""
        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = Mock()
            mock_storage.Client.side_effect = Exception("Auth failed")
            mock_import.return_value = mock_storage

            with pytest.raises(click.ClickException, match="Failed to create GCS client"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    blob_name="blob",
                )

    def test_import_gcs_missing(self, tmp_path):
        """Test that missing google-cloud-storage raises helpful error."""
        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_import.side_effect = click.ClickException(
                "GCS fetcher requires 'google-cloud-storage' package"
            )

            with pytest.raises(click.ClickException, match="google-cloud-storage"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    blob_name="blob",
                )


# Azure Key Vault Tests
class TestAzureKeyVaultFetcher:
    """Test Azure Key Vault fetcher."""

    def test_fetch_azure_keyvault_basic(self, tmp_path):
        """Test basic Azure Key Vault fetch."""
        # Mock certificate data
        mock_cert_bytes = b"MOCK_DER_CERTIFICATE"

        mock_certificate = Mock()
        mock_certificate.cer = mock_cert_bytes

        mock_cert_client = Mock()
        mock_cert_client.get_certificate.return_value = mock_certificate

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import_kv:
            mock_CertificateClient = Mock()
            mock_CertificateClient.return_value = mock_cert_client
            mock_import_kv.return_value = mock_CertificateClient

            with patch("bundlecraft.fetchers.azure_keyvault._import_azure_identity") as mock_import_id:
                mock_DefaultAzureCredential = Mock()
                mock_import_id.return_value = mock_DefaultAzureCredential

                # Mock cryptography to convert DER to PEM
                with patch("bundlecraft.fetchers.azure_keyvault.x509") as mock_x509:
                    with patch("bundlecraft.fetchers.azure_keyvault.serialization") as mock_ser:
                        mock_cert_obj = Mock()
                        mock_cert_obj.public_bytes.return_value = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
                        mock_x509.load_der_x509_certificate.return_value = mock_cert_obj

                        result = fetch_azure_keyvault(
                            dest_dir=tmp_path,
                            name="test-cert",
                            vault_url="https://myvault.vault.azure.net",
                            certificate_name="my-certificate",
                        )

                        assert result.exists()
                        assert result.name == "test-cert.pem"

    def test_fetch_azure_keyvault_with_version(self, tmp_path):
        """Test Azure Key Vault fetch with specific certificate version."""
        mock_cert_bytes = b"DER_DATA"

        mock_certificate = Mock()
        mock_certificate.cer = mock_cert_bytes

        mock_cert_client = Mock()
        mock_cert_client.get_certificate_version.return_value = mock_certificate

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import_kv:
            mock_CertificateClient = Mock()
            mock_CertificateClient.return_value = mock_cert_client
            mock_import_kv.return_value = mock_CertificateClient

            with patch("bundlecraft.fetchers.azure_keyvault._import_azure_identity") as mock_import_id:
                mock_DefaultAzureCredential = Mock()
                mock_import_id.return_value = mock_DefaultAzureCredential

                with patch("bundlecraft.fetchers.azure_keyvault.x509") as mock_x509:
                    with patch("bundlecraft.fetchers.azure_keyvault.serialization"):
                        mock_cert_obj = Mock()
                        mock_cert_obj.public_bytes.return_value = b"PEM_DATA"
                        mock_x509.load_der_x509_certificate.return_value = mock_cert_obj

                        fetch_azure_keyvault(
                            dest_dir=tmp_path,
                            name="test",
                            vault_url="https://myvault.vault.azure.net",
                            certificate_name="cert",
                            version="abc123",
                        )

                        # Verify get_certificate_version was called with version
                        mock_cert_client.get_certificate_version.assert_called_once_with(
                            certificate_name="cert",
                            version="abc123",
                        )

    def test_fetch_azure_keyvault_with_service_principal(self, tmp_path, monkeypatch):
        """Test Azure Key Vault fetch with service principal credentials."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "client-secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")

        mock_cert_bytes = b"DER_DATA"
        mock_certificate = Mock()
        mock_certificate.cer = mock_cert_bytes

        mock_cert_client = Mock()
        mock_cert_client.get_certificate.return_value = mock_certificate

        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import_kv:
            mock_CertificateClient = Mock()
            mock_CertificateClient.return_value = mock_cert_client
            mock_import_kv.return_value = mock_CertificateClient

            with patch("bundlecraft.fetchers.azure_keyvault._import_azure_identity"):
                with patch("bundlecraft.fetchers.azure_keyvault.ClientSecretCredential") as mock_cred:
                    with patch("bundlecraft.fetchers.azure_keyvault.x509") as mock_x509:
                        with patch("bundlecraft.fetchers.azure_keyvault.serialization"):
                            mock_cert_obj = Mock()
                            mock_cert_obj.public_bytes.return_value = b"PEM_DATA"
                            mock_x509.load_der_x509_certificate.return_value = mock_cert_obj

                            fetch_azure_keyvault(
                                dest_dir=tmp_path,
                                name="test",
                                vault_url="https://myvault.vault.azure.net",
                                certificate_name="cert",
                            )

                            # Verify ClientSecretCredential was used
                            mock_cred.assert_called_once_with(
                                tenant_id="tenant-id",
                                client_id="client-id",
                                client_secret="client-secret",
                            )

    def test_fetch_azure_keyvault_missing_params(self, tmp_path):
        """Test that missing required parameters raises error."""
        with pytest.raises(click.ClickException, match="requires 'vault_url' and 'certificate_name'"):
            fetch_azure_keyvault(
                dest_dir=tmp_path,
                name="test",
                vault_url="",
                certificate_name="cert",
            )

    def test_import_azure_keyvault_missing(self, tmp_path):
        """Test that missing azure-keyvault-certificates raises helpful error."""
        with patch("bundlecraft.fetchers.azure_keyvault._import_azure_keyvault") as mock_import:
            mock_import.side_effect = click.ClickException(
                "Azure Key Vault fetcher requires 'azure-keyvault-certificates' package"
            )

            with pytest.raises(click.ClickException, match="azure-keyvault-certificates"):
                fetch_azure_keyvault(
                    dest_dir=tmp_path,
                    name="test",
                    vault_url="https://vault.azure.net",
                    certificate_name="cert",
                )
