#!/usr/bin/env python3
"""
config_schema.py
Pydantic models for validating BundleCraft configuration files.

Provides schema validation for:
- Bundle configs (config/bundles/*.yaml)
- Craft configs (config/crafts/*.yaml)
- Defaults config (config/defaults.yaml)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# =====================================================================
# Bundle Configuration Schema
# =====================================================================


class RepoIncludeItem(BaseModel):
    """Schema for repo include items - supports path strings or inline PEM."""

    path: str | None = None
    inline: str | None = None
    name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_include_item(cls, data: Any) -> dict:
        """Allow string items (paths) or dict items (path/inline)."""
        if isinstance(data, str):
            return {"path": data}
        if isinstance(data, dict):
            if not data.get("path") and not data.get("inline"):
                raise ValueError("Include item must have either 'path' or 'inline' field")
            if data.get("path") and data.get("inline"):
                raise ValueError("Include item cannot have both 'path' and 'inline' fields")
        return data


class RepoConfig(BaseModel):
    """Schema for named repository sources in bundle configs."""

    name: str = Field(..., min_length=1, description="Unique repository name")
    include: list[str | RepoIncludeItem] = Field(
        default_factory=list, description="List of paths or inline PEM items to include"
    )
    exclude: list[str] = Field(default_factory=list, description="Optional exclusion patterns")

    @field_validator("name")
    @classmethod
    def validate_name_not_reserved(cls, v: str) -> str:
        """Ensure name is not a reserved keyword."""
        reserved = {"include", "exclude", "fetch"}
        if v.lower() in reserved:
            raise ValueError(f"Repository name '{v}' is reserved. Choose a different name.")
        return v


class FetchVerifyConfig(BaseModel):
    """Schema for fetch verification settings."""

    sha256: str | None = Field(None, description="Expected SHA256 hash for content pinning")
    ca_file: str | None = Field(None, description="Path to CA certificate for TLS verification")
    tls_fingerprint_sha256: str | None = Field(
        None, description="TLS certificate fingerprint for pinning"
    )


class FetchConfig(BaseModel):
    """Schema for remote fetch sources in bundle configs."""

    name: str | None = Field(None, description="Optional unique fetch source name")
    type: Literal["url", "api", "vault"] = Field("url", description="Fetch source type")
    url: str | None = Field(None, description="URL for url/api fetch types")
    endpoint: str | None = Field(None, description="API endpoint (for api type)")
    token_ref: str | None = Field(None, description="Environment variable name for auth token")
    verify: FetchVerifyConfig | None = Field(None, description="Verification settings")
    mount_point: str | None = Field(None, description="Vault mount point")
    path: str | None = Field(None, description="Vault secret path")
    pem_field: str | None = Field(None, description="Vault PEM field name")
    addr: str | None = Field(None, description="Vault server address")

    @field_validator("name")
    @classmethod
    def validate_name_not_reserved(cls, v: str | None) -> str | None:
        """Ensure name is not a reserved keyword."""
        if v is None:
            return v
        reserved = {"include", "exclude", "fetch"}
        if v.lower() in reserved:
            raise ValueError(f"Fetch name '{v}' is reserved. Choose a different name.")
        return v

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> FetchConfig:
        """Validate that required fields are present for each fetch type."""
        if self.type == "url" and not self.url:
            raise ValueError("Fetch type 'url' requires 'url' field")
        if self.type == "api":
            if not self.endpoint and not self.url:
                raise ValueError("Fetch type 'api' requires 'endpoint' or 'url' field")
        if self.type == "vault":
            if not self.mount_point or not self.path:
                raise ValueError("Fetch type 'vault' requires 'mount_point' and 'path' fields")
        return self


class BundleMetadata(BaseModel):
    """Schema for bundle metadata."""

    owner: str | None = None
    purpose: str | None = None
    change_control: str | None = None
    tags: list[str] = Field(default_factory=list)


class BundleConfig(BaseModel):
    """Schema for bundle configuration files (config/bundles/*.yaml)."""

    bundle_name: str = Field(..., min_length=1, description="Bundle identifier")
    description: str = Field(..., min_length=1, description="Bundle description")
    repo: list[RepoConfig] = Field(
        default_factory=list, description="Named repository sources (preferred schema)"
    )
    include: list[str] = Field(
        default_factory=list, description="Legacy flat include paths (backward compatibility)"
    )
    exclude: list[str] = Field(
        default_factory=list, description="Legacy flat exclude patterns"
    )
    fetch: list[FetchConfig] = Field(default_factory=list, description="Remote fetch sources")
    metadata: BundleMetadata | None = Field(None, description="Optional metadata")

    @model_validator(mode="after")
    def validate_repo_names_unique(self) -> BundleConfig:
        """Ensure all repo names are unique."""
        if not self.repo:
            return self
        repo_names = [r.name for r in self.repo]
        if len(repo_names) != len(set(repo_names)):
            duplicates = [name for name in repo_names if repo_names.count(name) > 1]
            raise ValueError(f"Duplicate repository names found: {', '.join(set(duplicates))}")
        return self

    @model_validator(mode="after")
    def validate_fetch_names_unique(self) -> BundleConfig:
        """Ensure all explicit fetch names are unique."""
        if not self.fetch:
            return self
        fetch_names = [f.name for f in self.fetch if f.name]
        if fetch_names and len(fetch_names) != len(set(fetch_names)):
            duplicates = [name for name in fetch_names if fetch_names.count(name) > 1]
            raise ValueError(f"Duplicate fetch names found: {', '.join(set(duplicates))}")
        return self

    @model_validator(mode="after")
    def validate_no_repo_fetch_conflicts(self) -> BundleConfig:
        """Ensure no name conflicts between repo and fetch."""
        if not self.repo or not self.fetch:
            return self
        repo_names = {r.name for r in self.repo}
        fetch_names = {f.name for f in self.fetch if f.name}
        conflicts = repo_names.intersection(fetch_names)
        if conflicts:
            raise ValueError(
                f"Name conflict between repo and fetch entries: {', '.join(sorted(conflicts))}"
            )
        return self


# =====================================================================
# Craft Configuration Schema
# =====================================================================


class TargetConfig(BaseModel):
    """Schema for craft target composition."""

    includes: list[str] | None = Field(None, description="List of bundle names to include")
    include_bundles: list[str] | None = Field(None, description="Alias for includes")
    compose: list[str] | None = Field(None, description="Alias for includes")

    @model_validator(mode="after")
    def normalize_includes(self) -> TargetConfig:
        """Normalize various include field names to 'includes'."""
        if self.includes is None:
            self.includes = self.include_bundles or self.compose or []
        return self


class VerifyConfig(BaseModel):
    """Schema for certificate verification settings."""

    fail_on_expired: bool = Field(True, description="Abort build on expired certificates")
    warn_days_before_expiry: int = Field(
        30, ge=0, description="Warn when cert expires within N days"
    )


class SignatureAlgorithmsFilter(BaseModel):
    """Schema for signature algorithm filtering."""

    include: list[str] = Field(default_factory=list, description="Whitelist of algorithms")
    exclude: list[str] = Field(default_factory=list, description="Blacklist of algorithms")


class FiltersConfig(BaseModel):
    """Schema for certificate filtering settings."""

    unique_by_fingerprint: bool = Field(True, description="Deduplicate by SHA256 fingerprint")
    not_expired_only: bool = Field(True, description="Exclude expired certificates")
    ca_certs_only: bool = Field(True, description="Only include CA certificates")
    root_certs_only: bool = Field(True, description="Only include self-signed root CAs")
    signature_algorithms: SignatureAlgorithmsFilter | None = Field(
        None, description="Filter by signature algorithm"
    )
    minimum_key_size_rsa: int | None = Field(
        None, ge=1024, description="Minimum RSA key size in bits"
    )
    minimum_key_size_ecc: int | None = Field(
        None, ge=160, description="Minimum ECC key size in bits"
    )


class PemConfig(BaseModel):
    """Schema for PEM output configuration."""

    include_subject_comments: bool = Field(
        True, description="Add '# Subject:' comments above each PEM block"
    )


class FormatOverrideConfig(BaseModel):
    """Schema for format-specific overrides."""

    storepass_env: str | None = Field(None, description="Environment variable for JKS password")
    password_env: str | None = Field(None, description="Environment variable for P12 password")
    alias_format: str | None = Field(
        None, description="Template for certificate aliases/friendly names"
    )
    filename: str | None = Field(None, description="Default output filename")


class DistributionTargetConfig(BaseModel):
    """Schema for distribution target metadata."""

    type: str = Field(..., description="Distribution target type (e.g., github-release, s3)")
    enabled: bool = Field(True, description="Whether this target is enabled")
    description: str | None = Field(None, description="Human-readable description")
    # Allow additional arbitrary fields for target-specific config
    model_config = {"extra": "allow"}


class DistributionMetadata(BaseModel):
    """Schema for distribution metadata (CI/CD use only)."""

    targets: list[DistributionTargetConfig] = Field(
        default_factory=list, description="Distribution targets"
    )
    tags: list[str] = Field(default_factory=list, description="CI/CD tags")


class CraftMetadata(BaseModel):
    """Schema for craft metadata."""

    name: str | None = None
    contact: str | None = None
    environment_tier: str | None = None
    compliance: str | None = None
    approval_required: bool | None = None
    maintainer: str | None = None
    policy_version: str | None = None


class CraftConfig(BaseModel):
    """Schema for craft configuration files (config/crafts/*.yaml)."""

    name: str | None = Field(None, description="Craft display name")
    description: str | None = Field(None, description="Craft description")
    targets: dict[str, TargetConfig] | list[dict[str, Any]] | None = Field(
        None, description="Target composition map or list"
    )
    output_formats: list[str] = Field(
        default_factory=lambda: ["pem"], description="Output formats to generate"
    )
    package: bool = Field(False, description="Create .tar.gz archives")
    verify: VerifyConfig | None = Field(None, description="Verification settings")
    filters: FiltersConfig | None = Field(None, description="Certificate filtering settings")
    pem: PemConfig | None = Field(None, description="PEM output configuration")
    format_overrides: dict[str, FormatOverrideConfig] | None = Field(
        None, description="Format-specific overrides"
    )
    distribution_metadata: DistributionMetadata | None = Field(
        None, description="Distribution metadata for CI/CD"
    )
    metadata: CraftMetadata | None = Field(None, description="Optional metadata")

    @field_validator("output_formats")
    @classmethod
    def validate_output_formats(cls, v: list[str]) -> list[str]:
        """Validate output format values."""
        valid_formats = {"pem", "p7b", "jks", "p12", "pkcs12"}
        for fmt in v:
            if fmt.lower() not in valid_formats:
                raise ValueError(
                    f"Invalid output format '{fmt}'. Valid formats: {', '.join(sorted(valid_formats))}"
                )
        return v

    @model_validator(mode="after")
    def validate_targets(self) -> CraftConfig:
        """Normalize targets to dict format."""
        if isinstance(self.targets, list):
            # Convert list format to dict format
            targets_dict = {}
            for item in self.targets:
                if isinstance(item, dict):
                    tname = item.get("target_name") or item.get("name")
                    if tname:
                        targets_dict[tname] = TargetConfig(
                            includes=item.get("include_bundles")
                            or item.get("includes")
                            or item.get("compose")
                        )
            self.targets = targets_dict
        return self


# =====================================================================
# Defaults Configuration Schema
# =====================================================================


class DefaultsConfig(BaseModel):
    """Schema for defaults configuration file (config/defaults.yaml)."""

    output_formats: list[str] = Field(
        default_factory=lambda: ["pem", "p7b", "jks", "p12"], description="Default output formats"
    )
    package: bool = Field(False, description="Create .tar.gz archives by default")
    verify: VerifyConfig | None = Field(None, description="Default verification settings")
    filters: FiltersConfig | None = Field(None, description="Default certificate filtering")
    pem: PemConfig | None = Field(None, description="Default PEM output configuration")
    format_overrides: dict[str, FormatOverrideConfig] | None = Field(
        None, description="Default format-specific overrides"
    )
    metadata: CraftMetadata | None = Field(None, description="Default metadata")

    @field_validator("output_formats")
    @classmethod
    def validate_output_formats(cls, v: list[str]) -> list[str]:
        """Validate output format values."""
        valid_formats = {"pem", "p7b", "jks", "p12", "pkcs12"}
        for fmt in v:
            if fmt.lower() not in valid_formats:
                raise ValueError(
                    f"Invalid output format '{fmt}'. Valid formats: {', '.join(sorted(valid_formats))}"
                )
        return v


# =====================================================================
# Validation Functions
# =====================================================================


def validate_bundle_config(config_data: dict[str, Any]) -> BundleConfig:
    """Validate and parse bundle configuration.

    Args:
        config_data: Raw configuration dictionary from YAML

    Returns:
        Validated BundleConfig model

    Raises:
        ValueError: If validation fails with detailed error messages
    """
    try:
        return BundleConfig.model_validate(config_data)
    except Exception as e:
        raise ValueError(f"Bundle config validation failed: {e}") from e


def validate_craft_config(config_data: dict[str, Any]) -> CraftConfig:
    """Validate and parse craft configuration.

    Args:
        config_data: Raw configuration dictionary from YAML

    Returns:
        Validated CraftConfig model

    Raises:
        ValueError: If validation fails with detailed error messages
    """
    try:
        return CraftConfig.model_validate(config_data)
    except Exception as e:
        raise ValueError(f"Craft config validation failed: {e}") from e


def validate_defaults_config(config_data: dict[str, Any]) -> DefaultsConfig:
    """Validate and parse defaults configuration.

    Args:
        config_data: Raw configuration dictionary from YAML

    Returns:
        Validated DefaultsConfig model

    Raises:
        ValueError: If validation fails with detailed error messages
    """
    try:
        return DefaultsConfig.model_validate(config_data)
    except Exception as e:
        raise ValueError(f"Defaults config validation failed: {e}") from e
