from __future__ import annotations

import os
from pathlib import Path

import click


def _import_boto3():
    try:
        import boto3  # type: ignore

        return boto3
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "S3 fetcher requires 'boto3' package. Install with: pip install 'bundlecraft[cloud]'"
        ) from e


def fetch_s3(
    dest_dir: Path,
    name: str,
    *,
    bucket: str,
    key: str,
    region: str | None = None,
    endpoint_url: str | None = None,
    access_key_ref: str | None = None,
    secret_key_ref: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM from AWS S3 and write to dest.

    Config options:
      - bucket: S3 bucket name (e.g., 'my-pki-bucket')
      - key: object key/path (e.g., 'certs/rootCA.pem')
      - region: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
      - endpoint_url: Custom S3 endpoint for S3-compatible storage (optional)
      - access_key_ref: env var name for AWS access key ID (defaults to AWS_ACCESS_KEY_ID)
      - secret_key_ref: env var name for AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY)
      - verify: may include TLS verification options
    """
    boto3 = _import_boto3()

    # Get credentials from environment
    access_key_env = access_key_ref or "AWS_ACCESS_KEY_ID"
    secret_key_env = secret_key_ref or "AWS_SECRET_ACCESS_KEY"
    
    access_key = os.environ.get(access_key_env)
    secret_key = os.environ.get(secret_key_env)
    
    # Create S3 client with optional credentials
    client_kwargs = {}
    if region:
        client_kwargs["region_name"] = region
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url
    if access_key and secret_key:
        client_kwargs["aws_access_key_id"] = access_key
        client_kwargs["aws_secret_access_key"] = secret_key
    
    # Handle TLS verification options
    if verify and isinstance(verify, dict):
        ca_file = verify.get("ca_file")
        if ca_file:
            client_kwargs["verify"] = str(ca_file)
    
    try:
        s3_client = boto3.client("s3", **client_kwargs)
        
        # Fetch object from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = response["Body"].read()
        
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
            f"Failed to fetch from S3 bucket '{bucket}' key '{key}': {e}"
        ) from e
