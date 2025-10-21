from __future__ import annotations

import json
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import click

from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff


def _tls_leaf_fingerprint_sha256(host: str, port: int) -> str:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der_cert = ssock.getpeercert(binary_form=True)
    import hashlib

    return hashlib.sha256(der_cert).hexdigest()


def fetch_api(
    endpoint: str,
    dest_dir: Path,
    name: str,
    provider: str | None = None,
    token_ref: str | None = None,
    headers: dict | None = None,
    verify: dict | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch from a generic API endpoint using bearer token auth.

    - token_ref names an environment variable holding the token (e.g., KEYFACTOR_TOKEN)
    - provider can hint header defaults (currently unused but reserved)
    - Writes response body to <name>.pem by default.
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

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme.lower() != "https":
        raise click.ClickException("API fetch requires HTTPS endpoint")

    hdrs = {"Accept": "application/x-pem-file, application/octet-stream, */*"}
    if headers:
        hdrs.update(headers)

    token = None
    if token_ref:
        token = os.environ.get(token_ref)
        if token is None:
            raise click.ClickException(
                f"Missing API token: environment variable '{token_ref}' is not set"
            )
    if token:
        hdrs["Authorization"] = f"Bearer {token}"

    # TLS verification options
    context: ssl.SSLContext | None = None
    ca_file = None
    tls_fingerprint = None
    if verify and isinstance(verify, dict):
        ca_file = verify.get("ca_file")
        tls_fingerprint = verify.get("tls_fingerprint_sha256")
    if ca_file:
        context = ssl.create_default_context(cafile=str(ca_file))

    # Optional TLS leaf certificate fingerprint pinning
    if tls_fingerprint:
        host = parsed.hostname or ""
        port = parsed.port or 443
        actual_fp = _tls_leaf_fingerprint_sha256(host, port)
        if actual_fp.lower() != str(tls_fingerprint).lower():
            raise click.ClickException(
                f"TLS fingerprint mismatch for {host}:{port}: expected {tls_fingerprint}, got {actual_fp}"
            )

    # Choose method and body
    data_bytes: bytes | None = None
    if (provider or "").lower() == "keyfactor":
        # Default Keyfactor-like request body
        body = {"CertID": 12345, "CertificateFormat": "PEM", "IncludeChain": True}
        data_bytes = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(endpoint, headers=hdrs, data=data_bytes)

    # Apply retry logic to the actual fetch
    @retry_with_backoff(
        retries=fetch_config["retries"],
        backoff_factor=fetch_config["backoff_factor"],
        retry_on_status=fetch_config["retry_on_status"],
        timeout=fetch_config["timeout"],
    )
    def _do_fetch():
        try:
            with urllib.request.urlopen(
                req, timeout=fetch_config["timeout"], context=context
            ) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            # Improve diagnostics for common API mistakes
            hint = None
            if e.code == 405:
                meth = "POST" if data_bytes is not None else "GET"
                hint = (
                    f"Endpoint rejected {meth}. If this is a Keyfactor-like API, it typically requires POST "
                    f"with JSON body and a Bearer token. Ensure provider=keyfactor and token_ref is set."
                )
            elif e.code in (401, 403):
                hint = (
                    f"Authentication failed (HTTP {e.code}). Check that the token env variable '{token_ref}' is set "
                    f"and correct, and that the 'Authorization: Bearer' header is being sent."
                )
            msg = f"HTTP Error {e.code}: {e.reason} for {endpoint}"
            if hint:
                msg = msg + f"\nHint: {hint}"
            raise click.ClickException(msg) from e

    data = _do_fetch()
    out_path.write_bytes(data)
    return out_path
