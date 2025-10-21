from __future__ import annotations

import os
from pathlib import Path

import click


def _import_azure_keyvault():
    try:
        from azure.keyvault.certificates import CertificateClient  # type: ignore

        return CertificateClient
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Key Vault fetcher requires 'azure-keyvault-certificates' package. "
            "Install with: pip install 'bundlecraft[cloud]'"
        ) from e


def fetch_azure_keyvault(
    dest_dir: Path,
    name: str,
    *,
    vault_url: str,
    certificate_name: str,
    version: str | None = None,
    tenant_id_ref: str | None = None,
    client_id_ref: str | None = None,
    client_secret_ref: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a certificate from Azure Key Vault and write to dest.

    Config options:
      - vault_url: Key Vault URL (e.g., 'https://myvault.vault.azure.net/')
      - certificate_name: name of the certificate in Key Vault
      - version: certificate version (optional, defaults to latest)
      - tenant_id_ref: env var for Azure tenant ID (optional, for service principal auth)
      - client_id_ref: env var for Azure client ID (optional, for service principal auth)
      - client_secret_ref: env var for Azure client secret (optional, for service principal auth)
      - verify: may include TLS verification options
    """
    CertificateClient = _import_azure_keyvault()

    # Get credentials from environment
    tenant_id_env = tenant_id_ref or "AZURE_TENANT_ID"
    client_id_env = client_id_ref or "AZURE_CLIENT_ID"
    client_secret_env = client_secret_ref or "AZURE_CLIENT_SECRET"

    tenant_id = os.environ.get(tenant_id_env)
    client_id = os.environ.get(client_id_env)
    client_secret = os.environ.get(client_secret_env)

    try:
        # Create credential
        if tenant_id and client_id and client_secret:
            from azure.identity import ClientSecretCredential

            credential = ClientSecretCredential(
                tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
            )
        else:
            # Use default credential (Managed Identity, Azure CLI, etc.)
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()

        # Create certificate client
        client = CertificateClient(vault_url=vault_url, credential=credential)

        # Get certificate
        if version:
            certificate = client.get_certificate_version(certificate_name, version)
        else:
            certificate = client.get_certificate(certificate_name)

        # Extract PEM from certificate
        # Azure Key Vault returns certificates in different formats
        # We need to convert to PEM format
        cer_bytes = certificate.cer

        # Convert DER to PEM
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization

        cert = x509.load_der_x509_certificate(cer_bytes)
        pem_bytes = cert.public_bytes(serialization.Encoding.PEM)
        content = pem_bytes.decode("utf-8")

        # Write to destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

        # Ensure trailing newline
        if not content.endswith("\n"):
            content = content + "\n"

        out_path.write_text(content, encoding="utf-8")
        return out_path

    except Exception as e:
        raise click.ClickException(
            f"Failed to fetch certificate '{certificate_name}' from Key Vault '{vault_url}': {e}"
        ) from e
