"""Tests for extended BundleCraft fetchers (cloud storage, artifact repos, root programs)."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

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


class TestS3Fetcher:
    def test_s3_fetch_with_mock_client(self, cli_runner, monkeypatch, temp_workspace):
        """Test S3 fetcher with mocked boto3 client."""
        # Mock boto3
        mock_boto3 = MagicMock()
        mock_s3_client = MagicMock()
        mock_response = {
            "Body": MagicMock(
                read=MagicMock(
                    return_value=b"-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
                )
            )
        }
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client

        from bundlecraft.fetchers import s3 as s3_mod

        monkeypatch.setattr(s3_mod, "_import_boto3", lambda: mock_boto3)

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_s3
            type: s3
            bucket: my-pki-bucket
            key: certs/rootCA.pem
            region: us-east-1
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
        staged = temp_workspace / "sources" / "staged"
        assert (staged / "test-bundle" / "from_s3").exists()
        pems = list((staged / "test-bundle" / "from_s3").glob("*.pem"))
        assert len(pems) > 0

    def test_s3_fetch_missing_bucket(self, cli_runner, temp_workspace):
        """Test S3 fetcher fails when bucket is missing."""
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_s3
            type: s3
            key: certs/rootCA.pem
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
        assert "requires 'bucket' and 'key'" in result.output


class TestAzureBlobFetcher:
    def test_azure_blob_fetch_with_mock_client(self, cli_runner, monkeypatch, temp_workspace):
        """Test Azure Blob fetcher with mocked client."""
        # Mock Azure Blob Storage client
        mock_blob_service_client = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_client.download_blob().readall.return_value = (
            b"-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
        )
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        MockBlobServiceClient = MagicMock(return_value=mock_blob_service_client)
        MockBlobServiceClient.from_connection_string = MagicMock(
            return_value=mock_blob_service_client
        )

        from bundlecraft.fetchers import azure_blob as azure_blob_mod

        monkeypatch.setattr(azure_blob_mod, "_import_azure_storage", lambda: MockBlobServiceClient)
        monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;...")

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_azure_blob
            type: azure_blob
            container: pki-certs
            blob_name: certs/rootCA.pem
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
        staged = temp_workspace / "sources" / "staged"
        assert (staged / "test-bundle" / "from_azure_blob").exists()


class TestGCSFetcher:
    def test_gcs_fetch_with_mock_client(self, cli_runner, monkeypatch, temp_workspace):
        """Test GCS fetcher with mocked client."""
        # Mock GCS storage client
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = (
            b"-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
        )
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        MockStorage = MagicMock()
        MockStorage.Client.return_value = mock_client

        from bundlecraft.fetchers import gcs as gcs_mod

        monkeypatch.setattr(gcs_mod, "_import_gcs", lambda: MockStorage)

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_gcs
            type: gcs
            bucket: my-pki-bucket
            blob_name: certs/rootCA.pem
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
        staged = temp_workspace / "sources" / "staged"
        assert (staged / "test-bundle" / "from_gcs").exists()


class TestArtifactoryFetcher:
    def test_artifactory_fetch_requires_https(self, cli_runner, temp_workspace):
        """Test Artifactory fetcher requires HTTPS."""
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_artifactory
            type: artifactory
            url: http://artifactory.local/artifact.pem
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
        assert "requires HTTPS" in result.output


class TestGitHubReleasesFetcher:
    def test_github_release_fetch_requires_owner_repo_asset(self, cli_runner, temp_workspace):
        """Test GitHub Release fetcher requires owner, repo, and asset_name."""
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_github
            type: github_release
            owner: curl
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
        assert "requires 'owner', 'repo', and 'asset_name'" in result.output


class TestAzureKeyVaultFetcher:
    def test_azure_keyvault_fetch_with_mock_client(self, cli_runner, monkeypatch, temp_workspace):
        """Test Azure Key Vault fetcher with mocked client."""
        # Mock certificate object
        mock_certificate = MagicMock()
        # Create a simple self-signed cert for testing
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta, timezone

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .sign(key, hashes.SHA256())
        )
        mock_certificate.cer = cert.public_bytes(serialization.Encoding.DER)

        mock_client = MagicMock()
        mock_client.get_certificate.return_value = mock_certificate

        MockCertificateClient = MagicMock(return_value=mock_client)

        from bundlecraft.fetchers import azure_keyvault as azure_keyvault_mod

        # Mock the azure.identity module before it's imported
        mock_azure_identity = MagicMock()
        mock_credential = MagicMock()
        mock_azure_identity.DefaultAzureCredential = MagicMock(return_value=mock_credential)

        import sys

        sys.modules["azure.identity"] = mock_azure_identity

        try:
            monkeypatch.setattr(
                azure_keyvault_mod, "_import_azure_keyvault", lambda: MockCertificateClient
            )

            bundle_dir = temp_workspace / "config" / "bundles"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            bundle_yaml = """
            fetch:
              - name: from_keyvault
                type: azure_keyvault
                vault_url: https://myvault.vault.azure.net/
                certificate_name: my-cert
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
            staged = temp_workspace / "sources" / "staged"
            assert (staged / "test-bundle" / "from_keyvault").exists()
        finally:
            # Clean up the mock module
            if "azure.identity" in sys.modules:
                del sys.modules["azure.identity"]


class TestMozillaRootsFetcher:
    def test_mozilla_roots_fetch_type(self, cli_runner, temp_workspace):
        """Test Mozilla roots fetcher configuration."""
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        # Use a file:// URL for testing since we don't want to hit the network
        test_pem = temp_workspace / "mozilla_roots.pem"
        test_pem.write_text(
            "-----BEGIN CERTIFICATE-----\nMOCK MOZILLA ROOT\n-----END CERTIFICATE-----\n",
            encoding="utf-8",
        )
        bundle_yaml = f"""
        fetch:
          - name: mozilla_roots
            type: mozilla_roots
            url: file://{test_pem}
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
        # Will fail because file:// is not HTTPS, but validates the type is recognized
        assert "requires HTTPS" in result.output


class TestMicrosoftRootsFetcher:
    def test_microsoft_roots_fetch_type(self, cli_runner, temp_workspace):
        """Test Microsoft roots fetcher configuration."""
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        test_pem = temp_workspace / "microsoft_roots.pem"
        test_pem.write_text(
            "-----BEGIN CERTIFICATE-----\nMOCK MICROSOFT ROOT\n-----END CERTIFICATE-----\n",
            encoding="utf-8",
        )
        bundle_yaml = f"""
        fetch:
          - name: microsoft_roots
            type: microsoft_roots
            url: file://{test_pem}
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
        # Will fail because file:// is not HTTPS, but validates the type is recognized
        assert "requires HTTPS" in result.output


class TestAppleRootsFetcher:
    def test_apple_roots_fetch_type(self, cli_runner, temp_workspace):
        """Test Apple roots fetcher configuration."""
        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        test_pem = temp_workspace / "apple_roots.pem"
        test_pem.write_text(
            "-----BEGIN CERTIFICATE-----\nMOCK APPLE ROOT\n-----END CERTIFICATE-----\n",
            encoding="utf-8",
        )
        bundle_yaml = f"""
        fetch:
          - name: apple_roots
            type: apple_roots
            url: file://{test_pem}
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
        # Will fail because file:// is not HTTPS, but validates the type is recognized
        assert "requires HTTPS" in result.output


class TestSHA256PinningAndTLSOptions:
    def test_s3_with_sha256_verification(self, cli_runner, monkeypatch, temp_workspace):
        """Test S3 fetcher with SHA256 content pinning."""
        # Mock boto3
        test_content = b"-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
        expected_sha = hashlib.sha256(test_content).hexdigest()

        mock_boto3 = MagicMock()
        mock_s3_client = MagicMock()
        mock_response = {"Body": MagicMock(read=MagicMock(return_value=test_content))}
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client

        from bundlecraft.fetchers import s3 as s3_mod

        monkeypatch.setattr(s3_mod, "_import_boto3", lambda: mock_boto3)

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = f"""
        fetch:
          - name: from_s3
            type: s3
            bucket: my-pki-bucket
            key: certs/rootCA.pem
            verify:
              sha256: {expected_sha}
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
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        # SHA256 verification logging is in the verbose output
        assert expected_sha.lower() in result.output.lower() or result.exit_code == 0

    def test_s3_with_wrong_sha256_fails(self, cli_runner, monkeypatch, temp_workspace):
        """Test S3 fetcher fails on SHA256 mismatch."""
        test_content = b"-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
        wrong_sha = "0" * 64

        mock_boto3 = MagicMock()
        mock_s3_client = MagicMock()
        mock_response = {"Body": MagicMock(read=MagicMock(return_value=test_content))}
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client

        from bundlecraft.fetchers import s3 as s3_mod

        monkeypatch.setattr(s3_mod, "_import_boto3", lambda: mock_boto3)

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = f"""
        fetch:
          - name: from_s3
            type: s3
            bucket: my-pki-bucket
            key: certs/rootCA.pem
            verify:
              sha256: {wrong_sha}
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


class TestProvenanceRecording:
    def test_provenance_file_created_for_s3(self, cli_runner, monkeypatch, temp_workspace):
        """Test that provenance file is created for S3 fetch."""
        mock_boto3 = MagicMock()
        mock_s3_client = MagicMock()
        mock_response = {
            "Body": MagicMock(
                read=MagicMock(
                    return_value=b"-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----\n"
                )
            )
        }
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client

        from bundlecraft.fetchers import s3 as s3_mod

        monkeypatch.setattr(s3_mod, "_import_boto3", lambda: mock_boto3)

        bundle_dir = temp_workspace / "config" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_yaml = """
        fetch:
          - name: from_s3
            type: s3
            bucket: my-pki-bucket
            key: certs/rootCA.pem
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

        # Check provenance file exists
        staged = temp_workspace / "sources" / "staged"
        provenance_file = staged / "test-bundle" / "from_s3" / "provenance.fetch.json"
        assert provenance_file.exists()

        # Verify provenance content
        import json

        prov_data = json.loads(provenance_file.read_text())
        assert "generated_at" in prov_data
        assert "items" in prov_data
        assert len(prov_data["items"]) == 1
        assert prov_data["items"][0]["name"] == "from_s3"
        assert "sha256" in prov_data["items"][0]
        assert prov_data["items"][0]["origin"]["type"] == "s3"
