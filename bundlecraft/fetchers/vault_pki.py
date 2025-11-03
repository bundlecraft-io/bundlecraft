from __future__ import annotations

import os
from pathlib import Path

import click


def _import_hvac():
    try:
        import hvac  # type: ignore

        return hvac
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException(
            "Vault PKI fetcher requires 'hvac' package. Install with: pip install 'bundlecraft[fetchers]'"
        ) from e


def fetch_vault_pki(
    dest_dir: Path,
    name: str,
    *,
    mount_point: str,
    issuer_ref: str = "default",
    addr: str | None = None,
    token_ref: str | None = None,
    namespace: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch an issuer certificate from HashiCorp Vault PKI engine.

    This fetcher retrieves the issuer certificate from a Vault PKI secrets engine
    using the Read Issuer Certificate endpoint:
    https://developer.hashicorp.com/vault/api-docs/secret/pki#read-issuer-certificate

    Config options:
      - mount_point: PKI engine mount name (e.g., 'pki', 'pki_int')
      - issuer_ref: Issuer reference (default: 'default'). Can be issuer ID, issuer name, or 'default'
      - addr: Vault address (defaults to VAULT_ADDR)
      - token_ref: env var name that holds token (defaults to VAULT_TOKEN)
      - namespace: X-Vault-Namespace header (optional, for Vault Enterprise)
      - verify: may include 'ca_file' for TLS verification

    The endpoint returns the raw certificate in PEM or DER format.
    """
    token_env = token_ref or "VAULT_TOKEN"
    token = os.environ.get(token_env)
    if not token:
        raise click.ClickException(f"Vault token not found in environment variable '{token_env}'.")

    url = addr or os.environ.get("VAULT_ADDR")
    if not url:
        raise click.ClickException("Vault address is required (set 'addr' or VAULT_ADDR)")

    hvac = _import_hvac()

    verify_ssl: str | bool | None = True
    if verify and isinstance(verify, dict) and verify.get("ca_file"):
        verify_ssl = str(verify.get("ca_file"))

    client = hvac.Client(url=url, token=token, namespace=namespace, verify=verify_ssl)

    # Fetch the issuer certificate using the PKI endpoint
    # The endpoint path is: /v1/{mount_point}/issuer/{issuer_ref}/pem
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    try:
        # Use the PKI secrets engine to read issuer certificate
        # hvac doesn't have a direct method for this, so we use the adapter's get method
        response = client.adapter.get(
            f"/v1/{mount_point}/issuer/{issuer_ref}/pem",
        )

        # The response is the raw PEM certificate
        pem_data = response.text

        if not pem_data or not pem_data.strip():
            raise click.ClickException(
                f"Vault PKI returned empty certificate for issuer '{issuer_ref}' at {mount_point}"
            )

        # Ensure trailing newline
        if not pem_data.endswith("\n"):
            pem_data = pem_data + "\n"

        out_path.write_text(pem_data, encoding="utf-8")
    except hvac.exceptions.InvalidPath as e:
        raise click.ClickException(
            f"Vault PKI issuer '{issuer_ref}' not found at mount '{mount_point}'. "
            f"Verify the mount point and issuer reference."
        ) from e
    except Exception as e:
        raise click.ClickException(
            f"Failed to fetch from Vault PKI mount '{mount_point}', issuer '{issuer_ref}': {e}"
        ) from e

    return out_path
