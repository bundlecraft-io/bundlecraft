#!/usr/bin/env python3
"""
test_config_validation.py
Comprehensive negative test suite for configuration validation.

Tests invalid configurations to ensure schema validation catches errors early.
"""

import pytest
from pydantic import ValidationError

from bundlecraft.helpers.config_schema import (
    validate_defaults_config,
    validate_env_config,
    validate_source_config,
)


class TestBundleConfigValidation:
    """Test bundle configuration validation."""

    def test_missing_source_name(self):
        """Bundle config must have source_name field."""
        data = {"description": "Test bundle"}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "source_name" in str(exc_info.value).lower()

    def test_missing_description(self):
        """Bundle config must have description field."""
        data = {"source_name": "test"}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "description" in str(exc_info.value).lower()

    def test_empty_source_name(self):
        """Bundle name cannot be empty string."""
        data = {"source_name": "", "description": "Test"}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "source_name" in str(exc_info.value).lower()

    def test_empty_description(self):
        """Description cannot be empty string."""
        data = {"source_name": "test", "description": ""}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "description" in str(exc_info.value).lower()

    def test_no_sources(self):
        """Bundle must have at least one repo or fetch entry."""
        data = {"source_name": "test", "description": "Test bundle"}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "at least one" in str(exc_info.value).lower()

    def test_reserved_source_name(self):
        """Bundle name cannot be a reserved keyword."""
        data = {"source_name": "fetch", "description": "Test", "repo": [{"name": "test"}]}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "reserved" in str(exc_info.value).lower()

    def test_duplicate_repo_names(self):
        """Repo entries must have unique names."""
        data = {
            "source_name": "test",
            "description": "Test",
            "repo": [{"name": "duplicate"}, {"name": "duplicate"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_duplicate_fetch_names(self):
        """Fetch entries must have unique names."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [
                {"name": "duplicate", "type": "url", "url": "https://example.com/ca.pem"},
                {"name": "duplicate", "type": "url", "url": "https://example.com/ca2.pem"},
            ],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_repo_fetch_name_conflict(self):
        """Repo and fetch entries cannot share names."""
        data = {
            "source_name": "test",
            "description": "Test",
            "repo": [{"name": "conflict"}],
            "fetch": [{"name": "conflict", "type": "url", "url": "https://example.com/ca.pem"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "conflict" in str(exc_info.value).lower()

    def test_reserved_repo_name(self):
        """Repo name cannot be a reserved keyword."""
        data = {
            "source_name": "test",
            "description": "Test",
            "repo": [{"name": "include"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "reserved" in str(exc_info.value).lower()

    def test_reserved_fetch_name(self):
        """Fetch name cannot be a reserved keyword."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [{"name": "exclude", "type": "url", "url": "https://example.com/ca.pem"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "reserved" in str(exc_info.value).lower()

    def test_insecure_http_url(self):
        """HTTP URLs (non-localhost) should be rejected."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [{"name": "insecure", "type": "url", "url": "http://example.com/ca.pem"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "https" in str(exc_info.value).lower()

    def test_url_fetch_missing_url(self):
        """URL fetch type requires url field."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [{"name": "test", "type": "url"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "url" in str(exc_info.value).lower() and "required" in str(exc_info.value).lower()

    def test_vault_fetch_missing_mount(self):
        """Vault fetch type requires mount field."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [{"name": "test", "type": "vault", "path": "secret/ca"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "mount" in str(exc_info.value).lower()

    def test_vault_fetch_missing_path(self):
        """Vault fetch type requires path field."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [{"name": "test", "type": "vault", "mount": "pki"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "path" in str(exc_info.value).lower()

    def test_api_fetch_missing_endpoint(self):
        """API fetch type requires endpoint field."""
        data = {
            "source_name": "test",
            "description": "Test",
            "fetch": [{"name": "test", "type": "api"}],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_source_config(data)
        assert "endpoint" in str(exc_info.value).lower()


class TestCraftConfigValidation:
    """Test env configuration validation."""

    def test_missing_name(self):
        """Environment config must have name field."""
        data = {
            "description": "Test environment",
            "bundles": {"internal": {"include_sources": ["test"]}},
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "name" in str(exc_info.value).lower()

    def test_missing_description(self):
        """Environment config must have description field."""
        data = {"name": "Test", "bundles": {"internal": {"include_sources": ["test"]}}}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "description" in str(exc_info.value).lower()

    def test_empty_targets(self):
        """Environment must have at least one bundle."""
        data = {"name": "Test", "description": "Test environment", "bundles": {}}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert (
            "at least one" in str(exc_info.value).lower()
            or "bundles" in str(exc_info.value).lower()
        )

    def test_invalid_output_format(self):
        """Output formats must be valid format names."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "output_formats": ["pem", "invalid_format"],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "invalid" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()

    def test_bundles_must_be_dict(self):
        """Bundles field must be a dictionary, not a list."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": [
                {"bundle_name": "bundle1", "include_sources": ["test1"]},
                {"bundle_name": "bundle2", "include_sources": ["test2"]},
            ],
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "dict" in str(exc_info.value).lower()

    def test_target_missing_includes(self):
        """Bundle must have include_sources field."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {}},
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "include_sources" in str(exc_info.value).lower()

    def test_build_path_parent_traversal(self):
        """build_path cannot contain parent directory references."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "build_path": "team/../escape",
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert ".." in str(exc_info.value)

    def test_build_path_absolute_path(self):
        """build_path cannot be an absolute path."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "build_path": "/absolute/path",
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "relative" in str(exc_info.value)

    def test_build_path_dist_prefix(self):
        """build_path should not include dist/ prefix."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "build_path": "dist/my/custom/path",
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "dist/" in str(exc_info.value) and "prefix" in str(exc_info.value)

    def test_build_path_invalid_characters(self):
        """build_path components can only contain safe characters."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "build_path": "invalid@chars/bad$name",
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "alphanumeric" in str(exc_info.value) or "characters" in str(exc_info.value)

    def test_build_path_empty_components(self):
        """build_path cannot have empty path components."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "build_path": "valid//empty",
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_env_config(data)
        assert "empty" in str(exc_info.value) and "component" in str(exc_info.value)

    def test_build_path_valid(self):
        """Valid build_path should pass validation."""
        data = {
            "name": "Test",
            "description": "Test",
            "bundles": {"internal": {"include_sources": ["test"]}},
            "build_path": "team-a/v2/staging",
        }
        # Should not raise an exception
        config = validate_env_config(data)
        assert config.build_path == "team-a/v2/staging"


class TestDefaultsConfigValidation:
    """Test defaults configuration validation."""

    def test_invalid_output_format(self):
        """Output formats must be valid format names."""
        data = {"output_formats": ["pem", "xyz"]}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_defaults_config(data)
        assert "xyz" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    def test_rsa_key_size_too_small(self):
        """RSA key size must be at least 1024 bits."""
        data = {"filters": {"minimum_key_size_rsa": 512}}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_defaults_config(data)
        assert "1024" in str(exc_info.value) or "rsa" in str(exc_info.value).lower()

    def test_ecc_key_size_too_small(self):
        """ECC key size must be at least 192 bits."""
        data = {"filters": {"minimum_key_size_ecc": 128}}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_defaults_config(data)
        assert "192" in str(exc_info.value) or "ecc" in str(exc_info.value).lower()

    def test_negative_warn_days(self):
        """Warn days cannot be negative."""
        data = {"verify": {"warn_days_before_expiry": -1}}
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            validate_defaults_config(data)
        # Pydantic v2 validation error for numeric constraints
        assert (
            "greater than or equal" in str(exc_info.value).lower()
            or "warn" in str(exc_info.value).lower()
        )


class TestValidConfigsPass:
    """Test that valid configurations pass validation."""

    def test_valid_bundle_with_repo(self):
        """Valid bundle config with repo should pass."""
        data = {
            "source_name": "test",
            "description": "Test bundle",
            "repo": [{"name": "internal", "include": ["cert_sources/internal/rootCA.pem"]}],
        }
        config = validate_source_config(data)
        assert config.source_name == "test"

    def test_valid_bundle_with_fetch(self):
        """Valid bundle config with fetch should pass."""
        data = {
            "source_name": "mozilla",
            "description": "Mozilla roots",
            "fetch": [{"name": "mozilla", "type": "url", "url": "https://curl.se/ca/cacert.pem"}],
        }
        config = validate_source_config(data)
        assert config.source_name == "mozilla"

    def test_valid_craft_config(self):
        """Valid environment config should pass."""
        data = {
            "name": "Development",
            "description": "Dev environment",
            "bundles": {"internal": {"include_sources": ["internal"]}},
            "output_formats": ["pem", "jks"],
        }
        config = validate_env_config(data)
        assert config.name == "Development"

    def test_valid_defaults_config(self):
        """Valid defaults config should pass."""
        data = {
            "output_formats": ["pem", "p7b", "jks", "p12"],
            "verify": {"fail_on_expired": True, "warn_days_before_expiry": 30},
            "filters": {"minimum_key_size_rsa": 2048, "minimum_key_size_ecc": 256},
        }
        config = validate_defaults_config(data)
        assert "pem" in config.output_formats
