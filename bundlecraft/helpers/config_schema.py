"""
config_schema.py
----------------
Configuration schema validation for BundleCraft.

This module provides schema definitions and validation functions for:
- Bundle configurations (sources, fetch, repo)
- Craft configurations (targets, output formats, signing)
- Environment variable validation for signing operations

The validation ensures configuration files conform to expected structures
and prevents common configuration errors before they cause runtime issues.
"""

from typing import Any, Literal

SigningMethod = Literal["gpg", "sigstore", "none"]


# =====================================================================
# Environment Variable Schemas
# =====================================================================

ENV_VAR_SCHEMA = {
    # Signing configuration
    "BUNDLECRAFT_SIGN_METHOD": {
        "type": "string",
        "allowed_values": ["gpg", "sigstore", "none"],
        "default": "none",
        "description": "Signing method for artifacts",
    },
    "BUNDLECRAFT_GPG_KEY_ID": {
        "type": "string",
        "required_when": {"BUNDLECRAFT_SIGN_METHOD": "gpg"},
        "description": "GPG key ID or fingerprint for signing",
    },
    "BUNDLECRAFT_GPG_PASSPHRASE": {
        "type": "string",
        "sensitive": True,
        "description": "GPG key passphrase (use secure vault in production)",
    },
    "BUNDLECRAFT_GPG_HOME": {
        "type": "string",
        "description": "Custom GPG home directory",
    },
    # Format-specific passwords
    "TRUST_JKS_PASSWORD": {
        "type": "string",
        "sensitive": True,
        "default": "changeit",
        "description": "Password for Java KeyStore (.jks) files",
    },
    "TRUST_P12_PASSWORD": {
        "type": "string",
        "sensitive": True,
        "default": "changeit",
        "description": "Password for PKCS#12 (.p12) files",
    },
}


# =====================================================================
# Bundle Configuration Schema
# =====================================================================

BUNDLE_CONFIG_SCHEMA = {
    "bundle_name": {
        "type": "string",
        "required": True,
        "description": "Unique identifier for the bundle",
    },
    "description": {
        "type": "string",
        "required": False,
        "description": "Human-readable description of the bundle",
    },
    "repo": {
        "type": "list",
        "required": False,
        "description": "Local certificate sources with named repositories",
        "item_schema": {
            "name": {
                "type": "string",
                "required": True,
                "reserved_names": ["include"],
                "description": "Unique name for this repository",
            },
            "include": {
                "type": "list",
                "required": True,
                "description": "List of file paths or inline PEM entries to include",
            },
            "exclude": {
                "type": "list",
                "required": False,
                "description": "List of file paths to exclude",
            },
        },
    },
    "fetch": {
        "type": "list",
        "required": False,
        "description": "Remote certificate sources to fetch at build time",
        "item_schema": {
            "name": {
                "type": "string",
                "required": True,
                "reserved_names": ["include"],
                "description": "Unique name for this fetch source",
            },
            "type": {
                "type": "string",
                "required": True,
                "allowed_values": ["url", "api", "vault"],
                "description": "Type of remote source",
            },
            "url": {
                "type": "string",
                "required_when": {"type": ["url", "api"]},
                "description": "URL to fetch certificates from",
            },
            "verify": {
                "type": "dict",
                "required": False,
                "description": "Verification options for HTTPS connections",
                "schema": {
                    "ca_file": {
                        "type": "string",
                        "description": "Path to CA certificate file",
                    },
                    "tls_fingerprint_sha256": {
                        "type": "string",
                        "description": "Expected TLS certificate fingerprint",
                    },
                    "sha256": {
                        "type": "string",
                        "description": "Expected content SHA256 hash",
                    },
                },
            },
        },
    },
}


# =====================================================================
# Craft Configuration Schema
# =====================================================================

CRAFT_CONFIG_SCHEMA = {
    "name": {
        "type": "string",
        "required": False,
        "description": "Display name for the craft",
    },
    "description": {
        "type": "string",
        "required": False,
        "description": "Human-readable description of the craft",
    },
    "targets": {
        "type": "dict",
        "required": False,
        "description": "Target bundles to build in this craft",
        "value_schema": {
            "includes": {
                "type": "list",
                "required": True,
                "description": "List of bundle names to include in this target",
            },
            "description": {
                "type": "string",
                "required": False,
                "description": "Description of this target",
            },
        },
    },
    "output_formats": {
        "type": "list",
        "required": False,
        "allowed_values": ["pem", "p7b", "jks", "p12", "zip"],
        "default": ["pem"],
        "description": "Certificate formats to generate",
    },
    "package": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Create .tar.gz archive of build output",
    },
    "build_path": {
        "type": "string",
        "required": False,
        "description": "Custom output directory path",
    },
    "verify": {
        "type": "dict",
        "required": False,
        "description": "Certificate verification settings",
        "schema": {
            "fail_on_expired": {
                "type": "boolean",
                "default": True,
                "description": "Abort build if expired certificates found",
            },
            "warn_days_before_expiry": {
                "type": "integer",
                "default": 30,
                "description": "Warn if certificate expires within N days",
            },
        },
    },
    "filters": {
        "type": "dict",
        "required": False,
        "description": "Certificate filtering rules",
        "schema": {
            "unique_by_fingerprint": {
                "type": "boolean",
                "default": True,
                "description": "Deduplicate by SHA256 fingerprint",
            },
            "not_expired_only": {
                "type": "boolean",
                "default": True,
                "description": "Exclude expired certificates",
            },
            "ca_certs_only": {
                "type": "boolean",
                "default": True,
                "description": "Only include CA certificates",
            },
            "root_certs_only": {
                "type": "boolean",
                "default": True,
                "description": "Only include self-signed root CAs",
            },
            "signature_algorithms": {
                "type": "dict",
                "required": False,
                "description": "Filter by signature algorithm",
                "schema": {
                    "include": {
                        "type": "list",
                        "description": "Whitelist of allowed algorithms",
                    },
                    "exclude": {
                        "type": "list",
                        "description": "Blacklist of disallowed algorithms",
                    },
                },
            },
            "minimum_key_size_rsa": {
                "type": "integer",
                "default": 2048,
                "description": "Minimum RSA key size in bits",
            },
            "minimum_key_size_ecc": {
                "type": "integer",
                "default": 256,
                "description": "Minimum ECC key size in bits",
            },
        },
    },
    "format_overrides": {
        "type": "dict",
        "required": False,
        "description": "Format-specific configuration overrides",
        "schema": {
            "jks": {
                "type": "dict",
                "schema": {
                    "storepass_env": {
                        "type": "string",
                        "default": "TRUST_JKS_PASSWORD",
                        "description": "Environment variable for JKS password",
                    },
                    "alias_format": {
                        "type": "string",
                        "default": "{subject.CN}-{serial}",
                        "description": "Template for certificate aliases",
                    },
                },
            },
            "pkcs12": {
                "type": "dict",
                "schema": {
                    "password_env": {
                        "type": "string",
                        "default": "TRUST_P12_PASSWORD",
                        "description": "Environment variable for P12 password",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Custom output filename",
                    },
                },
            },
            "pem": {
                "type": "dict",
                "schema": {
                    "include_subject_comments": {
                        "type": "boolean",
                        "default": True,
                        "description": "Add subject comments above PEM blocks",
                    },
                },
            },
        },
    },
    "signing": {
        "type": "dict",
        "required": False,
        "description": "Artifact signing configuration",
        "schema": {
            "enabled": {
                "type": "boolean",
                "default": False,
                "description": "Enable artifact signing",
            },
            "method": {
                "type": "string",
                "allowed_values": ["gpg", "sigstore", "none"],
                "default": "none",
                "description": "Signing method to use",
            },
            "gpg": {
                "type": "dict",
                "required_when": {"method": "gpg"},
                "description": "GPG-specific configuration",
                "schema": {
                    "key_id_env": {
                        "type": "string",
                        "default": "BUNDLECRAFT_GPG_KEY_ID",
                        "description": "Environment variable for GPG key ID",
                    },
                    "passphrase_env": {
                        "type": "string",
                        "default": "BUNDLECRAFT_GPG_PASSPHRASE",
                        "description": "Environment variable for GPG passphrase",
                    },
                    "home_env": {
                        "type": "string",
                        "default": "BUNDLECRAFT_GPG_HOME",
                        "description": "Environment variable for GPG home directory",
                    },
                },
            },
            "artifacts": {
                "type": "list",
                "default": ["manifest.json"],
                "description": "List of artifacts to sign",
            },
        },
    },
    "distribution": {
        "type": "dict",
        "required": False,
        "description": "Distribution configuration for CI/CD",
        "schema": {
            "targets": {
                "type": "list",
                "description": "Distribution targets",
            },
            "tags": {
                "type": "list",
                "description": "Tags for CI/CD routing",
            },
        },
    },
    "metadata": {
        "type": "dict",
        "required": False,
        "description": "Optional metadata",
    },
}


# =====================================================================
# Validation Functions
# =====================================================================


def validate_signing_config(config: dict[str, Any]) -> list[str]:
    """Validate signing configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    signing = config.get("signing", {})
    if not isinstance(signing, dict):
        return errors  # Optional, skip if not present

    method = signing.get("method", "none")
    if method not in ("gpg", "sigstore", "none"):
        errors.append(f"Invalid signing method: {method}. Must be 'gpg', 'sigstore', or 'none'")

    if method == "gpg":
        gpg_config = signing.get("gpg", {})
        if not isinstance(gpg_config, dict):
            errors.append("GPG configuration must be a dictionary when method is 'gpg'")

    artifacts = signing.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("Signing artifacts must be a list")

    return errors


def validate_output_formats(formats: list[str]) -> list[str]:
    """Validate output format list.

    Args:
        formats: List of format names

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    allowed = {"pem", "p7b", "jks", "p12", "zip"}

    if not isinstance(formats, list):
        errors.append("output_formats must be a list")
        return errors

    for fmt in formats:
        if fmt not in allowed:
            errors.append(
                f"Invalid output format: {fmt}. Allowed: {', '.join(sorted(allowed))}"
            )

    return errors


def validate_env_var_signing(env_vars: dict[str, str | None]) -> list[str]:
    """Validate signing-related environment variables.

    Args:
        env_vars: Dictionary of environment variable names to values

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    method = env_vars.get("BUNDLECRAFT_SIGN_METHOD", "none")
    if method not in ("gpg", "sigstore", "none"):
        errors.append(
            f"Invalid BUNDLECRAFT_SIGN_METHOD: {method}. Must be 'gpg', 'sigstore', or 'none'"
        )

    if method == "gpg":
        if not env_vars.get("BUNDLECRAFT_GPG_KEY_ID"):
            errors.append(
                "BUNDLECRAFT_GPG_KEY_ID is required when BUNDLECRAFT_SIGN_METHOD is 'gpg'"
            )

    return errors


def get_schema_documentation() -> dict[str, Any]:
    """Get schema documentation for generating help text.

    Returns:
        Dictionary containing schema documentation
    """
    return {
        "bundle_config": BUNDLE_CONFIG_SCHEMA,
        "craft_config": CRAFT_CONFIG_SCHEMA,
        "environment_variables": ENV_VAR_SCHEMA,
    }
