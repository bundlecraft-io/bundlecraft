from __future__ import annotations

import os
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


def fetch_artifactory(
    dest_dir: Path,
    name: str,
    *,
    url: str,
    repository: str | None = None,
    path: str | None = None,
    username_ref: str | None = None,
    password_ref: str | None = None,
    token_ref: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM from JFrog Artifactory and write to dest.

    Config options:
      - url: full Artifactory URL to the artifact OR base Artifactory URL (requires repository + path)
      - repository: repository name (e.g., 'libs-release-local', used with path)
      - path: artifact path within repository (e.g., 'com/example/certs/rootCA.pem')
      - username_ref: env var for Artifactory username (defaults to ARTIFACTORY_USERNAME)
      - password_ref: env var for Artifactory password (defaults to ARTIFACTORY_PASSWORD)
      - token_ref: env var for Artifactory API token (defaults to ARTIFACTORY_TOKEN, preferred over username/password)
      - verify: may include 'ca_file' and 'tls_fingerprint_sha256' for TLS verification
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Construct full URL if repository and path are provided
    if repository and path:
        base_url = url.rstrip("/")
        full_url = f"{base_url}/{repository}/{path.lstrip('/')}"
    else:
        full_url = url

    parsed = urllib.parse.urlparse(full_url)
    if parsed.scheme.lower() != "https":
        raise click.ClickException("Artifactory fetch requires HTTPS URL")

    # Prepare headers
    hdrs = {"Accept": "application/x-pem-file, application/octet-stream, */*"}

    # Authentication: prefer token, fallback to username/password
    token_env = token_ref or "ARTIFACTORY_TOKEN"
    token = os.environ.get(token_env)
    
    if token:
        hdrs["X-JFrog-Art-Api"] = token
    else:
        username_env = username_ref or "ARTIFACTORY_USERNAME"
        password_env = password_ref or "ARTIFACTORY_PASSWORD"
        username = os.environ.get(username_env)
        password = os.environ.get(password_env)
        
        if username and password:
            import base64
            
            creds = f"{username}:{password}"
            encoded = base64.b64encode(creds.encode()).decode()
            hdrs["Authorization"] = f"Basic {encoded}"

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

    # Fetch from Artifactory
    req = urllib.request.Request(full_url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=30, context=context) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        hint = None
        if e.code in (401, 403):
            hint = (
                f"Authentication failed (HTTP {e.code}). Check that the token env variable "
                f"'{token_env}' is set and correct, or provide valid username/password."
            )
        elif e.code == 404:
            hint = f"Artifact not found at {full_url}. Verify the repository and path."
        msg = f"HTTP Error {e.code}: {e.reason} for {full_url}"
        if hint:
            msg = msg + f"\nHint: {hint}"
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
