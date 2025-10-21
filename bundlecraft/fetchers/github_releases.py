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


def _tls_leaf_fingerprint_sha256(host: str, port: int) -> str:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der_cert = ssock.getpeercert(binary_form=True)
    import hashlib

    return hashlib.sha256(der_cert).hexdigest()


def fetch_github_release(
    dest_dir: Path,
    name: str,
    *,
    owner: str,
    repo: str,
    asset_name: str,
    tag: str | None = None,
    token_ref: str | None = None,
    verify: dict | None = None,
) -> Path:
    """Fetch a PEM from GitHub Releases and write to dest.

    Config options:
      - owner: GitHub repository owner/organization (e.g., 'curl')
      - repo: GitHub repository name (e.g., 'curl')
      - asset_name: name of the release asset to download (e.g., 'cacert.pem')
      - tag: release tag (e.g., 'v1.0.0'). If not provided, fetches from latest release
      - token_ref: env var for GitHub token (defaults to GITHUB_TOKEN, optional for public repos)
      - verify: may include 'ca_file' and 'tls_fingerprint_sha256' for TLS verification
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / (name if name.endswith(".pem") else f"{name}.pem")

    # Build GitHub API URL
    base_url = "https://api.github.com"
    if tag:
        api_url = f"{base_url}/repos/{owner}/{repo}/releases/tags/{tag}"
    else:
        api_url = f"{base_url}/repos/{owner}/{repo}/releases/latest"

    # Prepare headers
    hdrs = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "BundleCraft-Fetcher/1.0",
    }

    # Optional authentication
    token_env = token_ref or "GITHUB_TOKEN"
    token = os.environ.get(token_env)
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
    parsed = urllib.parse.urlparse(api_url)
    if tls_fingerprint:
        host = parsed.hostname or ""
        port = parsed.port or 443
        actual_fp = _tls_leaf_fingerprint_sha256(host, port)
        if actual_fp.lower() != str(tls_fingerprint).lower():
            raise click.ClickException(
                f"TLS fingerprint mismatch for {host}:{port}: expected {tls_fingerprint}, got {actual_fp}"
            )

    # Fetch release metadata
    req = urllib.request.Request(api_url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=30, context=context) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        hint = None
        if e.code == 404:
            if tag:
                hint = f"Release with tag '{tag}' not found in {owner}/{repo}"
            else:
                hint = f"No releases found in {owner}/{repo}"
        elif e.code in (401, 403):
            hint = (
                f"Authentication failed (HTTP {e.code}). For private repos, set '{token_env}' "
                "environment variable with a GitHub token."
            )
        msg = f"HTTP Error {e.code}: {e.reason} for {api_url}"
        if hint:
            msg = msg + f"\nHint: {hint}"
        raise click.ClickException(msg) from e

    # Find the asset
    assets = release_data.get("assets", [])
    asset_url = None
    for asset in assets:
        if asset.get("name") == asset_name:
            asset_url = asset.get("browser_download_url")
            break

    if not asset_url:
        available = [a.get("name") for a in assets]
        raise click.ClickException(
            f"Asset '{asset_name}' not found in release. Available assets: {', '.join(available)}"
        )

    # Download the asset
    asset_req = urllib.request.Request(asset_url, headers=hdrs)
    try:
        with urllib.request.urlopen(asset_req, timeout=30, context=context) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        msg = f"Failed to download asset: HTTP Error {e.code}: {e.reason}"
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
