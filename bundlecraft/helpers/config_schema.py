"""
Configuration schema definitions for BundleCraft fetchers.

This module provides schema definitions and validation for all supported fetcher types,
including cloud storage providers, artifact repositories, key management systems,
and public root certificate programs.
#!/usr/bin/env python3
"""
config_schema.py
Pydantic v2 schema models for validating BundleCraft configuration files.

Provides comprehensive validation for:
- Bundle configs (config/bundles/*.yaml)
- Craft configs (config/crafts/*.yaml)
- Defaults config (config/defaults.yaml)

Features:
- Required field enforcement
- Type validation
- Value constraints (min lengths, numeric ranges, valid format names)
- Cross-field validation (duplicate names, conflicts)
- Reserved name protection
- Clear, actionable error messages
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


# Schema definitions for each fetcher type
FETCHER_SCHEMAS: dict[str, dict[str, Any]] = {
    FETCHER_TYPE_URL: {
        "description": "Fetch from HTTPS or file:// URL",
        "required_fields": ["url"],
        "optional_fields": ["name", "verify"],
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
        "optional_fields": ["name", "provider", "token_ref", "verify"],
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
        "optional_fields": [
            "name",
            "mount_point",
            "pem_field",
            "addr",
            "token_ref",
            "namespace",
            "verify",
        ],
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
        "optional_fields": [
            "name",
            "region",
            "endpoint_url",
            "access_key_ref",
            "secret_key_ref",
            "verify",
        ],
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
        "optional_fields": [
            "name",
            "account_name",
            "account_url",
            "connection_string_ref",
            "sas_token_ref",
            "verify",
        ],
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
        "optional_fields": ["name", "project", "credentials_ref", "verify"],
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
        "optional_fields": [
            "name",
            "repository",
            "path",
            "username_ref",
            "password_ref",
            "token_ref",
            "verify",
        ],
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
        "optional_fields": ["name", "tag", "token_ref", "verify"],
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
        "optional_fields": [
            "name",
            "version",
            "tenant_id_ref",
            "client_id_ref",
            "client_secret_ref",
            "verify",
        ],
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
        "optional_fields": ["name", "url", "verify"],
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
        "optional_fields": ["name", "url", "verify"],
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
        "optional_fields": ["name", "url", "verify"],
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
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =====================================================================
# Enums for constrained values
# =====================================================================


class OutputFormat(str, Enum):
    """Valid output format names."""

    PEM = "pem"
    P7B = "p7b"
    JKS = "jks"
    P12 = "p12"
    PKCS12 = "pkcs12"
    DER = "der"


class FetchType(str, Enum):
    """Valid fetch type values."""

    URL = "url"
    HTTPS = "https"
    HTTP = "http"
    FILE = "file"
    VAULT = "vault"
    API = "api"


class DistributionTargetType(str, Enum):
    """Valid distribution target types."""

    GITHUB_RELEASE = "github-release"
    ARTIFACTORY = "artifactory"
    S3 = "s3"
    CUSTOM = "custom"


# =====================================================================
# Supporting models (nested structures)
# =====================================================================


class MetadataModel(BaseModel):
    """Metadata section for bundles/crafts."""

    model_config = ConfigDict(extra="allow")  # Allow additional metadata fields

    owner: str | None = None
    contact: str | None = None
    purpose: str | None = None
    upstream: str | None = None
    tags: list[str] = Field(default_factory=list)
    environment_tier: str | None = None
    approval_required: bool | None = None
    maintainer: str | None = None
    policy_version: str | int | float | None = None

    @field_validator("policy_version", mode="before")
    @classmethod
    def convert_policy_version_to_str(cls, v: str | int | float | None) -> str | None:
        """Convert numeric policy versions to strings."""
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class RepoEntry(BaseModel):
    """Repository entry in bundle config."""

    name: str = Field(min_length=1, description="Repository name")
    include: list[str | dict[str, str]] = Field(
        default_factory=list, description="File paths to include or inline PEM blocks"
    )
    exclude: list[str] = Field(default_factory=list, description="File paths to exclude")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty and not a reserved keyword."""
        reserved = {"include", "exclude", "fetch"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved name and cannot be used")
        return v

    @field_validator("include")
    @classmethod
    def validate_include_items(cls, v: list[str | dict[str, str]]) -> list[str | dict[str, str]]:
        """Validate that dict items have either 'path' or 'inline' key."""
        for item in v:
            if isinstance(item, dict):
                if "inline" not in item and "path" not in item:
                    raise ValueError("Include dict must have either 'inline' or 'path' key")
        return v


class FetchEntry(BaseModel):
    """Fetch entry in bundle config."""

    name: str = Field(min_length=1, description="Fetch source name")
    type: FetchType = Field(description="Fetch type (url, vault, api, etc.)")
    url: str | None = Field(None, description="URL for url/https/http fetch types")
    addr: str | None = Field(None, description="Vault server address")
    mount: str | None = Field(None, description="Vault mount path")
    path: str | None = Field(None, description="Vault secret path or file path")
    token_ref: str | None = Field(None, description="Environment variable for Vault token")
    endpoint: str | None = Field(None, description="API endpoint URL")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers for API")
    bearer_token_env: str | None = Field(None, description="Environment variable for bearer token")
    timeout: int | None = Field(
        None, ge=1, le=600, description="Request timeout in seconds (overrides default)"
    )
    retries: int | None = Field(
        None, ge=0, le=10, description="Number of retry attempts (overrides default)"
    )
    backoff_factor: float | None = Field(
        None, ge=1.0, le=10.0, description="Exponential backoff multiplier (overrides default)"
    )
    retry_on_status: list[int] | None = Field(
        None, description="HTTP status codes to retry (overrides default)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not a reserved keyword."""
        reserved = {"include", "exclude", "fetch", "repo"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved name and cannot be used")
        return v

    @field_validator("url", "endpoint")
    @classmethod
    def validate_url(cls, v: str | None, info) -> str | None:
        """Enforce HTTPS for security (except file:// URLs)."""
        if v and not v.startswith(("https://", "file://")):
            # Allow http:// only for localhost/127.0.0.1
            if not (v.startswith("http://localhost") or v.startswith("http://127.0.0.1")):
                raise ValueError(
                    "Only HTTPS URLs are allowed for security. Use https:// or file:// schemes."
                )
        return v

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> FetchEntry:
        """Validate that required fields are present for each fetch type."""
        if self.type in (FetchType.URL, FetchType.HTTPS, FetchType.HTTP):
            if not self.url:
                raise ValueError(f"'url' is required for fetch type '{self.type.value}'")
        elif self.type == FetchType.VAULT:
            if not self.mount or not self.path:
                raise ValueError(
                    f"'mount' and 'path' are required for fetch type '{self.type.value}'"
                )
        elif self.type == FetchType.API:
            if not self.endpoint:
                raise ValueError(f"'endpoint' is required for fetch type '{self.type.value}'")
        return self


class FiltersModel(BaseModel):
    """Certificate filtering options."""

    unique_by_fingerprint: bool = True
    not_expired_only: bool = True
    ca_certs_only: bool = True
    root_certs_only: bool = False
    signature_algorithms: dict[str, list[str]] | None = None
    minimum_key_size_rsa: int | None = Field(None, ge=1024, description="Minimum RSA key size")
    minimum_key_size_ecc: int | None = Field(None, ge=192, description="Minimum ECC key size")

    @field_validator("minimum_key_size_rsa")
    @classmethod
    def validate_rsa_key_size(cls, v: int | None) -> int | None:
        """Ensure RSA key size is at least 1024 bits."""
        if v is not None and v < 1024:
            raise ValueError("RSA key size must be at least 1024 bits for security")
        return v

    @field_validator("minimum_key_size_ecc")
    @classmethod
    def validate_ecc_key_size(cls, v: int | None) -> int | None:
        """Ensure ECC key size is at least 192 bits."""
        if v is not None and v < 192:
            raise ValueError("ECC key size must be at least 192 bits for security")
        return v


class FetchRetryConfig(BaseModel):
    """Fetch retry and timeout configuration."""

    timeout: int = Field(30, ge=1, le=600, description="Request timeout in seconds")
    retries: int = Field(3, ge=0, le=10, description="Number of retry attempts")
    backoff_factor: float = Field(
        2.0, ge=1.0, le=10.0, description="Exponential backoff multiplier"
    )
    retry_on_status: list[int] = Field(
        default_factory=lambda: [429, 502, 503, 504],
        description="HTTP status codes to retry",
    )

    @field_validator("retry_on_status")
    @classmethod
    def validate_retry_status_codes(cls, v: list[int]) -> list[int]:
        """Ensure retry status codes are valid HTTP codes."""
        for code in v:
            if not 100 <= code <= 599:
                raise ValueError(f"Invalid HTTP status code: {code}")
        return v


class VerifyModel(BaseModel):
    """Verification settings."""

    fail_on_expired: bool = True
    warn_days_before_expiry: int = Field(30, ge=0, le=365)


class PemModel(BaseModel):
    """PEM formatting options."""

    include_subject_comments: bool = True


class FormatOverridesModel(BaseModel):
    """Format-specific overrides (flexible structure)."""

    model_config = ConfigDict(extra="allow")  # Allow additional format overrides

    jks: dict[str, Any] = Field(default_factory=dict)
    pkcs12: dict[str, Any] = Field(default_factory=dict)
    pem: dict[str, Any] = Field(default_factory=dict)
    p7b: dict[str, Any] = Field(default_factory=dict)


class DistributionTarget(BaseModel):
    """Distribution target configuration."""

    model_config = ConfigDict(extra="allow")  # Allow custom target types and fields

    type: DistributionTargetType | str
    enabled: bool = False
    description: str | None = None
    assets: list[str] = Field(default_factory=list)


class DistributionMetadata(BaseModel):
    """Distribution metadata for CI/CD pipelines."""

    model_config = ConfigDict(extra="allow")  # Allow additional distribution fields

    targets: list[DistributionTarget] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    repositories: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class OutputMetadata(BaseModel):
    """Output metadata configuration for GitOps orchestration."""

    model_config = ConfigDict(extra="allow")  # Allow additional metadata fields

    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="Annotations for Kubernetes/GitOps (e.g., ArgoCD sync-wave)",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Labels for Kubernetes/GitOps (e.g., environment, component)",
    )


class TargetEntry(BaseModel):
    """Target entry in craft config."""

    includes: list[str] | None = Field(None, alias="includes")
    include_bundles: list[str] | None = Field(None, alias="include_bundles")
    compose: list[str] | None = Field(None, alias="compose")

    @model_validator(mode="after")
    def ensure_at_least_one_include(self) -> TargetEntry:
        """Ensure at least one include list is provided."""
        if not self.includes and not self.include_bundles and not self.compose:
            raise ValueError(
                "At least one of 'includes', 'include_bundles', or 'compose' must be provided"
            )
        return self


# =====================================================================
# Main configuration models
# =====================================================================


class BundleConfig(BaseModel):
    """Schema for bundle configuration files (config/bundles/*.yaml)."""

    bundle_name: str = Field(min_length=1, description="Unique bundle identifier")
    description: str = Field(min_length=1, description="Human-readable description")
    repo: list[RepoEntry] = Field(default_factory=list, description="Local repository sources")
    fetch: list[FetchEntry] = Field(default_factory=list, description="Remote fetch sources")
    metadata: MetadataModel = Field(default_factory=MetadataModel)

    @field_validator("bundle_name")
    @classmethod
    def validate_bundle_name(cls, v: str) -> str:
        """Ensure bundle_name is not a reserved keyword."""
        reserved = {"include", "exclude", "fetch", "repo"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved bundle name")
        return v

    @model_validator(mode="after")
    def validate_repo_and_fetch(self) -> BundleConfig:
        """Ensure at least one source is defined and no duplicate names."""
        if not self.repo and not self.fetch:
            raise ValueError("Bundle must have at least one 'repo' or 'fetch' entry")

        # Check for duplicate repo names
        repo_names = [r.name for r in self.repo]
        if len(repo_names) != len(set(repo_names)):
            duplicates = [name for name in repo_names if repo_names.count(name) > 1]
            raise ValueError(f"Duplicate repo names found: {', '.join(set(duplicates))}")

        # Check for duplicate fetch names
        fetch_names = [f.name for f in self.fetch]
        if len(fetch_names) != len(set(fetch_names)):
            duplicates = [name for name in fetch_names if fetch_names.count(name) > 1]
            raise ValueError(f"Duplicate fetch names found: {', '.join(set(duplicates))}")

        # Check for name conflicts between repo and fetch
        conflicts = set(repo_names) & set(fetch_names)
        if conflicts:
            raise ValueError(
                f"Name conflicts between repo and fetch: {', '.join(conflicts)}. "
                "Each source must have a unique name."
            )

        return self


class CraftConfig(BaseModel):
    """Schema for craft configuration files (config/crafts/*.yaml)."""

    name: str = Field(min_length=1, description="Craft display name")
    description: str = Field(min_length=1, description="Human-readable description")
    targets: dict[str, TargetEntry] | list[dict[str, Any]] = Field(
        description="Build targets with bundle composition"
    )
    output_formats: list[OutputFormat | str] = Field(
        default_factory=lambda: ["pem"], description="Output format list"
    )
    package: bool = Field(True, description="Create .tar.gz archives")
    verify: VerifyModel = Field(default_factory=VerifyModel)
    filters: FiltersModel = Field(default_factory=FiltersModel)
    pem: PemModel = Field(default_factory=PemModel)
    format_overrides: FormatOverridesModel = Field(default_factory=FormatOverridesModel)
    distribution_metadata: DistributionMetadata | None = None
    metadata: MetadataModel = Field(default_factory=MetadataModel)
    build_path: str | None = Field(None, description="Custom build output path")
    output_metadata: OutputMetadata | None = Field(
        None, description="Output metadata for GitOps (annotations/labels with templating)"
    )

    @field_validator("output_formats")
    @classmethod
    def validate_output_formats(cls, v: list[str]) -> list[str]:
        """Ensure output formats are valid."""
        valid_formats = {f.value for f in OutputFormat}
        for fmt in v:
            if fmt not in valid_formats:
                raise ValueError(
                    f"Invalid output format '{fmt}'. Valid formats: {', '.join(sorted(valid_formats))}"
                )
        return v

    @model_validator(mode="after")
    def validate_targets(self) -> CraftConfig:
        """Validate targets structure and check for duplicates."""
        if isinstance(self.targets, dict):
            if not self.targets:
                raise ValueError("Craft must have at least one target defined")
            # Check for duplicate target names (already handled by dict keys)
        elif isinstance(self.targets, list):
            if not self.targets:
                raise ValueError("Craft must have at least one target defined")
            target_names = [
                t.get("target_name") or t.get("name") for t in self.targets if isinstance(t, dict)
            ]
            if len(target_names) != len(set(target_names)):
                duplicates = [name for name in target_names if target_names.count(name) > 1]
                raise ValueError(f"Duplicate target names found: {', '.join(set(duplicates))}")
        return self


class DefaultsConfig(BaseModel):
    """Schema for defaults configuration file (config/defaults.yaml)."""

    output_formats: list[OutputFormat | str] = Field(
        default_factory=lambda: ["pem"], description="Default output formats"
    )
    verify: VerifyModel = Field(default_factory=VerifyModel)
    package: bool = False
    pem: PemModel = Field(default_factory=PemModel)
    filters: FiltersModel = Field(default_factory=FiltersModel)
    format_overrides: FormatOverridesModel = Field(default_factory=FormatOverridesModel)
    metadata: MetadataModel = Field(default_factory=MetadataModel)
    fetch: FetchRetryConfig = Field(
        default_factory=FetchRetryConfig,
        description="Default fetch retry and timeout configuration",
    )

    @field_validator("output_formats")
    @classmethod
    def validate_output_formats(cls, v: list[str]) -> list[str]:
        """Ensure output formats are valid."""
        valid_formats = {f.value for f in OutputFormat}
        for fmt in v:
            if fmt not in valid_formats:
                raise ValueError(
                    f"Invalid output format '{fmt}'. Valid formats: {', '.join(sorted(valid_formats))}"
                )
        return v


# =====================================================================
# Validation helper functions
# =====================================================================


def validate_bundle_config(data: dict[str, Any], config_path: str = "") -> BundleConfig:
    """Validate bundle configuration data against schema.

    Args:
        data: Raw configuration dictionary
        config_path: Path to config file (for error messages)

    Returns:
        Validated BundleConfig instance

    Raises:
        ValueError: If validation fails with detailed error message
    """
    try:
        return BundleConfig(**data)
    except Exception as e:
        path_info = f" for {config_path}" if config_path else ""
        raise ValueError(f"Config validation failed{path_info}: \n{e}") from e


def validate_craft_config(data: dict[str, Any], config_path: str = "") -> CraftConfig:
    """Validate craft configuration data against schema.

    Args:
        data: Raw configuration dictionary
        config_path: Path to config file (for error messages)

    Returns:
        Validated CraftConfig instance

    Raises:
        ValueError: If validation fails with detailed error message
    """
    try:
        return CraftConfig(**data)
    except Exception as e:
        path_info = f" for {config_path}" if config_path else ""
        raise ValueError(f"Config validation failed{path_info}: \n{e}") from e


def validate_defaults_config(data: dict[str, Any], config_path: str = "") -> DefaultsConfig:
    """Validate defaults configuration data against schema.

    Args:
        data: Raw configuration dictionary
        config_path: Path to config file (for error messages)

    Returns:
        Validated DefaultsConfig instance

    Raises:
        ValueError: If validation fails with detailed error message
    """
    try:
        return DefaultsConfig(**data)
    except Exception as e:
        path_info = f" for {config_path}" if config_path else ""
        raise ValueError(f"Config validation failed{path_info}: \n{e}") from e
