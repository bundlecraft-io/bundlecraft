from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click


def _import_hvac():
    try:
        import hvac  # type: ignore

        return hvac
    except Exception as e:  # pragma: no cover - tested via behavior
        raise click.ClickException("Vault fetcher requires 'hvac' package.") from e


def fetch_vault(
    dest_dir: Path,
    name: str,
    *,
    mount_point: str,
    path: str,
    pem_field: str = "pem",
    addr: str | None = None,
    token_ref: str | None = None,
    namespace: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM from HashiCorp Vault KV engine and write to dest.

    Config options:
      - mount_point: KV engine mount name (e.g., 'secret')
      - path: secret path under the mount (e.g., 'pki/trusted_roots')
      - pem_field: field inside the secret data with PEM content (default 'pem')
      - addr: Vault address (defaults to VAULT_ADDR)
      - token_ref: env var name that holds token (defaults to VAULT_TOKEN if not set)
      - namespace: X-Vault-Namespace header (optional)
      - verify: may include 'ca_file' for TLS verification
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

    # Try KV v2 first, fallback to v1
    data: dict[str, Any]
    try:
        secret = client.secrets.kv.v2.read_secret_version(path=path, mount_point=mount_point)
        data = secret.get("data", {}).get("data", {})
    except Exception:
        secret = client.secrets.kv.v1.read_secret(path=path, mount_point=mount_point)
        data = secret.get("data", {})

    pem = data.get(pem_field)
    if not pem:
        raise click.ClickException(
            f"Vault secret missing '{pem_field}' field at {mount_point}/{path}."
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")
    # ensure trailing newline
    if not pem.endswith("\n"):
        pem = pem + "\n"
    out_path.write_text(pem, encoding="utf-8")
    return out_path
