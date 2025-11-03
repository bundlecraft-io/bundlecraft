from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff


def _import_azure_keyvault():
    """Lazy import Azure Key Vault SDK to avoid hard dependency."""
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore
        from azure.keyvault.secrets import SecretClient  # type: ignore

        return SecretClient, DefaultAzureCredential
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Azure Key Vault fetcher requires 'azure-keyvault-secrets' and 'azure-identity' packages. "
            "Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def fetch_azure_keyvault(
    dest_dir: Path,
    name: str,
    *,
    vault_url: str,
    secret_name: str,
    secret_version: str | None = None,
    credential_type: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret_ref: str | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM certificate from Azure Key Vault and write to dest.

    Config options:
      - vault_url: Azure Key Vault URL (e.g., 'https://myvault.vault.azure.net')
      - secret_name: Name of the secret containing the certificate/PEM
      - secret_version: Optional version of the secret (defaults to latest)
      - credential_type: Authentication method ('default', 'client_secret', 'managed_identity', 'cli')
                        Defaults to 'default' which uses DefaultAzureCredential
      - tenant_id: Azure AD tenant ID (required for client_secret auth)
      - client_id: Azure AD client/application ID (required for client_secret auth)
      - client_secret_ref: Environment variable name containing client secret (for client_secret auth)
      - timeout: Request timeout in seconds (uses fetch config defaults)
      - retries: Number of retry attempts (uses fetch config defaults)
      - backoff_factor: Exponential backoff multiplier (uses fetch config defaults)
      - retry_on_status: HTTP status codes to retry (uses fetch config defaults)
      - defaults: Global defaults configuration
      - verify: Verification options (not used for Azure SDK, but included for consistency)

    Authentication:
      The fetcher supports multiple authentication methods via credential_type:
      
      1. 'default' (DefaultAzureCredential) - Tries multiple auth methods in order:
         - Environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
         - Managed Identity
         - Azure CLI
         - Visual Studio Code
         - Azure PowerShell
         This is the recommended approach for production use.
      
      2. 'client_secret' (ClientSecretCredential) - Service Principal with client secret:
         - Requires: tenant_id, client_id, and client_secret_ref
         - The client_secret_ref points to an environment variable containing the secret
      
      3. 'managed_identity' (ManagedIdentityCredential) - Azure Managed Identity:
         - For Azure VMs, App Service, Function Apps, etc.
         - Optional client_id for user-assigned managed identity
      
      4. 'cli' (AzureCliCredential) - Azure CLI authentication:
         - Uses credentials from `az login`
         - Useful for local development

    Environment Variables (for DefaultAzureCredential and explicit client_secret):
      - AZURE_TENANT_ID: Azure AD tenant ID
      - AZURE_CLIENT_ID: Application (client) ID
      - AZURE_CLIENT_SECRET: Client secret value
      
    Required Azure Permissions:
      The authenticated principal needs the following Key Vault access:
      - Secret: Get (to read secret contents)
      - Optionally: List (if discovering secrets)
      
      This can be granted via:
      - Azure RBAC: "Key Vault Secrets User" role
      - Access Policy: "Get" permission for secrets

    Returns:
        Path to the written PEM file
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

    # Import Azure SDK
    SecretClient, DefaultAzureCredential = _import_azure_keyvault()

    # Determine credential based on credential_type
    auth_type = (credential_type or "default").lower()
    credential = None

    if auth_type == "default":
        # Use DefaultAzureCredential which tries multiple auth methods
        credential = DefaultAzureCredential()
    elif auth_type == "client_secret":
        # Use ClientSecretCredential with explicit service principal
        from azure.identity import ClientSecretCredential  # type: ignore

        if not tenant_id:
            raise click.ClickException(
                "Azure Key Vault: 'tenant_id' is required when using credential_type='client_secret'"
            )
        if not client_id:
            raise click.ClickException(
                "Azure Key Vault: 'client_id' is required when using credential_type='client_secret'"
            )
        client_secret_env = client_secret_ref or "AZURE_CLIENT_SECRET"
        client_secret = os.environ.get(client_secret_env)
        if not client_secret:
            raise click.ClickException(
                f"Azure Key Vault: client secret not found in environment variable '{client_secret_env}'"
            )
        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
    elif auth_type == "managed_identity":
        # Use ManagedIdentityCredential for Azure resources
        from azure.identity import ManagedIdentityCredential  # type: ignore

        if client_id:
            # User-assigned managed identity
            credential = ManagedIdentityCredential(client_id=client_id)
        else:
            # System-assigned managed identity
            credential = ManagedIdentityCredential()
    elif auth_type == "cli":
        # Use AzureCliCredential for local development
        from azure.identity import AzureCliCredential  # type: ignore

        credential = AzureCliCredential()
    else:
        raise click.ClickException(
            f"Azure Key Vault: unknown credential_type '{auth_type}'. "
            f"Valid options: default, client_secret, managed_identity, cli"
        )

    # Create Key Vault client
    client = SecretClient(vault_url=vault_url, credential=credential)

    # Fetch secret with retry logic
    @retry_with_backoff(
        retries=fetch_config["retries"],
        backoff_factor=fetch_config["backoff_factor"],
        retry_on_status=fetch_config["retry_on_status"],
        timeout=fetch_config["timeout"],
    )
    def _fetch_secret():
        try:
            if secret_version:
                secret = client.get_secret(secret_name, version=secret_version)
            else:
                secret = client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            # Provide more helpful error messages
            error_msg = str(e)
            if "AuthenticationError" in type(e).__name__ or "403" in error_msg:
                raise click.ClickException(
                    f"Azure Key Vault authentication failed for {vault_url}. "
                    f"Ensure credentials are valid and have 'Get' permission on secrets. "
                    f"Error: {error_msg}"
                ) from e
            elif "404" in error_msg or "SecretNotFound" in type(e).__name__:
                raise click.ClickException(
                    f"Azure Key Vault secret '{secret_name}' not found in {vault_url}. "
                    f"Verify the secret name and that it exists."
                ) from e
            else:
                raise click.ClickException(
                    f"Azure Key Vault fetch failed for secret '{secret_name}' in {vault_url}: {error_msg}"
                ) from e

    pem_data = _fetch_secret()

    if not pem_data:
        raise click.ClickException(
            f"Azure Key Vault secret '{secret_name}' is empty or null in {vault_url}"
        )

    # Write to destination
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Ensure trailing newline
    if not pem_data.endswith("\n"):
        pem_data = pem_data + "\n"

    out_path.write_text(pem_data, encoding="utf-8")
    return out_path
