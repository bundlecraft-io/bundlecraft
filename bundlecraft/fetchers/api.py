from __future__ import annotations

import os
import socket
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

import click


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
) -> Path:
    """Fetch from a generic API endpoint using bearer token auth.

    - token_ref names an environment variable holding the token (e.g., KEYFACTOR_TOKEN)
    - provider can hint header defaults (currently unused but reserved)
    - Writes response body to <name>.pem by default.
    """
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

    req = urllib.request.Request(endpoint, headers=hdrs)
    with urllib.request.urlopen(req, timeout=30, context=context) as resp:
        data = resp.read()
    out_path.write_bytes(data)
    return out_path
