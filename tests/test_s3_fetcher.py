"""
Comprehensive tests for S3 fetcher.

Tests for:
- Basic S3 object fetching
- Authentication via access keys and IAM roles
- Custom endpoint URLs (S3-compatible services)
- Region configuration
- Timeout and retry configuration
- Error handling (missing bucket, key, auth errors)
- Verification options
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from bundlecraft.fetchers.s3 import fetch_s3


def create_mock_s3_client():
    """Create a mock S3 client."""
    mock_client = Mock()
    mock_response = {
        "Body": Mock(read=Mock(return_value=b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"))
    }
    mock_client.get_object = Mock(return_value=mock_response)
    return mock_client


class TestS3FetcherBasic:
    """Test basic S3 fetching functionality."""

    def test_fetch_s3_basic(self, tmp_path, monkeypatch):
        """Test basic S3 object fetch."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            # Mock botocore.config.Config
            with patch("bundlecraft.fetchers.s3.Config") as mock_config:
                mock_config.return_value = Mock()

                result = fetch_s3(
                    dest_dir=tmp_path,
                    name="test-cert",
                    bucket="my-bucket",
                    key="certs/ca.pem",
                )

                assert result.exists()
                assert result.name == "test-cert.pem"
                content = result.read_text()
                assert "BEGIN CERTIFICATE" in content

    def test_fetch_s3_with_pem_extension(self, tmp_path, monkeypatch):
        """Test that .pem extension is not duplicated."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                result = fetch_s3(
                    dest_dir=tmp_path,
                    name="test-cert.pem",
                    bucket="my-bucket",
                    key="certs/ca.pem",
                )

                assert result.name == "test-cert.pem"


class TestS3FetcherAuthentication:
    """Test S3 authentication methods."""

    def test_fetch_with_explicit_credentials(self, tmp_path, monkeypatch):
        """Test S3 fetch with explicit access keys."""
        monkeypatch.setenv("CUSTOM_ACCESS_KEY", "custom_key")
        monkeypatch.setenv("CUSTOM_SECRET_KEY", "custom_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                result = fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                    access_key_id_ref="CUSTOM_ACCESS_KEY",
                    secret_access_key_ref="CUSTOM_SECRET_KEY",
                )

                assert result.exists()

    def test_fetch_with_session_token(self, tmp_path, monkeypatch):
        """Test S3 fetch with temporary credentials (session token)."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "test_token")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                result = fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                )

                assert result.exists()

    def test_fetch_with_iam_role(self, tmp_path, monkeypatch):
        """Test S3 fetch using IAM role (no explicit credentials)."""
        # Ensure no credentials in environment
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                result = fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                )

                assert result.exists()

    def test_fetch_with_partial_credentials_fails(self, tmp_path, monkeypatch):
        """Test that providing only access key or secret key fails."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                with pytest.raises(click.ClickException, match="Both AWS access key ID"):
                    fetch_s3(
                        dest_dir=tmp_path,
                        name="test",
                        bucket="bucket",
                        key="key",
                    )


class TestS3FetcherConfiguration:
    """Test S3 configuration options."""

    def test_fetch_with_custom_region(self, tmp_path, monkeypatch):
        """Test S3 fetch with custom region."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config") as mock_config:
                mock_config.return_value = Mock()

                fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                    region="eu-west-1",
                )

                # Verify region was passed to Config
                call_kwargs = mock_config.call_args[1]
                assert call_kwargs["region_name"] == "eu-west-1"

    def test_fetch_with_custom_endpoint(self, tmp_path, monkeypatch):
        """Test S3 fetch with custom endpoint (e.g., MinIO)."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                    endpoint_url="https://minio.example.com",
                )

                # Verify endpoint_url was passed to client
                call_kwargs = mock_boto3.client.call_args[1]
                assert call_kwargs["endpoint_url"] == "https://minio.example.com"

    def test_fetch_respects_timeout_config(self, tmp_path, monkeypatch):
        """Test that timeout configuration is respected."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config") as mock_config:
                mock_config.return_value = Mock()

                fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                    timeout=60,
                )

                # Verify timeout was passed to Config
                call_kwargs = mock_config.call_args[1]
                assert call_kwargs["connect_timeout"] == 60
                assert call_kwargs["read_timeout"] == 60

    def test_fetch_respects_retry_config(self, tmp_path, monkeypatch):
        """Test that retry configuration is respected."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config") as mock_config:
                mock_config.return_value = Mock()

                fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                    retries=5,
                )

                # Verify retries was passed to Config (max_attempts = retries + 1)
                call_kwargs = mock_config.call_args[1]
                assert call_kwargs["retries"]["max_attempts"] == 6


class TestS3FetcherErrors:
    """Test S3 error handling."""

    def test_fetch_missing_bucket_or_key(self, tmp_path):
        """Test that missing bucket or key raises error."""
        with pytest.raises(click.ClickException, match="requires 'bucket' and 'key'"):
            fetch_s3(
                dest_dir=tmp_path,
                name="test",
                bucket="bucket",
                key="",
            )

    def test_fetch_client_creation_failure(self, tmp_path, monkeypatch):
        """Test handling of S3 client creation errors."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.side_effect = Exception("Connection failed")
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                with pytest.raises(click.ClickException, match="Failed to create S3 client"):
                    fetch_s3(
                        dest_dir=tmp_path,
                        name="test",
                        bucket="bucket",
                        key="key",
                    )

    def test_fetch_object_not_found(self, tmp_path, monkeypatch):
        """Test handling of missing S3 object."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = Mock()
        mock_client.get_object.side_effect = Exception("NoSuchKey")

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                with pytest.raises(click.ClickException, match="Failed to fetch from S3"):
                    fetch_s3(
                        dest_dir=tmp_path,
                        name="test",
                        bucket="bucket",
                        key="nonexistent.pem",
                    )

    def test_import_boto3_missing(self, tmp_path):
        """Test that missing boto3 raises helpful error."""
        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_import.side_effect = click.ClickException(
                "S3 fetcher requires 'boto3' package"
            )

            with pytest.raises(click.ClickException, match="boto3"):
                fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                )


class TestS3FetcherVerification:
    """Test S3 TLS verification options."""

    def test_fetch_with_custom_ca_file(self, tmp_path, monkeypatch):
        """Test S3 fetch with custom CA certificate."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        mock_client = create_mock_s3_client()

        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_boto3 = Mock()
            mock_boto3.client.return_value = mock_client
            mock_import.return_value = mock_boto3

            with patch("bundlecraft.fetchers.s3.Config"):
                fetch_s3(
                    dest_dir=tmp_path,
                    name="test",
                    bucket="bucket",
                    key="key",
                    verify={"ca_file": "/path/to/ca.pem"},
                )

                # Verify custom CA was passed to client
                call_kwargs = mock_boto3.client.call_args[1]
                assert call_kwargs["verify"] == "/path/to/ca.pem"
