"""
Configuration schema definitions for BundleCraft fetchers.

This module provides schema definitions and validation for all supported fetcher types,
including cloud storage providers, artifact repositories, key management systems,
and public root certificate programs.
"""

from __future__ import annotations

from typing import Any, TypedDict

# Fetcher type constants
FETCHER_TYPE_URL = "url"
FETCHER_TYPE_API = "api"
FETCHER_TYPE_VAULT = "vault"
FETCHER_TYPE_S3 = "s3"
FETCHER_TYPE_AZURE_BLOB = "azure_blob"
FETCHER_TYPE_GCS = "gcs"
FETCHER_TYPE_ARTIFACTORY = "artifactory"
FETCHER_TYPE_GITHUB_RELEASE = "github_release"
FETCHER_TYPE_AZURE_KEYVAULT = "azure_keyvault"
FETCHER_TYPE_MOZILLA_ROOTS = "mozilla_roots"
FETCHER_TYPE_MICROSOFT_ROOTS = "microsoft_roots"
FETCHER_TYPE_APPLE_ROOTS = "apple_roots"

# All supported fetcher types
SUPPORTED_FETCHER_TYPES = {
    FETCHER_TYPE_URL,
    FETCHER_TYPE_API,
    FETCHER_TYPE_VAULT,
    FETCHER_TYPE_S3,
    FETCHER_TYPE_AZURE_BLOB,
    FETCHER_TYPE_GCS,
    FETCHER_TYPE_ARTIFACTORY,
    FETCHER_TYPE_GITHUB_RELEASE,
    FETCHER_TYPE_AZURE_KEYVAULT,
    FETCHER_TYPE_MOZILLA_ROOTS,
    FETCHER_TYPE_MICROSOFT_ROOTS,
    FETCHER_TYPE_APPLE_ROOTS,
}


class VerifyConfig(TypedDict, total=False):
    """Common verification options for all fetchers."""

    sha256: str  # Expected SHA256 hash of fetched content
    ca_file: str  # Path to custom CA certificate for TLS verification
    tls_fingerprint_sha256: str  # Expected SHA256 fingerprint of TLS certificate
    headers: dict[str, str]  # Custom HTTP headers (for API fetcher)


class BaseFetcherConfig(TypedDict, total=False):
    """Base configuration common to all fetchers."""

    name: str  # Name for the fetched resource
    type: str  # Fetcher type
    verify: VerifyConfig  # Verification options
    timeout: int  # Request timeout in seconds (1-600, default: 30)
    retries: int  # Number of retry attempts on transient failures (0-10, default: 3)
    backoff_factor: float  # Exponential backoff multiplier (1.0-10.0, default: 2.0)
    retry_on_status: list[int]  # HTTP status codes that trigger retry (default: [429, 502, 503, 504])


class URLFetcherConfig(BaseFetcherConfig):
    """Configuration for URL (HTTPS/file) fetcher."""

    url: str  # Required: HTTPS or file:// URL


class APIFetcherConfig(BaseFetcherConfig):
    """Configuration for generic API fetcher."""

    endpoint: str  # Required: API endpoint URL (alias: url)
    url: str  # Alias for endpoint
    provider: str  # Optional: Provider hint (e.g., 'keyfactor')
    token_ref: str  # Optional: Environment variable name for ****** token


class VaultFetcherConfig(BaseFetcherConfig):
    """Configuration for HashiCorp Vault fetcher."""

    path: str  # Required: Secret path under the mount point
    mount_point: str  # Optional: KV engine mount name (default: 'secret')
    mount: str  # Alias for mount_point
    engine: str  # Alias for mount_point
    pem_field: str  # Optional: Field name containing PEM (default: 'pem')
    addr: str  # Optional: Vault address (default: VAULT_ADDR env)
    token_ref: str  # Optional: Environment variable for token (default: VAULT_TOKEN)
    namespace: str  # Optional: Vault namespace (Enterprise only)


class S3FetcherConfig(BaseFetcherConfig):
    """Configuration for AWS S3 fetcher."""

    bucket: str  # Required: S3 bucket name
    key: str  # Required: Object key/path
    region: str  # Optional: AWS region
    endpoint_url: str  # Optional: Custom S3 endpoint (for S3-compatible storage)
    access_key_ref: str  # Optional: Environment variable for access key
    secret_key_ref: str  # Optional: Environment variable for secret key


class AzureBlobFetcherConfig(BaseFetcherConfig):
    """Configuration for Azure Blob Storage fetcher."""

    container: str  # Required: Blob container name
    blob_name: str  # Required: Blob name/path
    account_name: str  # Optional: Storage account name
    account_url: str  # Optional: Full storage account URL
    connection_string_ref: str  # Optional: Environment variable for connection string
    sas_token_ref: str  # Optional: Environment variable for SAS token


class GCSFetcherConfig(BaseFetcherConfig):
    """Configuration for Google Cloud Storage fetcher."""

    bucket: str  # Required: GCS bucket name
    blob_name: str  # Required: Blob name/path
    project: str  # Optional: GCP project ID
    credentials_ref: str  # Optional: Environment variable for credentials path


class ArtifactoryFetcherConfig(BaseFetcherConfig):
    """Configuration for JFrog Artifactory fetcher."""

    url: str  # Required: Full artifact URL or base Artifactory URL
    repository: str  # Optional: Repository name (used with path)
    path: str  # Optional: Artifact path (used with repository)
    username_ref: str  # Optional: Environment variable for username
    password_ref: str  # Optional: Environment variable for password
    token_ref: str  # Optional: Environment variable for API token (preferred)


class GitHubReleaseFetcherConfig(BaseFetcherConfig):
    """Configuration for GitHub Releases fetcher."""

    owner: str  # Required: GitHub repository owner/organization
    repo: str  # Required: GitHub repository name
    asset_name: str  # Required: Name of the release asset to download
    tag: str  # Optional: Release tag (default: latest release)
    token_ref: str  # Optional: Environment variable for GitHub token


class AzureKeyVaultFetcherConfig(BaseFetcherConfig):
    """Configuration for Azure Key Vault fetcher."""

    vault_url: str  # Required: Key Vault URL
    certificate_name: str  # Required: Name of the certificate
    version: str  # Optional: Certificate version (default: latest)
    tenant_id_ref: str  # Optional: Environment variable for tenant ID
    client_id_ref: str  # Optional: Environment variable for client ID
    client_secret_ref: str  # Optional: Environment variable for client secret


class RootProgramFetcherConfig(BaseFetcherConfig):
    """Configuration for public root certificate program fetchers."""

    url: str  # Optional: Custom URL (defaults to standard source)


# Common optional fields for all fetchers
COMMON_OPTIONAL_FIELDS = ["name", "verify", "timeout", "retries", "backoff_factor", "retry_on_status"]

# Schema definitions for each fetcher type
FETCHER_SCHEMAS: dict[str, dict[str, Any]] = {
    FETCHER_TYPE_URL: {
        "description": "Fetch from HTTPS or file:// URL",
        "required_fields": ["url"],
        "optional_fields": COMMON_OPTIONAL_FIELDS,
        "example": {
            "name": "external-ca",
            "type": "url",
            "url": "https://example.com/certs/rootCA.pem",
            "verify": {"sha256": "abc123...", "tls_fingerprint_sha256": "def456..."},
        },
    },
    FETCHER_TYPE_API: {
        "description": "Fetch from generic REST API with ****** authentication",
        "required_fields": ["endpoint"],  # or 'url'
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["provider", "token_ref"],
        "example": {
            "name": "api-cert",
            "type": "api",
            "endpoint": "https://pki.company.com/api/v1/certificates/root",
            "token_ref": "PKI_API_TOKEN",
        },
    },
    FETCHER_TYPE_VAULT: {
        "description": "Fetch from HashiCorp Vault KV engine",
        "required_fields": ["path"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["mount_point", "pem_field", "addr", "token_ref", "namespace"],
        "example": {
            "name": "vault-cert",
            "type": "vault",
            "mount_point": "secret",
            "path": "pki/trusted_roots",
            "addr": "https://vault.company.com:8200",
        },
    },
    FETCHER_TYPE_S3: {
        "description": "Fetch from AWS S3 or S3-compatible storage",
        "required_fields": ["bucket", "key"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["region", "endpoint_url", "access_key_ref", "secret_key_ref"],
        "example": {
            "name": "s3-cert",
            "type": "s3",
            "bucket": "my-pki-bucket",
            "key": "certificates/rootCA.pem",
            "region": "us-east-1",
        },
        "dependencies": ["boto3"],
        "install": "pip install 'bundlecraft[cloud]'",
    },
    FETCHER_TYPE_AZURE_BLOB: {
        "description": "Fetch from Azure Blob Storage",
        "required_fields": ["container", "blob_name"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["account_name", "account_url", "connection_string_ref", "sas_token_ref"],
        "example": {
            "name": "azure-blob-cert",
            "type": "azure_blob",
            "container": "pki-certs",
            "blob_name": "certificates/rootCA.pem",
        },
        "dependencies": ["azure-storage-blob", "azure-identity"],
        "install": "pip install 'bundlecraft[cloud]'",
    },
    FETCHER_TYPE_GCS: {
        "description": "Fetch from Google Cloud Storage",
        "required_fields": ["bucket", "blob_name"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["project", "credentials_ref"],
        "example": {
            "name": "gcs-cert",
            "type": "gcs",
            "bucket": "my-pki-bucket",
            "blob_name": "certificates/rootCA.pem",
        },
        "dependencies": ["google-cloud-storage"],
        "install": "pip install 'bundlecraft[cloud]'",
    },
    FETCHER_TYPE_ARTIFACTORY: {
        "description": "Fetch from JFrog Artifactory",
        "required_fields": ["url"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["repository", "path", "username_ref", "password_ref", "token_ref"],
        "example": {
            "name": "artifactory-cert",
            "type": "artifactory",
            "url": "https://artifactory.company.com/artifactory",
            "repository": "libs-release-local",
            "path": "certs/rootCA.pem",
            "token_ref": "ARTIFACTORY_TOKEN",
        },
    },
    FETCHER_TYPE_GITHUB_RELEASE: {
        "description": "Fetch from GitHub Releases",
        "required_fields": ["owner", "repo", "asset_name"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["tag", "token_ref"],
        "example": {
            "name": "github-cert",
            "type": "github_release",
            "owner": "myorg",
            "repo": "pki-certs",
            "asset_name": "rootCA.pem",
            "tag": "v1.0.0",
        },
    },
    FETCHER_TYPE_AZURE_KEYVAULT: {
        "description": "Fetch from Azure Key Vault",
        "required_fields": ["vault_url", "certificate_name"],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["version", "tenant_id_ref", "client_id_ref", "client_secret_ref"],
        "example": {
            "name": "keyvault-cert",
            "type": "azure_keyvault",
            "vault_url": "https://myvault.vault.azure.net/",
            "certificate_name": "my-root-ca",
        },
        "dependencies": ["azure-keyvault-certificates", "azure-identity"],
        "install": "pip install 'bundlecraft[cloud]'",
    },
    FETCHER_TYPE_MOZILLA_ROOTS: {
        "description": "Fetch Mozilla's trusted root certificate bundle",
        "required_fields": [],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["url"],
        "example": {
            "name": "mozilla-roots",
            "type": "mozilla_roots",
            "verify": {"sha256": "abc123..."},
        },
        "default_url": "https://curl.se/ca/cacert.pem",
    },
    FETCHER_TYPE_MICROSOFT_ROOTS: {
        "description": "Fetch Microsoft's trusted root certificate bundle",
        "required_fields": [],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["url"],
        "example": {
            "name": "microsoft-roots",
            "type": "microsoft_roots",
            "verify": {"sha256": "def456..."},
        },
        "default_url": "https://ccadb.my.salesforce-sites.com/microsoft/IncludedRootsPEMTxt?TrustBitsInclude=ServerAuth",
    },
    FETCHER_TYPE_APPLE_ROOTS: {
        "description": "Fetch Apple's trusted root certificate bundle",
        "required_fields": [],
        "optional_fields": COMMON_OPTIONAL_FIELDS + ["url"],
        "example": {
            "name": "apple-roots",
            "type": "apple_roots",
            "verify": {"sha256": "789abc..."},
        },
        "default_url": "https://ccadb.my.salesforce-sites.com/apple/IncludedRootsPEMTxt?TrustBitsInclude=ServerAuth",
    },
}


def get_fetcher_schema(fetcher_type: str) -> dict[str, Any] | None:
    """Get schema definition for a fetcher type.

    Args:
        fetcher_type: The fetcher type (e.g., 's3', 'azure_blob', 'mozilla_roots')

    Returns:
        Schema definition dict or None if type is not supported
    """
    return FETCHER_SCHEMAS.get(fetcher_type)


def is_valid_fetcher_type(fetcher_type: str) -> bool:
    """Check if a fetcher type is supported.

    Args:
        fetcher_type: The fetcher type to validate

    Returns:
        True if the fetcher type is supported, False otherwise
    """
    return fetcher_type in SUPPORTED_FETCHER_TYPES


def get_all_fetcher_types() -> set[str]:
    """Get all supported fetcher types.

    Returns:
        Set of all supported fetcher type strings
    """
    return SUPPORTED_FETCHER_TYPES.copy()


def get_fetcher_categories() -> dict[str, list[str]]:
    """Get fetchers organized by category.

    Returns:
        Dictionary mapping category names to lists of fetcher types
    """
    return {
        "Cloud Storage": [
            FETCHER_TYPE_S3,
            FETCHER_TYPE_AZURE_BLOB,
            FETCHER_TYPE_GCS,
        ],
        "Artifact Repositories": [
            FETCHER_TYPE_ARTIFACTORY,
            FETCHER_TYPE_GITHUB_RELEASE,
        ],
        "Key Management": [
            FETCHER_TYPE_AZURE_KEYVAULT,
            FETCHER_TYPE_VAULT,
        ],
        "Public Root Programs": [
            FETCHER_TYPE_MOZILLA_ROOTS,
            FETCHER_TYPE_MICROSOFT_ROOTS,
            FETCHER_TYPE_APPLE_ROOTS,
        ],
        "Generic Sources": [
            FETCHER_TYPE_URL,
            FETCHER_TYPE_API,
        ],
    }
