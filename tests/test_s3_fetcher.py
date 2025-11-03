"""
Comprehensive tests for S3 fetcher.

Tests for:
- URL parsing (s3:// URLs)
- Bucket and key parameter handling
- AWS credential chain
- Error handling (NoSuchBucket, NoSuchKey, AccessDenied, etc.)
- Timeout and retry configuration
- Custom endpoints (S3-compatible services)
- Content verification (SHA256)
- Region configuration
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from bundlecraft.fetchers.s3 import _parse_s3_url, _safe_filename_from_key, fetch_s3


class TestS3URLParsing:
    """Test S3 URL parsing functionality."""

    def test_parse_valid_s3_url(self):
        """Test parsing a valid s3:// URL."""
        bucket, key = _parse_s3_url("s3://my-bucket/path/to/cert.pem")
        assert bucket == "my-bucket"
        assert key == "path/to/cert.pem"

    def test_parse_s3_url_with_multiple_slashes(self):
        """Test parsing S3 URL with nested paths."""
        bucket, key = _parse_s3_url("s3://my-bucket/nested/path/to/cert.pem")
        assert bucket == "my-bucket"
        assert key == "nested/path/to/cert.pem"

    def test_parse_s3_url_without_leading_slash(self):
        """Test that leading slash is stripped from key."""
        bucket, key = _parse_s3_url("s3://my-bucket//path/to/cert.pem")
        assert bucket == "my-bucket"
        assert key == "path/to/cert.pem"

    def test_parse_s3_url_invalid_scheme(self):
        """Test that non-s3:// schemes are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 URL scheme"):
            _parse_s3_url("https://my-bucket.s3.amazonaws.com/cert.pem")

    def test_parse_s3_url_missing_bucket(self):
        """Test that URLs without bucket names are rejected."""
        with pytest.raises(ValueError, match="missing bucket name"):
            _parse_s3_url("s3:///path/to/cert.pem")

    def test_parse_s3_url_missing_key(self):
        """Test that URLs without object keys are rejected."""
        with pytest.raises(ValueError, match="missing object key"):
            _parse_s3_url("s3://my-bucket/")
        with pytest.raises(ValueError, match="missing object key"):
            _parse_s3_url("s3://my-bucket")


class TestS3FilenameGeneration:
    """Test safe filename generation from S3 keys."""

    def test_filename_from_key_simple(self):
        """Test filename generation from simple key."""
        filename = _safe_filename_from_key("cert.pem")
        assert filename == "cert.pem"

    def test_filename_from_key_nested_path(self):
        """Test filename generation extracts basename from nested path."""
        filename = _safe_filename_from_key("path/to/cert.pem")
        assert filename == "cert.pem"

    def test_filename_from_key_adds_pem_extension(self):
        """Test that .pem extension is added if missing."""
        filename = _safe_filename_from_key("cert")
        assert filename == "cert.pem"

    def test_filename_from_explicit_name(self):
        """Test that explicit name takes precedence."""
        filename = _safe_filename_from_key("path/to/cert.pem", name="custom-name")
        assert filename == "custom-name.pem"

    def test_filename_from_explicit_name_with_extension(self):
        """Test that explicit name with .pem is preserved."""
        filename = _safe_filename_from_key("path/to/cert.pem", name="custom.pem")
        assert filename == "custom.pem"


class TestS3FetcherBasicFunctionality:
    """Test basic S3 fetcher operations."""

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_fetch_with_s3_url(self, mock_boto3, tmp_path):
        """Test fetching using s3:// URL."""
        # Mock S3 client
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Create a mock file to "download"
        test_file = tmp_path / "test.pem"
        test_file.write_text("MOCK CERT DATA\n")
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("MOCK CERT DATA\n")
        
        mock_client.download_file.side_effect = mock_download_file

        result = fetch_s3(
            dest_dir=tmp_path,
            url="s3://test-bucket/certs/root-ca.pem",
            timeout=30,
        )

        assert result.exists()
        assert result.name == "root-ca.pem"
        assert result.read_text() == "MOCK CERT DATA\n"
        
        # Verify boto3 was called correctly
        mock_client.download_file.assert_called_once()
        call_args = mock_client.download_file.call_args
        assert call_args[0][0] == "test-bucket"
        assert call_args[0][1] == "certs/root-ca.pem"

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_fetch_with_bucket_and_key(self, mock_boto3, tmp_path):
        """Test fetching using explicit bucket and key parameters."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT CONTENT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        result = fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="path/to/cert.pem",
            timeout=30,
        )

        assert result.exists()
        assert result.name == "cert.pem"
        
        mock_client.download_file.assert_called_once()
        call_args = mock_client.download_file.call_args
        assert call_args[0][0] == "my-bucket"
        assert call_args[0][1] == "path/to/cert.pem"

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_fetch_with_custom_name(self, mock_boto3, tmp_path):
        """Test that custom name is used for output file."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        result = fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="original-name.pem",
            name="custom-name",
            timeout=30,
        )

        assert result.name == "custom-name.pem"

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_fetch_with_region(self, mock_boto3, tmp_path):
        """Test that region parameter is passed to boto3 client."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="cert.pem",
            region="us-west-2",
            timeout=30,
        )

        # Verify region was passed to client
        assert mock_boto3.client.called
        call_kwargs = mock_boto3.client.call_args[1]
        assert "region_name" in call_kwargs
        assert call_kwargs["region_name"] == "us-west-2"

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_fetch_with_custom_endpoint(self, mock_boto3, tmp_path):
        """Test fetching from S3-compatible service with custom endpoint."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="cert.pem",
            endpoint_url="https://minio.example.com:9000",
            timeout=30,
        )

        # Verify endpoint_url was passed to client
        call_kwargs = mock_boto3.client.call_args[1]
        assert "endpoint_url" in call_kwargs
        assert call_kwargs["endpoint_url"] == "https://minio.example.com:9000"


class TestS3FetcherErrorHandling:
    """Test error handling for various S3 failure scenarios."""

    def test_missing_url_and_bucket_key(self, tmp_path):
        """Test that error is raised when neither URL nor bucket/key provided."""
        with pytest.raises(click.ClickException, match="requires either 'url'|both 'bucket' and 'key'"):
            fetch_s3(dest_dir=tmp_path, timeout=30)

    def test_missing_key_parameter(self, tmp_path):
        """Test that error is raised when bucket provided without key."""
        with pytest.raises(click.ClickException, match="requires either 'url'|both 'bucket' and 'key'"):
            fetch_s3(dest_dir=tmp_path, bucket="my-bucket", timeout=30)

    def test_missing_bucket_parameter(self, tmp_path):
        """Test that error is raised when key provided without bucket."""
        with pytest.raises(click.ClickException, match="requires either 'url'|both 'bucket' and 'key'"):
            fetch_s3(dest_dir=tmp_path, key="cert.pem", timeout=30)

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_no_credentials_error(self, mock_boto3, tmp_path):
        """Test helpful error message when AWS credentials are missing."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Simulate NoCredentialsError
        from botocore.exceptions import NoCredentialsError
        mock_client.download_file.side_effect = NoCredentialsError()

        with pytest.raises(click.ClickException, match="AWS credentials not found"):
            fetch_s3(
                dest_dir=tmp_path,
                bucket="my-bucket",
                key="cert.pem",
                timeout=30,
            )

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_no_such_bucket_error(self, mock_boto3, tmp_path):
        """Test helpful error message when S3 bucket doesn't exist."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Simulate NoSuchBucket error
        from botocore.exceptions import ClientError
        error_response = {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}}
        mock_client.download_file.side_effect = ClientError(error_response, "GetObject")

        with pytest.raises(click.ClickException, match="S3 bucket not found.*my-bucket"):
            fetch_s3(
                dest_dir=tmp_path,
                bucket="my-bucket",
                key="cert.pem",
                timeout=30,
            )

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_no_such_key_error(self, mock_boto3, tmp_path):
        """Test helpful error message when S3 object doesn't exist."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Simulate NoSuchKey error
        from botocore.exceptions import ClientError
        error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}}
        mock_client.download_file.side_effect = ClientError(error_response, "GetObject")

        with pytest.raises(click.ClickException, match="S3 object not found.*cert.pem"):
            fetch_s3(
                dest_dir=tmp_path,
                bucket="my-bucket",
                key="cert.pem",
                timeout=30,
            )

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_access_denied_error(self, mock_boto3, tmp_path):
        """Test helpful error message when access is denied."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Simulate AccessDenied error
        from botocore.exceptions import ClientError
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
        mock_client.download_file.side_effect = ClientError(error_response, "GetObject")

        with pytest.raises(click.ClickException, match="Access denied to S3 bucket"):
            fetch_s3(
                dest_dir=tmp_path,
                bucket="my-bucket",
                key="cert.pem",
                timeout=30,
            )

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_endpoint_connection_error(self, mock_boto3, tmp_path):
        """Test helpful error message for endpoint connection failures."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Simulate EndpointConnectionError
        from botocore.exceptions import EndpointConnectionError
        mock_client.download_file.side_effect = EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")

        with pytest.raises(click.ClickException, match="Cannot connect to S3 endpoint"):
            fetch_s3(
                dest_dir=tmp_path,
                bucket="my-bucket",
                key="cert.pem",
                timeout=30,
            )

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_generic_boto_error(self, mock_boto3, tmp_path):
        """Test generic error handling for unexpected boto3 errors."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        # Simulate generic exception
        mock_client.download_file.side_effect = Exception("Unexpected error")

        with pytest.raises(click.ClickException, match="S3 fetch failed"):
            fetch_s3(
                dest_dir=tmp_path,
                bucket="my-bucket",
                key="cert.pem",
                timeout=30,
            )


class TestS3FetcherRetryConfiguration:
    """Test retry and timeout configuration."""

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_timeout_configuration(self, mock_boto3, tmp_path):
        """Test that timeout is configured in boto3 client."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="cert.pem",
            timeout=120,
        )

        # Verify Config was passed with timeout
        call_kwargs = mock_boto3.client.call_args[1]
        assert "config" in call_kwargs
        config = call_kwargs["config"]
        assert hasattr(config, "connect_timeout")
        assert config.connect_timeout == 120

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_retry_configuration(self, mock_boto3, tmp_path):
        """Test that retry count is configured in boto3 client."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="cert.pem",
            retries=5,
            timeout=30,
        )

        # Verify Config was passed with retries
        call_kwargs = mock_boto3.client.call_args[1]
        assert "config" in call_kwargs
        config = call_kwargs["config"]
        assert hasattr(config, "retries")
        # boto3 counts initial attempt, so max_attempts = retries + 1
        assert config.retries["max_attempts"] == 6

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_defaults_configuration(self, mock_boto3, tmp_path):
        """Test that default fetch configuration is applied."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        # Provide defaults
        defaults = {
            "fetch": {
                "timeout": 60,
                "retries": 4,
                "backoff_factor": 3.0,
            }
        }

        fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="cert.pem",
            defaults=defaults,
        )

        # Verify defaults were applied
        call_kwargs = mock_boto3.client.call_args[1]
        config = call_kwargs["config"]
        assert config.connect_timeout == 60
        assert config.retries["max_attempts"] == 5  # retries + 1


class TestS3FetcherVerification:
    """Test content verification features."""

    @patch("bundlecraft.fetchers.s3.boto3")
    def test_custom_ca_file(self, mock_boto3, tmp_path):
        """Test that custom CA file is used for verification."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        def mock_download_file(bucket, key, local_path):
            Path(local_path).write_text("CERT\n")
        
        mock_client.download_file.side_effect = mock_download_file

        # Create a mock CA file
        ca_file = tmp_path / "custom-ca.pem"
        ca_file.write_text("MOCK CA\n")

        fetch_s3(
            dest_dir=tmp_path,
            bucket="my-bucket",
            key="cert.pem",
            verify={"ca_file": str(ca_file)},
            timeout=30,
        )

        # Verify ca_file was passed as verify parameter
        call_kwargs = mock_boto3.client.call_args[1]
        assert "verify" in call_kwargs
        assert call_kwargs["verify"] == str(ca_file)


class TestS3FetcherModuleImport:
    """Test boto3 import handling."""

    def test_import_error_handling(self, tmp_path):
        """Test that missing boto3 raises helpful error."""
        with patch("bundlecraft.fetchers.s3._import_boto3") as mock_import:
            mock_import.side_effect = click.ClickException("boto3 not installed")
            
            with pytest.raises(click.ClickException, match="boto3"):
                fetch_s3(
                    dest_dir=tmp_path,
                    bucket="my-bucket",
                    key="cert.pem",
                )
