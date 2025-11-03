from __future__ import annotations

import os
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config


def _import_boto3():
    try:
        import boto3  # type: ignore

        return boto3
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "S3 fetcher requires 'boto3' package. Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def fetch_s3(
    dest_dir: Path,
    name: str,
    *,
    bucket: str,
    key: str,
    region: str | None = None,
    access_key_id_ref: str | None = None,
    secret_access_key_ref: str | None = None,
    session_token_ref: str | None = None,
    endpoint_url: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate from AWS S3.

    Config options:
      - bucket: S3 bucket name
      - key: Object key (path) in the bucket
      - region: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
      - access_key_id_ref: env var name for AWS access key ID (defaults to AWS_ACCESS_KEY_ID)
      - secret_access_key_ref: env var name for AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY)
      - session_token_ref: env var name for AWS session token (optional, for temporary credentials)
      - endpoint_url: Custom S3 endpoint URL (optional, for S3-compatible services)
      - verify: may include 'ca_file' for TLS verification
      - timeout: operation timeout in seconds
      - retries: number of retry attempts
      - backoff_factor: exponential backoff multiplier
      - retry_on_status: HTTP status codes to retry on
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

    # Get credentials from environment variables
    access_key_id_env = access_key_id_ref or "AWS_ACCESS_KEY_ID"
    secret_access_key_env = secret_access_key_ref or "AWS_SECRET_ACCESS_KEY"
    session_token_env = session_token_ref or "AWS_SESSION_TOKEN"

    access_key_id = os.environ.get(access_key_id_env)
    secret_access_key = os.environ.get(secret_access_key_env)
    session_token = os.environ.get(session_token_env)

    # Access key and secret are required unless using IAM role
    if not access_key_id and not secret_access_key:
        # Try to use default credentials (IAM role, config file, etc.)
        pass
    elif not access_key_id or not secret_access_key:
        raise click.ClickException(
            f"Both AWS access key ID ('{access_key_id_env}') and secret access key ('{secret_access_key_env}') "
            f"must be set, or neither (to use IAM role/default credentials)"
        )

    # Determine region
    aws_region = region or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

    # Build boto3 config for retries
    from botocore.config import Config

    boto_config = Config(
        region_name=aws_region,
        retries={"max_attempts": fetch_config["retries"] + 1, "mode": "standard"},
        connect_timeout=fetch_config["timeout"],
        read_timeout=fetch_config["timeout"],
    )

    # Custom verification for TLS
    verify_ssl: str | bool = True
    if verify and isinstance(verify, dict) and verify.get("ca_file"):
        verify_ssl = str(verify.get("ca_file"))

    # Create S3 client
    try:
        if access_key_id and secret_access_key:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                config=boto_config,
                endpoint_url=endpoint_url,
                verify=verify_ssl,
            )
        else:
            # Use default credentials
            s3_client = boto3.client(
                "s3",
                config=boto_config,
                endpoint_url=endpoint_url,
                verify=verify_ssl,
            )
    except Exception as e:
        raise click.ClickException(f"Failed to create S3 client: {e}") from e

    # Fetch the object
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = response["Body"].read()
        out_path.write_bytes(data)
    except Exception as e:
        raise click.ClickException(f"Failed to fetch from S3 bucket '{bucket}', key '{key}': {e}") from e

    return out_path
