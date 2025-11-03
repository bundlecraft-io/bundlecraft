from __future__ import annotations

import os
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config


def _import_azure_storage():
    try:
        from azure.storage.blob import BlobServiceClient  # type: ignore

        return BlobServiceClient
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Blob fetcher requires 'azure-storage-blob' package. "
            "Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def fetch_azure_blob(
    dest_dir: Path,
    name: str,
    *,
    account_name: str,
    container: str,
    blob_name: str,
    account_key_ref: str | None = None,
    connection_string_ref: str | None = None,
    sas_token_ref: str | None = None,
    endpoint_url: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate from Azure Blob Storage.

    Config options:
      - account_name: Azure storage account name
      - container: Blob container name
      - blob_name: Blob name (path) within the container
      - account_key_ref: env var name for account key (defaults to AZURE_STORAGE_KEY)
      - connection_string_ref: env var name for connection string (defaults to AZURE_STORAGE_CONNECTION_STRING)
      - sas_token_ref: env var name for SAS token (optional, alternative to account key)
      - endpoint_url: Custom blob endpoint URL (optional)
      - verify: may include 'ca_file' for TLS verification
      - timeout: operation timeout in seconds
      - retries: number of retry attempts
      - backoff_factor: exponential backoff multiplier
      - retry_on_status: HTTP status codes to retry on

    Authentication priority (first available is used):
      1. Connection string (AZURE_STORAGE_CONNECTION_STRING)
      2. Account key (AZURE_STORAGE_KEY)
      3. SAS token
      4. Managed identity (if no credentials provided)
    """
    BlobServiceClient = _import_azure_storage()

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

    # Get credentials from environment variables
    connection_string_env = connection_string_ref or "AZURE_STORAGE_CONNECTION_STRING"
    account_key_env = account_key_ref or "AZURE_STORAGE_KEY"
    sas_token_env = sas_token_ref or "AZURE_STORAGE_SAS_TOKEN"

    connection_string = os.environ.get(connection_string_env)
    account_key = os.environ.get(account_key_env)
    sas_token = os.environ.get(sas_token_env)

    # Determine the endpoint URL
    if not endpoint_url:
        endpoint_url = f"https://{account_name}.blob.core.windows.net"

    # Custom verification for TLS
    verify_ssl: str | bool = True
    if verify and isinstance(verify, dict) and verify.get("ca_file"):
        verify_ssl = str(verify.get("ca_file"))

    # Create BlobServiceClient with appropriate authentication
    try:
        if connection_string:
            # Priority 1: Connection string
            blob_service_client = BlobServiceClient.from_connection_string(
                conn_str=connection_string,
                connection_verify=verify_ssl,
            )
        elif account_key:
            # Priority 2: Account key
            blob_service_client = BlobServiceClient(
                account_url=endpoint_url,
                credential=account_key,
                connection_verify=verify_ssl,
            )
        elif sas_token:
            # Priority 3: SAS token
            blob_service_client = BlobServiceClient(
                account_url=f"{endpoint_url}?{sas_token}",
                connection_verify=verify_ssl,
            )
        else:
            # Priority 4: Managed identity / default credentials
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(
                account_url=endpoint_url,
                credential=credential,
                connection_verify=verify_ssl,
            )
    except Exception as e:
        raise click.ClickException(f"Failed to create Azure Blob client: {e}") from e

    # Fetch the blob
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    try:
        blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
        download_stream = blob_client.download_blob(timeout=fetch_config["timeout"])
        data = download_stream.readall()
        out_path.write_bytes(data)
    except Exception as e:
        raise click.ClickException(
            f"Failed to fetch from Azure Blob container '{container}', blob '{blob_name}': {e}"
        ) from e

    return out_path
