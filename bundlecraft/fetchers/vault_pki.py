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


def fetch_vault_pki_issuer(
    dest_dir: Path,
    name: str,
    *,
    mount_point: str = "pki",
    issuer_ref: str = "default",
    addr: str | None = None,
    token_ref: str | None = None,
    namespace: str | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a certificate from HashiCorp Vault PKI Issuer endpoint and write to dest.

    This fetcher retrieves certificates from Vault's PKI secrets engine using the issuer
    endpoint. According to Vault's API documentation, the issuer endpoint is unauthenticated
    and returns the PEM-encoded certificate chain.

    Reference: https://developer.hashicorp.com/vault/api-docs/secret/pki#read-issuer-certificate

    Config options:
      - mount_point: PKI secrets engine mount path (default: 'pki')
      - issuer_ref: Issuer reference (name or UUID, default: 'default')
      - addr: Vault address (defaults to VAULT_ADDR env var)
      - token_ref: env var name that holds token (optional, for authenticated access)
      - namespace: X-Vault-Namespace header (optional, for Vault Enterprise)
      - verify: may include 'ca_file' for TLS verification
      - timeout: request timeout in seconds (uses fetch config defaults if not set)
      - retries: number of retry attempts (uses fetch config defaults if not set)
      - backoff_factor: exponential backoff multiplier (uses fetch config defaults if not set)
      - retry_on_status: HTTP status codes to retry on (uses fetch config defaults if not set)

    Note: While the Vault PKI issuer endpoint is documented as unauthenticated,
    this implementation supports optional token-based authentication for environments
    that may require it or for accessing Enterprise features.
    """
    from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff

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

    # Vault address is required
    url = addr or os.environ.get("VAULT_ADDR")
    if not url:
        raise click.ClickException(
            "Vault address is required. Set 'addr' in config or VAULT_ADDR environment variable."
        )

    # Token is optional for PKI issuer endpoint (documented as unauthenticated)
    token = None
    if token_ref:
        token_env = token_ref
        token = os.environ.get(token_env)
        # Don't fail if token is missing, as the endpoint is unauthenticated
        # but log a warning if token_ref was specified but not found
        if not token:
            click.echo(
                f"  ⚠️  Token not found in environment variable '{token_env}', "
                "proceeding without authentication (PKI issuer endpoint is unauthenticated)",
                err=True,
            )

    hvac = _import_hvac()

    # TLS verification options
    verify_ssl: str | bool | None = True
    if verify and isinstance(verify, dict) and verify.get("ca_file"):
        verify_ssl = str(verify.get("ca_file"))

    # Create Vault client
    client = hvac.Client(url=url, token=token, namespace=namespace, verify=verify_ssl)

    # Build the issuer certificate endpoint path
    # Format: /v1/{mount_point}/issuer/{issuer_ref}/pem
    issuer_path = f"{mount_point}/issuer/{issuer_ref}/pem"

    # Apply retry logic to the fetch operation
    @retry_with_backoff(
        retries=fetch_config["retries"],
        backoff_factor=fetch_config["backoff_factor"],
        retry_on_status=fetch_config["retry_on_status"],
        timeout=fetch_config["timeout"],
    )
    def _do_fetch():
        try:
            # Use hvac's adapter to make the request
            # The issuer endpoint returns the PEM directly in the response body
            response = client.adapter.get(
                f"/v1/{issuer_path}", timeout=fetch_config["timeout"]
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise click.ClickException(
                f"Failed to fetch certificate from Vault PKI issuer at {url}/v1/{issuer_path}: {e}"
            ) from e

    pem_data = _do_fetch()

    if not pem_data or not pem_data.strip():
        raise click.ClickException(
            f"Vault PKI issuer returned empty certificate data from {issuer_path}"
        )

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Write certificate to file
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Ensure trailing newline
    if not pem_data.endswith("\n"):
        pem_data = pem_data + "\n"

    out_path.write_text(pem_data, encoding="utf-8")
    return out_path
