from __future__ import annotations

import os
import socket
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes

from bundlecraft.helpers.fetch_utils import get_fetch_config, retry_with_backoff


def _safe_filename_from_url(url: str, name: str | None = None) -> str:
    """Derive a safe output filename from URL or provided name.

    If name is provided, use '<name>.pem' (unless it already ends with .pem).
    Otherwise, use the last path segment of the URL, defaulting to 'download.pem'.
    """
    if name:
        return name if name.lower().endswith(".pem") else f"{name}.pem"
    parsed = urllib.parse.urlparse(url)
    base = os.path.basename(parsed.path) or "download.pem"
    if not base.lower().endswith(".pem"):
        base = f"{base}.pem"
    return base


def _tls_leaf_fingerprint_sha256(host: str, port: int) -> str:
    """Retrieve the server leaf cert and return its SHA256 fingerprint (hex).

    Note: Fingerprint computation should not depend on system trust to allow
    pinning against self-signed endpoints. We therefore use an unverified
    SSL context for the probe and still rely on normal verification (with
    optional ca_file) during the actual fetch.
    """
    # Use an unverified context to allow self-signed endpoints for pinning only
    ctx = ssl._create_unverified_context()
    with socket.create_connection((host, port), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der = ssock.getpeercert(binary_form=True)
    cert = x509.load_der_x509_certificate(der)
    fp = cert.fingerprint(hashes.SHA256()).hex()
    return fp


def fetch_url(
    url: str,
    dest_dir: Path,
    name: str | None = None,
    verify: dict | None = None,
    root: Path | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    backoff_factor: float | None = None,
    retry_on_status: list[int] | None = None,
    defaults: dict | None = None,
) -> Path:
    """Fetch a URL (https or file) and save to dest_dir.

    - HTTPS is verified against system CAs (no custom CA pinning yet)
    - file:// URLs are copied directly
    Returns the output file path.
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
    out_name = _safe_filename_from_url(url, name)
    out_path = dest_dir / out_name

    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()

    if scheme in {"http"}:
        raise ValueError("Insecure HTTP is not allowed for fetch; use HTTPS or file URLs")

    if scheme in {"https"}:
        # Build SSL context (system CAs or custom CA)
        ctx = ssl.create_default_context()
        v = verify or {}
        ca_file = v.get("ca_file") if isinstance(v, dict) else None
        tls_fp = v.get("tls_fingerprint_sha256") if isinstance(v, dict) else None
        if ca_file:
            ca_path = Path(ca_file)
            if root is not None and not ca_path.is_absolute():
                ca_path = (root / ca_file).resolve()
            ctx.load_verify_locations(cafile=str(ca_path))

        # Optional TLS fingerprint pinning (leaf cert)
        if tls_fp:
            host = parsed.hostname or ""
            port = parsed.port or 443
            actual_fp = _tls_leaf_fingerprint_sha256(host, port)
            if actual_fp.lower() != str(tls_fp).lower():
                raise ValueError(
                    f"TLS fingerprint mismatch for {host}:{port} (expected {tls_fp}, got {actual_fp})"
                )

        # Apply retry logic to the actual fetch
        @retry_with_backoff(
            retries=fetch_config["retries"],
            backoff_factor=fetch_config["backoff_factor"],
            retry_on_status=fetch_config["retry_on_status"],
            timeout=fetch_config["timeout"],
        )
        def _do_fetch():
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=fetch_config["timeout"]) as resp:
                return resp.read()

        data = _do_fetch()
        out_path.write_bytes(data)
        return out_path

    if scheme in {"file", ""}:
        # Local file path
        src_path = Path(parsed.path if scheme == "file" else url)
        if not src_path.exists():
            raise FileNotFoundError(f"File not found: {src_path}")
        data = src_path.read_bytes()
        out_path.write_bytes(data)
        return out_path

    raise ValueError(f"Unsupported URL scheme: {scheme}")
