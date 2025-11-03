from __future__ import annotations

import os
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config


def _import_gcs():
    try:
        from google.cloud import storage  # type: ignore

        return storage
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "GCS fetcher requires 'google-cloud-storage' package. "
            "Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def fetch_gcs(
    dest_dir: Path,
    name: str,
    *,
    bucket: str,
    blob_name: str,
    project_id: str | None = None,
    credentials_file_ref: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate from Google Cloud Storage.

    Config options:
      - bucket: GCS bucket name
      - blob_name: Blob name (path) within the bucket
      - project_id: GCP project ID (optional, can be inferred from credentials)
      - credentials_file_ref: env var name pointing to service account JSON file
                              (defaults to GOOGLE_APPLICATION_CREDENTIALS)
      - verify: may include 'ca_file' for TLS verification
      - timeout: operation timeout in seconds
      - retries: number of retry attempts
      - backoff_factor: exponential backoff multiplier
      - retry_on_status: HTTP status codes to retry on

    Authentication:
      - Uses service account JSON file from GOOGLE_APPLICATION_CREDENTIALS env var
      - Falls back to application default credentials (ADC) if not set
    """
    storage = _import_gcs()

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

    # Get credentials file path from environment
    credentials_env = credentials_file_ref or "GOOGLE_APPLICATION_CREDENTIALS"
    credentials_file = os.environ.get(credentials_env)

    # Custom verification for TLS
    # Note: google-cloud-storage uses requests internally, which respects REQUESTS_CA_BUNDLE
    if verify and isinstance(verify, dict) and verify.get("ca_file"):
        ca_file = str(verify.get("ca_file"))
        # Set environment variable for requests library
        os.environ["REQUESTS_CA_BUNDLE"] = ca_file

    # Create GCS client
    try:
        if credentials_file:
            # Use service account from file
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(credentials_file)
            client = storage.Client(
                project=project_id,
                credentials=credentials,
            )
        else:
            # Use application default credentials
            client = storage.Client(project=project_id)
    except Exception as e:
        raise click.ClickException(f"Failed to create GCS client: {e}") from e

    # Fetch the blob
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    try:
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(blob_name)

        # Download with timeout
        data = blob.download_as_bytes(timeout=fetch_config["timeout"])
        out_path.write_bytes(data)
    except Exception as e:
        raise click.ClickException(
            f"Failed to fetch from GCS bucket '{bucket}', blob '{blob_name}': {e}"
        ) from e

    return out_path
