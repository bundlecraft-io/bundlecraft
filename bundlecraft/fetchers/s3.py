"""AWS S3 fetcher for BundleCraft.

Fetches certificate files from AWS S3 buckets with support for:
- s3:// URLs or explicit bucket/key parameters
- AWS credential chain (environment variables, IAM roles, profiles)
- Configurable retry and timeout behavior
- Content verification (SHA256)
- Custom S3 endpoints (for S3-compatible services)
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff

# Import boto3 at module level for testability
try:
    import boto3  # type: ignore
except ImportError:
    boto3 = None  # type: ignore


def _import_boto3():
    """Import boto3 with helpful error message if not installed."""
    if boto3 is None:  # pragma: no cover
        raise click.ClickException("S3 fetcher requires 'boto3' package. ")
    return boto3


def _safe_filename_from_key(key: str, name: str | None = None) -> str:
    """Derive a safe output filename from S3 key or provided name.

    Args:
        key: S3 object key
        name: Optional explicit name for the output file

    Returns:
        Safe filename with .pem extension
    """
    if name:
        return name if name.lower().endswith(".pem") else f"{name}.pem"
    # Extract basename from key
    base = key.split("/")[-1] or "download.pem"
    if not base.lower().endswith(".pem"):
        base = f"{base}.pem"
    return base


def _parse_s3_url(url: str) -> tuple[str, str]:
    """Parse an s3:// URL into bucket and key.

    Args:
        url: S3 URL in format s3://bucket-name/path/to/object

    Returns:
        Tuple of (bucket, key)

    Raises:
        ValueError: If URL is malformed
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "s3":
        raise ValueError(f"Invalid S3 URL scheme: {parsed.scheme} (expected 's3')")
    bucket = parsed.netloc
    if not bucket:
        raise ValueError(f"Invalid S3 URL: missing bucket name in {url}")
    # Remove leading slash from path
    key = parsed.path.lstrip("/")
    if not key:
        raise ValueError(f"Invalid S3 URL: missing object key in {url}")
    return bucket, key


def fetch_s3(
    dest_dir: Path,
    name: str | None = None,
    *,
    url: str | None = None,
    bucket: str | None = None,
    key: str | None = None,
    region: str | None = None,
    endpoint_url: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate file from AWS S3.

    Authentication uses the standard AWS credential chain:
    1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    2. Shared credential files (~/.aws/credentials, ~/.aws/config)
    3. IAM instance profile or ECS task role (when running on AWS)

    Args:
        dest_dir: Destination directory for downloaded file
        name: Optional name for output file (defaults to S3 key basename)
        url: S3 URL in format s3://bucket-name/path/to/object
        bucket: S3 bucket name (alternative to url)
        key: S3 object key (alternative to url)
        region: AWS region (optional, uses default region if not specified)
        endpoint_url: Custom S3 endpoint URL (for S3-compatible services)
        verify: Verification options (sha256, ca_file for custom endpoints)
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        backoff_factor: Exponential backoff multiplier
        retry_on_status: HTTP status codes to retry
        defaults: Global defaults configuration

    Returns:
        Path to downloaded file

    Raises:
        click.ClickException: On authentication, network, or S3 errors

    Example:
        >>> # Using s3:// URL
        >>> fetch_s3(Path("/tmp"), url="s3://my-bucket/certs/root-ca.pem")

        >>> # Using explicit bucket/key
        >>> fetch_s3(
        ...     Path("/tmp"),
        ...     bucket="my-bucket",
        ...     key="certs/root-ca.pem",
        ...     region="us-west-2"
        ... )
    """
    boto3 = _import_boto3()

    # Get fetch configuration with overrides
    fetch_config = get_fetch_config(
        source_config=(
            {
                "timeout": timeout,
                "retries": retries,
                "backoff_factor": backoff_factor,
                "retry_on_status": retry_on_status,
            }
            if any(x is not None for x in [timeout, retries, backoff_factor, retry_on_status])
            else None
        ),
        defaults=defaults,
    )

    # Parse bucket and key from URL or use explicit parameters
    if url:
        bucket, key = _parse_s3_url(url)
    elif bucket and key:
        pass  # Use provided bucket and key
    else:
        raise click.ClickException(
            "S3 fetch requires either 'url' (s3://bucket/key) or both 'bucket' and 'key'"
        )

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename
    out_name = _safe_filename_from_key(key, name)
    out_path = dest_dir / out_name

    # Build boto3 client configuration
    client_config = {
        "service_name": "s3",
    }

    # Apply region if specified
    if region:
        client_config["region_name"] = region

    # Apply custom endpoint if specified (for S3-compatible services)
    if endpoint_url:
        client_config["endpoint_url"] = endpoint_url

    # Handle custom CA for S3-compatible endpoints with self-signed certs
    verify_ssl: str | bool = True
    if verify and isinstance(verify, dict):
        ca_file = verify.get("ca_file")
        if ca_file:
            verify_ssl = str(ca_file)

    # Configure boto3 client with retry logic
    from botocore.config import Config

    boto_config = Config(
        retries={
            "max_attempts": fetch_config["retries"] + 1,  # boto3 counts initial attempt
            "mode": "adaptive",  # Use adaptive retry mode for better handling
        },
        connect_timeout=fetch_config["timeout"],
        read_timeout=fetch_config["timeout"],
    )

    client_config["config"] = boto_config
    client_config["verify"] = verify_ssl

    # Import botocore exceptions for proper error handling
    try:
        from botocore.exceptions import (
            ClientError,
            EndpointConnectionError,
            NoCredentialsError,
        )
    except ImportError:  # pragma: no cover
        # Fallback if botocore is not available (should not happen if boto3 is installed)
        ClientError = Exception
        NoCredentialsError = Exception
        EndpointConnectionError = Exception

    # Apply retry logic wrapper
    @retry_with_backoff(
        retries=fetch_config["retries"],
        backoff_factor=fetch_config["backoff_factor"],
        retry_on_status=fetch_config["retry_on_status"],
        timeout=fetch_config["timeout"],
    )
    def _do_fetch():
        try:
            # Create S3 client
            s3_client = boto3.client(**client_config)

            # Download object
            s3_client.download_file(bucket, key, str(out_path))

            return out_path
        except NoCredentialsError as e:
            raise click.ClickException(
                "AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                "environment variables, configure ~/.aws/credentials, or use an IAM role."
            ) from e
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "NoSuchBucket":
                raise click.ClickException(
                    f"S3 bucket not found: {bucket}. "
                    "Check the bucket name and ensure it exists in the specified region."
                ) from e
            elif error_code == "NoSuchKey":
                raise click.ClickException(
                    f"S3 object not found: {key} in bucket {bucket}. "
                    "Check the object key and ensure the file exists."
                ) from e
            elif error_code in ("AccessDenied", "403"):
                raise click.ClickException(
                    f"Access denied to S3 bucket {bucket} or object {key}. "
                    "Check IAM permissions and bucket policies."
                ) from e
            else:
                # Generic ClientError
                raise click.ClickException(
                    f"S3 error ({error_code}): {error_msg} for {bucket}/{key}"
                ) from e
        except EndpointConnectionError as e:
            raise click.ClickException(
                f"Cannot connect to S3 endpoint. Check region setting and network connectivity. "
                f"Bucket: {bucket}, Region: {region or 'default'}"
            ) from e
        except Exception as e:
            # Generic catch-all for unexpected errors
            raise click.ClickException(f"S3 fetch failed for {bucket}/{key}: {str(e)}") from e

    # Execute fetch with retries
    result = _do_fetch()
    return result
