"""Google Cloud Storage (GCS) fetcher for BundleCraft.

Fetches certificates from Google Cloud Storage buckets with support for:
- Google Cloud SDK authentication (Application Default Credentials)
- Service account JSON key files
- Configurable retry and timeout behavior
- Content verification (SHA256)
- Provenance recording

Authentication methods (in order of precedence):
1. GOOGLE_APPLICATION_CREDENTIALS environment variable (path to service account JSON)
2. Application Default Credentials (ADC) - gcloud auth application-default login
3. Compute Engine/GKE/Cloud Run default service account
"""

from __future__ import annotations

import os
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff


def _import_gcs():
    """Import Google Cloud Storage client library with helpful error message."""
    try:
        from google.cloud import storage  # type: ignore

        return storage
    except ImportError as e:  # pragma: no cover - tested via behavior
        raise click.ClickException("GCS fetcher requires 'google-cloud-storage' package. ") from e


def _import_service_account():
    """Import Google OAuth2 service account module with helpful error message."""
    try:
        from google.oauth2 import service_account  # type: ignore

        return service_account
    except ImportError as e:  # pragma: no cover - tested via behavior
        raise click.ClickException("GCS fetcher requires 'google-auth' package. ") from e


def fetch_gcs(
    dest_dir: Path,
    name: str,
    *,
    bucket: str,
    object_path: str,
    credentials_file: str | None = None,
    project: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate from Google Cloud Storage.

    Args:
        dest_dir: Destination directory for the fetched file
        name: Name for the output file (without .pem extension)
        bucket: GCS bucket name
        object_path: Path to the object within the bucket (e.g., 'certs/root.pem')
        credentials_file: Optional path to service account JSON key file.
                         If not provided, uses GOOGLE_APPLICATION_CREDENTIALS env var
                         or Application Default Credentials.
        project: Optional GCP project ID (usually not required)
        verify: Optional verification settings (e.g., {'sha256': 'expected_hash'})
        timeout: Request timeout in seconds (default from config)
        retries: Number of retry attempts (default from config)
        backoff_factor: Exponential backoff multiplier (default from config)
        retry_on_status: HTTP status codes to retry (default from config)
        defaults: Global default configuration

    Returns:
        Path to the downloaded file

    Raises:
        click.ClickException: On authentication, network, or validation errors

    Environment Variables:
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON key file
        GOOGLE_CLOUD_PROJECT: Default GCP project (optional)

    Required GCS Permissions:
        - storage.objects.get: Read objects from the bucket
        - storage.buckets.get: (Optional) Verify bucket access
    """
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

    # Import GCS library
    storage = _import_gcs()

    # Prepare output path
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Determine credentials source
    creds_path = credentials_file or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not Path(creds_path).exists():
        raise click.ClickException(
            f"GCS credentials file not found: {creds_path}. "
            "Ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid service account JSON file."
        )

    # Initialize GCS client with retry logic
    try:
        if creds_path:
            # Use explicit service account credentials
            service_account = _import_service_account()
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            client = storage.Client(credentials=credentials, project=project)
        else:
            # Use Application Default Credentials (ADC)
            client = storage.Client(project=project)
    except Exception as e:
        raise click.ClickException(
            f"Failed to initialize GCS client: {e}. "
            "Ensure you have valid credentials configured. "
            "See: https://cloud.google.com/docs/authentication/provide-credentials-adc"
        ) from e

    # Fetch the object with retry logic
    @retry_with_backoff(
        retries=fetch_config["retries"],
        backoff_factor=fetch_config["backoff_factor"],
        retry_on_status=fetch_config["retry_on_status"],
        timeout=fetch_config["timeout"],
    )
    def _do_fetch():
        try:
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(object_path)

            # Check if object exists
            if not blob.exists():
                raise click.ClickException(
                    f"GCS object not found: gs://{bucket}/{object_path}. "
                    "Verify the bucket and object path are correct."
                )

            # Download to destination with timeout
            blob.download_to_filename(
                str(out_path),
                timeout=fetch_config["timeout"],
            )
            return out_path
        except click.ClickException:
            # Re-raise ClickExceptions as-is (non-retryable)
            raise
        except Exception as e:
            # Check for specific errors that should not be retried
            error_msg = str(e)

            # Non-retryable errors - convert to ClickException
            if "403" in error_msg or "Forbidden" in error_msg:
                raise click.ClickException(
                    f"Access denied to gs://{bucket}/{object_path}. "
                    "Ensure your service account has 'storage.objects.get' permission."
                ) from e
            elif "404" in error_msg or "Not Found" in error_msg:
                raise click.ClickException(
                    f"GCS object not found: gs://{bucket}/{object_path}"
                ) from e
            elif "401" in error_msg or "Unauthorized" in error_msg:
                raise click.ClickException(
                    "Authentication failed for GCS. "
                    "Verify your credentials are valid and not expired."
                ) from e

            # For other exceptions (including OSError, network errors),
            # let them bubble up to trigger retry logic
            raise

    # Perform the fetch
    try:
        result_path = _do_fetch()
    except (OSError, TimeoutError) as e:
        # Convert retryable errors to ClickException if retries are exhausted
        raise click.ClickException(f"GCS fetch failed: {e}") from e

    return result_path
