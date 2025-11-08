"""Mozilla CA Bundle fetcher.

This fetcher provides a convenient shortcut to fetch the Mozilla CA Bundle
(curated list of Certificate Authorities included in Mozilla products) from
the official curl.se distribution site.

The Mozilla CA Bundle is extracted from NSS and maintained by the Mozilla
Foundation. It's widely used as a source of trusted root certificates.

Reference: https://curl.se/docs/caextract.html
"""

from __future__ import annotations

from pathlib import Path

from bundlecraft.fetchers.http import fetch_url

# Official Mozilla CA Bundle URL maintained by curl.se
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
    """Fetch Mozilla CA Bundle from curl.se.

    This is a convenience wrapper around the HTTP fetcher that hardcodes
    the URL to the official Mozilla CA Bundle maintained by curl.se.

    Args:
        dest_dir: Destination directory for the downloaded bundle
        name: Optional output filename (default: 'mozilla' -> 'mozilla.pem')
        verify: Optional verification config (sha256, ca_file, tls_fingerprint_sha256)
        root: Optional workspace root for resolving relative paths
        timeout: Request timeout in seconds (default from config: 30)
        retries: Number of retry attempts (default from config: 3)
        backoff_factor: Exponential backoff multiplier (default from config: 2.0)
        retry_on_status: HTTP status codes to retry (default: [429, 502, 503, 504])
        defaults: Global default configuration

    Returns:
        Path to the fetched bundle file

    Example:
        >>> from pathlib import Path
        >>> bundle = fetch_mozilla(
        ...     dest_dir=Path("./cert_sources/fetched"),
        ...     verify={"sha256": "expected-sha256-hash"}
        ... )

    Note:
        The Mozilla CA Bundle is updated regularly. Consider using SHA256
        verification to ensure you're getting an expected version.

    Security:
        - HTTPS-only connection to curl.se
        - Optional SHA256 content verification
        - Optional TLS fingerprint pinning
        - No authentication required (public resource)
    """
    # Use "mozilla" as default name if not specified
    if name is None:
        name = "mozilla"

    # Delegate to HTTP fetcher with hardcoded Mozilla CA Bundle URL
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
