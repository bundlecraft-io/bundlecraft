from __future__ import annotations

import socket
import ssl
import urllib.error
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


def fetch_mozilla_roots(
    dest_dir: Path,
    name: str,
    *,
    url: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch Mozilla's trusted root certificates bundle.

    Config options:
      - url: URL to Mozilla's CA bundle (defaults to curl.se mirror of Mozilla's bundle)
      - verify: may include 'sha256', 'ca_file', and 'tls_fingerprint_sha256' for verification

    Default source: https://curl.se/ca/cacert.pem (Mozilla's CA certificate bundle)
    See: https://wiki.mozilla.org/CA/Included_Certificates
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Default to curl.se mirror of Mozilla's bundle
    bundle_url = url or "https://curl.se/ca/cacert.pem"

    parsed = urllib.parse.urlparse(bundle_url)
    if parsed.scheme.lower() != "https":
        raise click.ClickException("Mozilla roots fetch requires HTTPS URL")

    # Prepare headers
    hdrs = {
        "User-Agent": "BundleCraft-Fetcher/1.0",
        "Accept": "application/x-pem-file, text/plain, */*",
    }

    # TLS verification options
    context: ssl.SSLContext | None = None
    ca_file = None
    tls_fingerprint = None
    if verify and isinstance(verify, dict):
        ca_file = verify.get("ca_file")
        tls_fingerprint = verify.get("tls_fingerprint_sha256")
    if ca_file:
        context = ssl.create_default_context(cafile=str(ca_file))
    else:
        context = ssl.create_default_context()

    # Optional TLS leaf certificate fingerprint pinning
    if tls_fingerprint:
        host = parsed.hostname or ""
        port = parsed.port or 443
        actual_fp = _tls_leaf_fingerprint_sha256(host, port)
        if actual_fp.lower() != str(tls_fingerprint).lower():
            raise click.ClickException(
                f"TLS fingerprint mismatch for {host}:{port}: expected {tls_fingerprint}, got {actual_fp}"
            )

    # Fetch the bundle
    req = urllib.request.Request(bundle_url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60, context=context) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        msg = f"Failed to fetch Mozilla roots: HTTP Error {e.code}: {e.reason}"
        raise click.ClickException(msg) from e

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
