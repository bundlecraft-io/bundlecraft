from __future__ import annotations

import os
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config


def _import_azure_keyvault():
    try:
        from azure.keyvault.certificates import CertificateClient  # type: ignore

        return CertificateClient
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Key Vault fetcher requires 'azure-keyvault-certificates' package. "
            "Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def _import_azure_identity():
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore

        return DefaultAzureCredential
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Key Vault fetcher requires 'azure-identity' package. "
            "Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def _import_cryptography():
    """Import cryptography dependencies for certificate conversion."""
    try:
        from cryptography import x509  # type: ignore
        from cryptography.hazmat.primitives import serialization  # type: ignore

        return x509, serialization
    except Exception as e:  # pragma: no cover
        raise click.ClickException(
            "Azure Key Vault fetcher requires 'cryptography' package for DER to PEM conversion."
        ) from e


def fetch_azure_keyvault(
    dest_dir: Path,
    name: str,
    *,
    vault_url: str,
    certificate_name: str,
    version: str | None = None,
    client_id_ref: str | None = None,
    client_secret_ref: str | None = None,
    tenant_id_ref: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate from Azure Key Vault.

    Config options:
      - vault_url: Azure Key Vault URL (e.g., 'https://myvault.vault.azure.net')
      - certificate_name: Name of the certificate in Key Vault
      - version: Certificate version (optional, uses latest if not specified)
      - client_id_ref: env var name for client ID (for service principal auth)
      - client_secret_ref: env var name for client secret (for service principal auth)
      - tenant_id_ref: env var name for tenant ID (for service principal auth)
      - verify: may include 'ca_file' for TLS verification
      - timeout: operation timeout in seconds
      - retries: number of retry attempts
      - backoff_factor: exponential backoff multiplier
      - retry_on_status: HTTP status codes to retry on

    Authentication:
      - If client_id, client_secret, and tenant_id are provided via env vars, uses service principal
      - Otherwise, uses DefaultAzureCredential (managed identity, Azure CLI, etc.)
    """
    CertificateClient = _import_azure_keyvault()
    DefaultAzureCredential = _import_azure_identity()

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

    # Get service principal credentials from environment if provided
    client_id_env = client_id_ref or "AZURE_CLIENT_ID"
    client_secret_env = client_secret_ref or "AZURE_CLIENT_SECRET"
    tenant_id_env = tenant_id_ref or "AZURE_TENANT_ID"

    client_id = os.environ.get(client_id_env)
    client_secret = os.environ.get(client_secret_env)
    tenant_id = os.environ.get(tenant_id_env)

    # Custom verification for TLS
    verify_ssl: str | bool = True
    if verify and isinstance(verify, dict) and verify.get("ca_file"):
        verify_ssl = str(verify.get("ca_file"))

    # Create credential
    try:
        if client_id and client_secret and tenant_id:
            # Use service principal authentication
            from azure.identity import ClientSecretCredential

            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            # Use default credential chain
            credential = DefaultAzureCredential()
    except Exception as e:
        raise click.ClickException(f"Failed to create Azure credentials: {e}") from e

    # Create Key Vault client
    try:
        # Note: Azure SDK doesn't support custom CA bundle directly via client constructor
        # It uses the system's CA bundle or REQUESTS_CA_BUNDLE env var
        if verify and isinstance(verify, dict) and verify.get("ca_file"):
            os.environ["REQUESTS_CA_BUNDLE"] = str(verify.get("ca_file"))

        certificate_client = CertificateClient(
            vault_url=vault_url,
            credential=credential,
        )
    except Exception as e:
        raise click.ClickException(f"Failed to create Azure Key Vault client: {e}") from e

    # Fetch the certificate
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    try:
        if version:
            certificate = certificate_client.get_certificate_version(
                certificate_name=certificate_name,
                version=version,
            )
        else:
            certificate = certificate_client.get_certificate(certificate_name=certificate_name)

        # Azure Key Vault returns the certificate in various formats
        # The .cer property contains the certificate in DER format
        # We need to convert it to PEM format
        cert_bytes = certificate.cer

        # Convert DER to PEM
        x509, serialization = _import_cryptography()
        cert_obj = x509.load_der_x509_certificate(cert_bytes)
        pem_data = cert_obj.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        # Ensure trailing newline
        if not pem_data.endswith("\n"):
            pem_data = pem_data + "\n"

        out_path.write_text(pem_data, encoding="utf-8")
    except Exception as e:
        raise click.ClickException(
            f"Failed to fetch certificate '{certificate_name}' from Azure Key Vault '{vault_url}': {e}"
        ) from e

    return out_path
