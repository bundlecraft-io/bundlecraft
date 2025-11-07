from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff


def _import_azure():
    """Lazy import azure-storage-blob to avoid hard dependency."""
    try:
        from azure.core.exceptions import AzureError
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        return BlobServiceClient, DefaultAzureCredential, AzureError
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Blob fetcher requires 'azure-storage-blob' and 'azure-identity' packages. "
        ) from e


def fetch_azure_blob(
    dest_dir: Path,
    name: str,
    *,
    container: str,
    blob_name: str,
    account_name: str | None = None,
    connection_string_ref: str | None = None,
    account_key_ref: str | None = None,
    sas_token_ref: str | None = None,
    use_managed_identity: bool = False,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a blob from Azure Blob Storage.

    Authentication options (in order of precedence):
      1. connection_string_ref: Environment variable name containing connection string
      2. account_key_ref: Environment variable with account key (requires account_name)
      3. sas_token_ref: Environment variable with SAS token (requires account_name)
      4. use_managed_identity: Use Azure Managed Identity (requires account_name)
      5. DefaultAzureCredential: Fallback to Azure SDK default credential chain

    Config options:
      - container: Azure Blob container name (required)
      - blob_name: Blob path/name within the container (required)
      - account_name: Storage account name (required unless using connection_string)
      - connection_string_ref: Env var containing connection string
      - account_key_ref: Env var containing account key
      - sas_token_ref: Env var containing SAS token
      - use_managed_identity: Use managed identity for auth (default: False)
      - verify: may include content verification options
      - timeout: Request timeout in seconds
      - retries: Number of retry attempts
      - backoff_factor: Exponential backoff multiplier
      - retry_on_status: HTTP status codes to retry on
      - defaults: Global default configuration

    Returns:
        Path to the downloaded file
    """
    # Validate required parameters first
    if not container:
        raise click.ClickException("container parameter is required")
    if not blob_name:
        raise click.ClickException("blob_name parameter is required")

    # Validate authentication parameter requirements
    if account_key_ref and not account_name:
        raise click.ClickException(
            "account_name is required when using account_key_ref authentication"
        )
    if sas_token_ref and not account_name:
        raise click.ClickException(
            "account_name is required when using sas_token_ref authentication"
        )
    if use_managed_identity and not account_name:
        raise click.ClickException(
            "account_name is required when using managed identity or default credential authentication"
        )

    BlobServiceClient, DefaultAzureCredential, AzureError = _import_azure()

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

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Determine authentication method
    blob_service_client: Any = None

    # Option 1: Connection string
    if connection_string_ref:
        conn_str = os.environ.get(connection_string_ref)
        if not conn_str:
            raise click.ClickException(
                f"Connection string not found in environment variable '{connection_string_ref}'"
            )
        blob_service_client = BlobServiceClient.from_connection_string(
            conn_str, connection_timeout=fetch_config["timeout"]
        )

    # Option 2: Account key
    elif account_key_ref:
        if not account_name:
            raise click.ClickException(
                "account_name is required when using account_key_ref authentication"
            )
        account_key = os.environ.get(account_key_ref)
        if not account_key:
            raise click.ClickException(
                f"Account key not found in environment variable '{account_key_ref}'"
            )
        account_url = f"https://{account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=account_key,
            connection_timeout=fetch_config["timeout"],
        )

    # Option 3: SAS token
    elif sas_token_ref:
        if not account_name:
            raise click.ClickException(
                "account_name is required when using sas_token_ref authentication"
            )
        sas_token = os.environ.get(sas_token_ref)
        if not sas_token:
            raise click.ClickException(
                f"SAS token not found in environment variable '{sas_token_ref}'"
            )
        # Ensure SAS token starts with '?'
        if not sas_token.startswith("?"):
            sas_token = f"?{sas_token}"
        account_url = f"https://{account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=sas_token,
            connection_timeout=fetch_config["timeout"],
        )

    # Option 4: Managed Identity or DefaultAzureCredential
    else:
        if not account_name:
            raise click.ClickException(
                "account_name is required when using managed identity or default credential authentication"
            )
        account_url = f"https://{account_name}.blob.core.windows.net"
        # DefaultAzureCredential already tries managed identity as part of its credential chain
        # The use_managed_identity flag is informational/documentation but both paths use the same credential
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential,
            connection_timeout=fetch_config["timeout"],
        )

    # Apply retry logic to the blob download
    @retry_with_backoff(
        retries=fetch_config["retries"],
        backoff_factor=fetch_config["backoff_factor"],
        retry_on_status=fetch_config["retry_on_status"],
        timeout=fetch_config["timeout"],
    )
    def _do_fetch():
        try:
            blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)

            # Download blob content
            stream = blob_client.download_blob(timeout=fetch_config["timeout"])
            return stream.readall()
        except AzureError as e:
            # Translate Azure errors to more user-friendly messages
            error_msg = str(e)
            if "ContainerNotFound" in error_msg or "BlobNotFound" in error_msg:
                raise click.ClickException(
                    f"Azure Blob not found: container='{container}', blob='{blob_name}'. "
                    "Verify the container and blob names are correct."
                ) from e
            elif "AuthenticationFailed" in error_msg or "AuthorizationFailed" in error_msg:
                raise click.ClickException(
                    f"Azure authentication failed. Check your credentials and permissions. "
                    f"Error: {error_msg}"
                ) from e
            else:
                raise click.ClickException(f"Azure Blob fetch failed: {error_msg}") from e

    data = _do_fetch()
    out_path.write_bytes(data)
    return out_path
