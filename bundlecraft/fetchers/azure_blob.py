from __future__ import annotations

import os
from pathlib import Path

import click


def _import_azure_storage():
    try:
        from azure.storage.blob import BlobServiceClient  # type: ignore

        return BlobServiceClient
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Blob fetcher requires 'azure-storage-blob' package. "
            "Install with: pip install 'bundlecraft[cloud]'"
        ) from e


def fetch_azure_blob(
    dest_dir: Path,
    name: str,
    *,
    container: str,
    blob_name: str,
    account_name: str | None = None,
    account_url: str | None = None,
    connection_string_ref: str | None = None,
    sas_token_ref: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM from Azure Blob Storage and write to dest.

    Config options:
      - container: blob container name (e.g., 'pki-certs')
      - blob_name: blob name/path (e.g., 'certs/rootCA.pem')
      - account_name: storage account name (optional, can be in connection string)
      - account_url: full account URL (e.g., 'https://myaccount.blob.core.windows.net')
      - connection_string_ref: env var for connection string (defaults to AZURE_STORAGE_CONNECTION_STRING)
      - sas_token_ref: env var for SAS token (optional, alternative to connection string)
      - verify: may include TLS verification options
    """
    BlobServiceClient = _import_azure_storage()

    # Try connection string first
    conn_str_env = connection_string_ref or "AZURE_STORAGE_CONNECTION_STRING"
    conn_str = os.environ.get(conn_str_env)
    
    # Try SAS token
    sas_token_env = sas_token_ref or "AZURE_STORAGE_SAS_TOKEN"
    sas_token = os.environ.get(sas_token_env)
    
    try:
        # Create BlobServiceClient
        if conn_str:
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        elif account_url:
            if sas_token:
                blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=sas_token
                )
            else:
                # Try default credential (Managed Identity, etc.)
                from azure.identity import DefaultAzureCredential
                
                credential = DefaultAzureCredential()
                blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=credential
                )
        elif account_name:
            url = f"https://{account_name}.blob.core.windows.net"
            if sas_token:
                blob_service_client = BlobServiceClient(account_url=url, credential=sas_token)
            else:
                from azure.identity import DefaultAzureCredential
                
                credential = DefaultAzureCredential()
                blob_service_client = BlobServiceClient(account_url=url, credential=credential)
        else:
            raise click.ClickException(
                "Azure Blob fetch requires either connection_string_ref, account_url, or account_name"
            )
        
        # Get blob client and download
        blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
        data = blob_client.download_blob().readall()
        
        # Write to destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")
        
        # Ensure data is decoded if bytes
        if isinstance(data, bytes):
            content = data.decode("utf-8")
        else:
            content = data
        
        # Ensure trailing newline
        if not content.endswith("\n"):
            content = content + "\n"
        
        out_path.write_text(content, encoding="utf-8")
        return out_path
        
    except Exception as e:
        raise click.ClickException(
            f"Failed to fetch from Azure Blob container '{container}' blob '{blob_name}': {e}"
        ) from e
