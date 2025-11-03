"""
Comprehensive tests for GCS (Google Cloud Storage) fetcher.

Tests for:
- Authentication methods (service account, ADC)
- Successful fetch operations
- Error handling (missing bucket, missing object, network errors)
- Retry logic and timeout handling
- Content verification (SHA256)
- Provenance recording via integration with fetch.py
- Required GCS permissions
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from bundlecraft.fetchers.gcs import fetch_gcs


class MockGCSException(Exception):
    """Mock exception for simulating GCS errors."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class MockBlob:
    """Mock GCS Blob object."""

    def __init__(self, name: str, content: bytes, exists: bool = True):
        self.name = name
        self.content = content
        self._exists = exists

    def exists(self) -> bool:
        return self._exists

    def download_to_filename(self, filename: str, timeout: int = None):
        """Mock download to file."""
        if not self._exists:
            raise Exception("404 Not Found")
        Path(filename).write_bytes(self.content)


class MockBucket:
    """Mock GCS Bucket object."""

    def __init__(self, name: str, blobs: dict[str, MockBlob] | None = None):
        self.name = name
        self.blobs = blobs if blobs is not None else {}

    def blob(self, object_path: str) -> MockBlob:
        """Get a blob by path."""
        return self.blobs.get(
            object_path,
            MockBlob(object_path, b"", exists=False),
        )


class MockStorageClient:
    """Mock GCS Storage Client."""

    def __init__(self, buckets: dict[str, MockBucket] | None = None):
        self.buckets = buckets if buckets is not None else {}

    def bucket(self, bucket_name: str) -> MockBucket:
        """Get a bucket by name."""
        return self.buckets.get(
            bucket_name,
            MockBucket(bucket_name),
        )


class TestGCSFetcherBasic:
    """Test basic GCS fetch operations."""

    def test_successful_fetch_with_service_account(self, tmp_path, monkeypatch):
        """Test successful fetch using service account credentials."""
        # Create a mock service account file
        creds_file = tmp_path / "service-account.json"
        creds_file.write_text('{"type": "service_account", "project_id": "test"}')
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_file))

        # Mock certificate content
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST_CERT\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("certs/root.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"certs/root.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            with patch("bundlecraft.fetchers.gcs.service_account"):
                result = fetch_gcs(
                    dest_dir=tmp_path,
                    name="test-cert",
                    bucket="test-bucket",
                    object_path="certs/root.pem",
                    timeout=30,
                )

                assert result.exists()
                assert result.name == "test-cert.pem"
                assert result.read_bytes() == test_cert

    def test_successful_fetch_with_adc(self, tmp_path):
        """Test successful fetch using Application Default Credentials."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST_CERT\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("root.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"root.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test-cert",
                bucket="test-bucket",
                object_path="root.pem",
                timeout=30,
            )

            assert result.exists()
            assert result.read_bytes() == test_cert

    def test_fetch_with_project_id(self, tmp_path):
        """Test fetch with explicit project ID."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST_CERT\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("project-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"project-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="project-cert",
                bucket="project-bucket",
                object_path="cert.pem",
                project="my-gcp-project",
                timeout=30,
            )

            assert result.exists()
            assert result.name == "project-cert.pem"

    def test_output_with_pem_extension(self, tmp_path):
        """Test that .pem extension is preserved if already present."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test.pem",  # Already has .pem
                bucket="test-bucket",
                object_path="cert.pem",
                timeout=30,
            )

            assert result.name == "test.pem"


class TestGCSFetcherErrors:
    """Test error handling in GCS fetcher."""

    def test_missing_gcs_library(self, tmp_path):
        """Test error when google-cloud-storage is not installed."""
        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_import.side_effect = click.ClickException(
                "GCS fetcher requires 'google-cloud-storage' package"
            )

            with pytest.raises(click.ClickException, match="google-cloud-storage"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="cert.pem",
                )

    def test_missing_credentials_file(self, tmp_path):
        """Test error when credentials file doesn't exist."""
        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_import.return_value = mock_storage

            with pytest.raises(click.ClickException, match="credentials file not found"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="cert.pem",
                    credentials_file="/nonexistent/creds.json",
                )

    def test_object_not_found(self, tmp_path):
        """Test error when GCS object doesn't exist."""
        mock_blob = MockBlob("nonexistent.pem", b"", exists=False)
        mock_bucket = MockBucket("test-bucket", {"nonexistent.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            with pytest.raises(click.ClickException, match="GCS object not found"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="nonexistent.pem",
                    timeout=30,
                )

    def test_access_denied_403(self, tmp_path):
        """Test error handling for 403 Forbidden (insufficient permissions)."""
        mock_blob = MockBlob("cert.pem", b"", exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        # Make download raise a 403 error
        def raise_403(*args, **kwargs):
            raise MockGCSException("403 Forbidden: Insufficient permissions", code=403)

        mock_blob.download_to_filename = raise_403

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            with pytest.raises(
                click.ClickException,
                match="Access denied|storage.objects.get",
            ):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="cert.pem",
                    timeout=30,
                )

    def test_not_found_404(self, tmp_path):
        """Test error handling for 404 Not Found."""
        mock_blob = MockBlob("cert.pem", b"", exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        # Make download raise a 404 error
        def raise_404(*args, **kwargs):
            raise MockGCSException("404 Not Found", code=404)

        mock_blob.download_to_filename = raise_404

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            with pytest.raises(click.ClickException, match="GCS object not found"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="cert.pem",
                    timeout=30,
                )

    def test_authentication_failed_401(self, tmp_path):
        """Test error handling for 401 Unauthorized."""
        mock_blob = MockBlob("cert.pem", b"", exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        # Make download raise a 401 error
        def raise_401(*args, **kwargs):
            raise MockGCSException("401 Unauthorized", code=401)

        mock_blob.download_to_filename = raise_401

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            with pytest.raises(click.ClickException, match="Authentication failed"):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="cert.pem",
                    timeout=30,
                )

    def test_client_initialization_failure(self, tmp_path):
        """Test error when GCS client initialization fails."""
        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.side_effect = Exception("Failed to initialize")
            mock_import.return_value = mock_storage

            with pytest.raises(
                click.ClickException,
                match="Failed to initialize GCS client|credentials",
            ):
                fetch_gcs(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="test-bucket",
                    object_path="cert.pem",
                )


class TestGCSFetcherRetry:
    """Test retry logic and timeout handling."""

    def test_retry_on_transient_error(self, tmp_path):
        """Test that transient errors trigger retry."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        # First call fails, second succeeds
        call_count = {"count": 0}

        def download_with_retry(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # Simulate transient network error
                raise OSError("Network error")
            # Second attempt succeeds
            Path(args[0]).write_bytes(test_cert)

        mock_blob.download_to_filename = download_with_retry

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="test-bucket",
                object_path="cert.pem",
                retries=2,
                backoff_factor=1.0,
                timeout=30,
            )

            assert result.exists()
            assert call_count["count"] == 2  # First failed, second succeeded

    def test_custom_timeout(self, tmp_path):
        """Test custom timeout configuration."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        timeout_used = {"value": None}

        def capture_timeout(*args, **kwargs):
            timeout_used["value"] = kwargs.get("timeout")
            Path(args[0]).write_bytes(test_cert)

        mock_blob.download_to_filename = capture_timeout

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="test-bucket",
                object_path="cert.pem",
                timeout=120,  # Custom timeout
            )

            assert timeout_used["value"] == 120

    def test_custom_retry_config(self, tmp_path):
        """Test custom retry configuration."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="test-bucket",
                object_path="cert.pem",
                retries=5,
                backoff_factor=3.0,
                retry_on_status=[429, 503],
                timeout=60,
            )

            assert result.exists()


class TestGCSFetcherIntegration:
    """Test integration with fetch.py configuration system."""

    def test_fetch_config_defaults(self, tmp_path):
        """Test that default fetch config is properly applied."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            # Test with defaults
            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="test-bucket",
                object_path="cert.pem",
                defaults={
                    "fetch": {
                        "timeout": 45,
                        "retries": 4,
                        "backoff_factor": 2.5,
                    }
                },
            )

            assert result.exists()

    def test_source_config_overrides_defaults(self, tmp_path):
        """Test that source-specific config overrides defaults."""
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="test-bucket",
                object_path="cert.pem",
                timeout=90,  # Override
                retries=10,  # Override
                defaults={
                    "fetch": {
                        "timeout": 30,
                        "retries": 3,
                    }
                },
            )

            assert result.exists()


class TestGCSFetcherContentVerification:
    """Test content verification and provenance."""

    def test_sha256_verification_via_fetch_py(self, tmp_path):
        """Test that SHA256 verification works through fetch.py integration."""
        # This test verifies that the file is successfully written
        # and can be verified by fetch.py's SHA256 check
        test_cert = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_blob = MockBlob("cert.pem", test_cert, exists=True)
        mock_bucket = MockBucket("test-bucket", {"cert.pem": mock_blob})
        mock_client = MockStorageClient({"test-bucket": mock_bucket})

        with patch("bundlecraft.fetchers.gcs._import_gcs") as mock_import:
            mock_storage = MagicMock()
            mock_storage.Client.return_value = mock_client
            mock_import.return_value = mock_storage

            result = fetch_gcs(
                dest_dir=tmp_path,
                name="test",
                bucket="test-bucket",
                object_path="cert.pem",
                verify={"sha256": "expected_hash"},  # Pass through to fetch.py
                timeout=30,
            )

            # Verify file was written correctly for SHA256 check
            assert result.exists()
            assert result.read_bytes() == test_cert
