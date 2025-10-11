#!/usr/bin/env python3
"""
fetch_public_roots.py

Fetches Mozilla's public CA root bundle (cacert.pem) from an authoritative source,
saves it locally under certs/external_public/, and records a SHA256 hash for version tracking.

Supports HTTP(S) proxy through environment variables.
"""

import os
import hashlib
import requests
from pathlib import Path

# === Configuration ===
MOZILLA_PEM_URL = "https://curl.se/ca/cacert.pem"
TARGET_DIR = Path(__file__).resolve().parents[1] / "certs" / "external_public"
TARGET_FILE = TARGET_DIR / "mozilla_cacert.pem"
HASH_FILE = TARGET_FILE.with_suffix(".hash")

def get_proxies():
    """Read proxy configuration from environment variables."""
    return {
        "http": os.environ.get("HTTP_PROXY"),
        "https": os.environ.get("HTTPS_PROXY"),
    }

def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def fetch_mozilla_bundle():
    """Fetch the Mozilla CA bundle and store it locally."""
    print(f"Fetching Mozilla CA bundle from {MOZILLA_PEM_URL}...")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    proxies = get_proxies()
    if proxies["https"]:
        print(f"Using HTTPS proxy: {proxies['https']}")
    elif proxies["http"]:
        print(f"Using HTTP proxy: {proxies['http']}")

    response = requests.get(MOZILLA_PEM_URL, proxies=proxies, timeout=60)
    response.raise_for_status()

    TARGET_FILE.write_bytes(response.content)
    print(f"✅ Saved bundle to {TARGET_FILE}")

    hash_value = compute_sha256(TARGET_FILE)
    HASH_FILE.write_text(hash_value + "\n")
    print(f"🔒 SHA256: {hash_value}")
    print(f"📝 Hash recorded at {HASH_FILE}")

def main():
    try:
        fetch_mozilla_bundle()
        print("\n✔ Mozilla public root bundle fetched successfully.")
    except Exception as e:
        print(f"❌ Failed to fetch Mozilla bundle: {e}")

if __name__ == "__main__":
    main()
