#!/usr/bin/env python3
"""
Tests for config schema validation.

These tests verify that invalid YAML configurations are properly rejected
with clear error messages.
"""


import pytest
from click.testing import CliRunner

from bundlecraft.config_schema import (
    validate_bundle_config,
    validate_craft_config,
    validate_defaults_config,
)
from bundlecraft.helpers.utils import load_yaml


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestBundleConfigValidation:
    """Test bundle config schema validation."""

    def test_valid_bundle_config(self):
        """Valid bundle config should pass validation."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "include": ["sources/test.pem"],
        }
        result = validate_bundle_config(config)
        assert result.bundle_name == "test"
        assert result.description == "Test bundle"

    def test_bundle_missing_name_fails(self):
        """Bundle config without bundle_name should fail."""
        config = {
            "description": "Test bundle",
            "include": ["sources/test.pem"],
        }
        with pytest.raises(ValueError, match="bundle_name"):
            validate_bundle_config(config)

    def test_bundle_missing_description_fails(self):
        """Bundle config without description should fail."""
        config = {
            "bundle_name": "test",
            "include": ["sources/test.pem"],
        }
        with pytest.raises(ValueError, match="description"):
            validate_bundle_config(config)

    def test_bundle_empty_name_fails(self):
        """Bundle config with empty name should fail."""
        config = {
            "bundle_name": "",
            "description": "Test bundle",
        }
        with pytest.raises(ValueError):
            validate_bundle_config(config)

    def test_bundle_empty_description_fails(self):
        """Bundle config with empty description should fail."""
        config = {
            "bundle_name": "test",
            "description": "",
        }
        with pytest.raises(ValueError):
            validate_bundle_config(config)

    def test_bundle_duplicate_repo_names_fails(self):
        """Bundle config with duplicate repo names should fail."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "repo": [
                {"name": "roots", "include": ["sources/test1.pem"]},
                {"name": "roots", "include": ["sources/test2.pem"]},
            ],
        }
        with pytest.raises(ValueError, match="Duplicate repository names"):
            validate_bundle_config(config)

    def test_bundle_duplicate_fetch_names_fails(self):
        """Bundle config with duplicate fetch names should fail."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "fetch": [
                {"name": "remote1", "type": "url", "url": "https://example.com/1.pem"},
                {"name": "remote1", "type": "url", "url": "https://example.com/2.pem"},
            ],
        }
        with pytest.raises(ValueError, match="Duplicate fetch names"):
            validate_bundle_config(config)

    def test_bundle_repo_fetch_name_conflict_fails(self):
        """Bundle config with repo/fetch name conflict should fail."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "repo": [{"name": "conflict", "include": ["sources/test.pem"]}],
            "fetch": [{"name": "conflict", "type": "url", "url": "https://example.com/test.pem"}],
        }
        with pytest.raises(ValueError, match="Name conflict"):
            validate_bundle_config(config)

    def test_bundle_reserved_repo_name_fails(self):
        """Bundle config with reserved repo name should fail."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "repo": [{"name": "include", "include": ["sources/test.pem"]}],
        }
        with pytest.raises(ValueError, match="reserved"):
            validate_bundle_config(config)

    def test_bundle_reserved_fetch_name_fails(self):
        """Bundle config with reserved fetch name should fail."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "fetch": [{"name": "fetch", "type": "url", "url": "https://example.com/test.pem"}],
        }
        with pytest.raises(ValueError, match="reserved"):
            validate_bundle_config(config)

    def test_bundle_fetch_url_type_requires_url(self):
        """Bundle config with url fetch type must have url field."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "fetch": [{"name": "remote", "type": "url"}],
        }
        with pytest.raises(ValueError, match="url.*requires.*url"):
            validate_bundle_config(config)

    def test_bundle_fetch_vault_type_requires_fields(self):
        """Bundle config with vault fetch type must have required fields."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "fetch": [{"name": "vault", "type": "vault"}],
        }
        with pytest.raises(ValueError, match="vault.*requires"):
            validate_bundle_config(config)

    def test_bundle_inline_pem_without_path(self):
        """Bundle config with inline PEM entry should work."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle with inline PEM",
            "repo": [
                {
                    "name": "inline-test",
                    "include": [
                        {
                            "inline": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
                            "name": "test.pem",
                        }
                    ],
                }
            ],
        }
        result = validate_bundle_config(config)
        assert result.repo[0].name == "inline-test"

    def test_bundle_inline_pem_with_both_path_and_inline_fails(self):
        """Bundle config with both path and inline should fail."""
        config = {
            "bundle_name": "test",
            "description": "Test bundle",
            "repo": [
                {
                    "name": "bad",
                    "include": [{"path": "sources/test.pem", "inline": "PEM content"}],
                }
            ],
        }
        with pytest.raises(ValueError, match="cannot have both"):
            validate_bundle_config(config)


class TestCraftConfigValidation:
    """Test craft config schema validation."""

    def test_valid_craft_config(self):
        """Valid craft config should pass validation."""
        config = {
            "name": "test-craft",
            "description": "Test craft",
            "targets": {"test-target": {"includes": ["bundle1"]}},
            "output_formats": ["pem", "p7b"],
        }
        result = validate_craft_config(config)
        assert result.name == "test-craft"

    def test_craft_invalid_output_format_fails(self):
        """Craft config with invalid output format should fail."""
        config = {
            "name": "test-craft",
            "output_formats": ["pem", "invalid_format"],
        }
        with pytest.raises(ValueError, match="Invalid output format"):
            validate_craft_config(config)

    def test_craft_valid_output_formats(self):
        """Craft config with all valid output formats should pass."""
        config = {
            "name": "test-craft",
            "output_formats": ["pem", "p7b", "jks", "p12", "pkcs12"],
        }
        result = validate_craft_config(config)
        assert len(result.output_formats) == 5

    def test_craft_verify_config_negative_warn_days_fails(self):
        """Craft config with negative warn_days_before_expiry should fail."""
        config = {
            "name": "test-craft",
            "verify": {"fail_on_expired": True, "warn_days_before_expiry": -1},
        }
        with pytest.raises(ValueError):
            validate_craft_config(config)

    def test_craft_filters_minimum_key_size_rsa_too_small_fails(self):
        """Craft config with RSA key size < 1024 should fail."""
        config = {
            "name": "test-craft",
            "filters": {"minimum_key_size_rsa": 512},
        }
        with pytest.raises(ValueError):
            validate_craft_config(config)

    def test_craft_filters_minimum_key_size_ecc_too_small_fails(self):
        """Craft config with ECC key size < 160 should fail."""
        config = {
            "name": "test-craft",
            "filters": {"minimum_key_size_ecc": 128},
        }
        with pytest.raises(ValueError):
            validate_craft_config(config)

    def test_craft_targets_list_format(self):
        """Craft config with targets as list should be normalized to dict."""
        config = {
            "name": "test-craft",
            "targets": [
                {"target_name": "target1", "includes": ["bundle1"]},
                {"name": "target2", "include_bundles": ["bundle2"]},
            ],
        }
        result = validate_craft_config(config)
        assert isinstance(result.targets, dict)
        assert "target1" in result.targets
        assert "target2" in result.targets


class TestDefaultsConfigValidation:
    """Test defaults config schema validation."""

    def test_valid_defaults_config(self):
        """Valid defaults config should pass validation."""
        config = {
            "output_formats": ["pem", "p7b", "jks", "p12"],
            "verify": {"fail_on_expired": True, "warn_days_before_expiry": 30},
            "package": False,
        }
        result = validate_defaults_config(config)
        assert len(result.output_formats) == 4

    def test_defaults_invalid_output_format_fails(self):
        """Defaults config with invalid output format should fail."""
        config = {
            "output_formats": ["pem", "bad_format"],
        }
        with pytest.raises(ValueError, match="Invalid output format"):
            validate_defaults_config(config)

    def test_defaults_empty_config_uses_defaults(self):
        """Empty defaults config should use model defaults."""
        config = {}
        result = validate_defaults_config(config)
        assert result.output_formats  # Should have default formats
        assert result.package is False  # Default value


class TestConfigValidationIntegration:
    """Integration tests for config validation with actual files."""

    def test_load_yaml_with_bundle_validation(self, temp_workspace):
        """Test load_yaml with bundle validation."""
        config_file = temp_workspace / "test-bundle.yaml"
        config_file.write_text(
            """
bundle_name: test
description: Test bundle
include:
  - sources/test.pem
""",
            encoding="utf-8",
        )
        result = load_yaml(config_file, validate="bundle")
        assert result["bundle_name"] == "test"

    def test_load_yaml_bundle_validation_missing_field_fails(self, temp_workspace):
        """Test load_yaml with invalid bundle config."""
        config_file = temp_workspace / "bad-bundle.yaml"
        config_file.write_text(
            """
# Missing required fields
include:
  - sources/test.pem
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="validation failed"):
            load_yaml(config_file, validate="bundle")

    def test_load_yaml_with_craft_validation(self, temp_workspace):
        """Test load_yaml with craft validation."""
        config_file = temp_workspace / "test-craft.yaml"
        config_file.write_text(
            """
name: test-craft
description: Test craft
targets:
  test: {includes: [bundle1]}
output_formats: [pem]
""",
            encoding="utf-8",
        )
        result = load_yaml(config_file, validate="craft")
        assert result["name"] == "test-craft"

    def test_load_yaml_craft_validation_invalid_format_fails(self, temp_workspace):
        """Test load_yaml with invalid craft config."""
        config_file = temp_workspace / "bad-craft.yaml"
        config_file.write_text(
            """
name: test-craft
output_formats: [pem, invalid_format]
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Invalid output format"):
            load_yaml(config_file, validate="craft")

    def test_load_yaml_with_defaults_validation(self, temp_workspace):
        """Test load_yaml with defaults validation."""
        config_file = temp_workspace / "defaults.yaml"
        config_file.write_text(
            """
output_formats: [pem, p7b]
package: false
""",
            encoding="utf-8",
        )
        result = load_yaml(config_file, validate="defaults")
        assert result["output_formats"] == ["pem", "p7b"]

    def test_fetch_command_with_invalid_bundle_fails(self, cli_runner, temp_workspace):
        """Test that fetch command rejects invalid bundle configs."""
        from bundlecraft.fetch import main as fetch_main

        config_file = temp_workspace / "invalid-bundle.yaml"
        config_file.write_text(
            """
# Missing bundle_name and description
fetch:
  - name: test
    type: url
    url: https://example.com/test.pem
""",
            encoding="utf-8",
        )
        result = cli_runner.invoke(
            fetch_main,
            [
                "--bundle-config-file",
                str(config_file),
                "--workspace-root",
                str(temp_workspace),
            ],
        )
        assert result.exit_code != 0
        assert "validation failed" in result.output.lower()

    def test_build_command_with_invalid_craft_fails(self, cli_runner, temp_workspace, monkeypatch):
        """Test that build command rejects invalid craft configs."""
        import bundlecraft.builder as builder_mod
        from bundlecraft.builder import main as build_main

        # Setup directories
        crafts_dir = temp_workspace / "config" / "crafts"
        bundles_dir = temp_workspace / "config" / "bundles"
        crafts_dir.mkdir(parents=True, exist_ok=True)
        bundles_dir.mkdir(parents=True, exist_ok=True)

        # Create invalid craft config
        (crafts_dir / "invalid.yaml").write_text(
            """
name: invalid-craft
output_formats: [pem, bad_format]
targets:
  test: {includes: [test-bundle]}
""",
            encoding="utf-8",
        )

        # Create valid bundle config
        (bundles_dir / "test-bundle.yaml").write_text(
            """
bundle_name: test-bundle
description: Test bundle
include: []
""",
            encoding="utf-8",
        )

        # Monkeypatch paths
        monkeypatch.setattr(builder_mod, "ROOT", temp_workspace)
        monkeypatch.setattr(builder_mod, "CONFIG_DIR", temp_workspace / "config")
        monkeypatch.setattr(builder_mod, "SOURCES_DIR", temp_workspace / "sources")
        monkeypatch.setattr(builder_mod, "STAGED_DIR", temp_workspace / "sources" / "staged")
        monkeypatch.setattr(builder_mod, "DIST_DIR", temp_workspace / "dist")

        result = cli_runner.invoke(build_main, ["--craft", "invalid"])
        assert result.exit_code != 0
        assert "Invalid output format" in result.output or "validation" in result.output.lower()
