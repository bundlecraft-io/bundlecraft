from __future__ import annotations

from pathlib import Path

from bundlecraft.fetchers.http import fetch_url

# Mozilla CA certificate bundle URL
MOZILLA_CA_BUNDLE_URL = "https://curl.se/ca/cacert.pem"


def fetch_mozilla(
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
    """Fetch the Mozilla CA certificate bundle.

    This is a convenience wrapper around the URL fetcher that retrieves
    the Mozilla root certificate store from https://curl.se/ca/cacert.pem

    This bundle is extracted from Mozilla's NSS library and is widely used
    as a trusted root certificate store. It is maintained by the curl project
    and updated regularly.

    See: https://curl.se/docs/caextract.html

    Config options:
      - name: Output filename (optional, defaults to 'mozilla-roots')
      - verify: Verification options (sha256, ca_file, tls_fingerprint_sha256)
      - root: Workspace root for resolving relative paths
      - timeout: operation timeout in seconds
      - retries: number of retry attempts
      - backoff_factor: exponential backoff multiplier
      - retry_on_status: HTTP status codes to retry on

    Example configuration:
      fetch:
        - name: mozilla_roots
          type: mozilla
          verify:
            sha256: "expected-sha256-of-current-bundle"
    """
    # Default name if not provided
    if not name:
        name = "mozilla-roots"

    # Use the http fetcher with the Mozilla CA bundle URL
    return fetch_url(
        url=MOZILLA_CA_BUNDLE_URL,
        dest_dir=dest_dir,
        name=name,
        verify=verify,
        root=root,
        timeout=timeout,
        retries=retries,
        backoff_factor=backoff_factor,
        retry_on_status=retry_on_status,
        defaults=defaults,
    )
