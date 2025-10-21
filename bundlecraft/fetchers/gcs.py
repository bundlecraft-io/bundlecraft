from __future__ import annotations

import os
from pathlib import Path

import click


def _import_gcs():
    try:
        from google.cloud import storage  # type: ignore

        return storage
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "GCS fetcher requires 'google-cloud-storage' package. "
            "Install with: pip install 'bundlecraft[cloud]'"
        ) from e


def fetch_gcs(
    dest_dir: Path,
    name: str,
    *,
    bucket: str,
    blob_name: str,
    project: str | None = None,
    credentials_ref: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM from Google Cloud Storage and write to dest.

    Config options:
      - bucket: GCS bucket name (e.g., 'my-pki-bucket')
      - blob_name: blob name/path (e.g., 'certs/rootCA.pem')
      - project: GCP project ID (optional, uses default if not specified)
      - credentials_ref: env var for service account JSON key path (defaults to GOOGLE_APPLICATION_CREDENTIALS)
      - verify: may include TLS verification options
    """
    storage = _import_gcs()

    # Get credentials from environment
    creds_env = credentials_ref or "GOOGLE_APPLICATION_CREDENTIALS"
    creds_path = os.environ.get(creds_env)

    try:
        # Create storage client
        if creds_path:
            client = storage.Client.from_service_account_json(creds_path, project=project)
        elif project:
            client = storage.Client(project=project)
        else:
            # Use default credentials
            client = storage.Client()

        # Get bucket and blob
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(blob_name)

        # Download blob content
        data = blob.download_as_bytes()

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
            f"Failed to fetch from GCS bucket '{bucket}' blob '{blob_name}': {e}"
        ) from e
