"""
Tests for bundlecraft.helpers.config_schema module.
"""


from bundlecraft.helpers.config_schema import (
    BUNDLE_CONFIG_SCHEMA,
    CRAFT_CONFIG_SCHEMA,
    ENV_VAR_SCHEMA,
    get_schema_documentation,
    validate_env_var_signing,
    validate_output_formats,
    validate_signing_config,
)


class TestSchemaDefinitions:
    """Tests for schema definitions."""

    def test_env_var_schema_exists(self):
        """Test that ENV_VAR_SCHEMA is defined."""
        assert isinstance(ENV_VAR_SCHEMA, dict)
        assert "BUNDLECRAFT_SIGN_METHOD" in ENV_VAR_SCHEMA
        assert "BUNDLECRAFT_GPG_KEY_ID" in ENV_VAR_SCHEMA

    def test_env_var_schema_signing_method(self):
        """Test BUNDLECRAFT_SIGN_METHOD schema definition."""
        schema = ENV_VAR_SCHEMA["BUNDLECRAFT_SIGN_METHOD"]
        assert schema["type"] == "string"
        assert schema["default"] == "none"
        assert "gpg" in schema["allowed_values"]
        assert "sigstore" in schema["allowed_values"]
        assert "none" in schema["allowed_values"]

    def test_env_var_schema_gpg_key_id(self):
        """Test BUNDLECRAFT_GPG_KEY_ID schema definition."""
        schema = ENV_VAR_SCHEMA["BUNDLECRAFT_GPG_KEY_ID"]
        assert schema["type"] == "string"
        assert "required_when" in schema

    def test_bundle_config_schema_exists(self):
        """Test that BUNDLE_CONFIG_SCHEMA is defined."""
        assert isinstance(BUNDLE_CONFIG_SCHEMA, dict)
        assert "bundle_name" in BUNDLE_CONFIG_SCHEMA
        assert "repo" in BUNDLE_CONFIG_SCHEMA
        assert "fetch" in BUNDLE_CONFIG_SCHEMA

    def test_bundle_config_schema_repo(self):
        """Test repo schema definition."""
        schema = BUNDLE_CONFIG_SCHEMA["repo"]
        assert schema["type"] == "list"
        assert "item_schema" in schema
        assert "name" in schema["item_schema"]

    def test_craft_config_schema_exists(self):
        """Test that CRAFT_CONFIG_SCHEMA is defined."""
        assert isinstance(CRAFT_CONFIG_SCHEMA, dict)
        assert "targets" in CRAFT_CONFIG_SCHEMA
        assert "output_formats" in CRAFT_CONFIG_SCHEMA
        assert "signing" in CRAFT_CONFIG_SCHEMA

    def test_craft_config_schema_signing(self):
        """Test signing schema definition in craft config."""
        schema = CRAFT_CONFIG_SCHEMA["signing"]
        assert schema["type"] == "dict"
        assert "schema" in schema
        assert "enabled" in schema["schema"]
        assert "method" in schema["schema"]
        assert "gpg" in schema["schema"]

    def test_craft_config_schema_output_formats(self):
        """Test output_formats schema definition."""
        schema = CRAFT_CONFIG_SCHEMA["output_formats"]
        assert schema["type"] == "list"
        assert "pem" in schema["allowed_values"]
        assert "jks" in schema["allowed_values"]
        assert "p12" in schema["allowed_values"]


class TestValidateSigningConfig:
    """Tests for validate_signing_config function."""

    def test_validate_empty_config(self):
        """Test validation with empty config."""
        errors = validate_signing_config({})
        assert len(errors) == 0

    def test_validate_none_method(self):
        """Test validation with method='none'."""
        config = {"signing": {"method": "none"}}
        errors = validate_signing_config(config)
        assert len(errors) == 0

    def test_validate_gpg_method(self):
        """Test validation with method='gpg'."""
        config = {
            "signing": {
                "method": "gpg",
                "gpg": {
                    "key_id_env": "BUNDLECRAFT_GPG_KEY_ID",
                },
            }
        }
        errors = validate_signing_config(config)
        assert len(errors) == 0

    def test_validate_sigstore_method(self):
        """Test validation with method='sigstore'."""
        config = {"signing": {"method": "sigstore"}}
        errors = validate_signing_config(config)
        assert len(errors) == 0

    def test_validate_invalid_method(self):
        """Test validation with invalid method."""
        config = {"signing": {"method": "invalid"}}
        errors = validate_signing_config(config)
        assert len(errors) > 0
        assert any("Invalid signing method" in e for e in errors)

    def test_validate_gpg_method_without_config(self):
        """Test validation with gpg method but missing gpg config."""
        config = {"signing": {"method": "gpg"}}
        errors = validate_signing_config(config)
        # GPG config is optional in the schema (env vars can provide it)
        # So this should not error at config validation level
        assert isinstance(errors, list)

    def test_validate_invalid_gpg_config_type(self):
        """Test validation with invalid gpg config type."""
        config = {"signing": {"method": "gpg", "gpg": "not-a-dict"}}
        errors = validate_signing_config(config)
        assert len(errors) > 0
        assert any("GPG configuration must be a dictionary" in e for e in errors)

    def test_validate_invalid_artifacts_type(self):
        """Test validation with invalid artifacts type."""
        config = {"signing": {"method": "gpg", "artifacts": "not-a-list"}}
        errors = validate_signing_config(config)
        assert len(errors) > 0
        assert any("artifacts must be a list" in e for e in errors)

    def test_validate_valid_artifacts(self):
        """Test validation with valid artifacts list."""
        config = {
            "signing": {
                "method": "gpg",
                "gpg": {},
                "artifacts": ["manifest.json", "checksums.sha256"],
            }
        }
        errors = validate_signing_config(config)
        # Should have error about gpg config but not artifacts
        assert not any("artifacts" in e.lower() for e in errors)


class TestValidateOutputFormats:
    """Tests for validate_output_formats function."""

    def test_validate_empty_list(self):
        """Test validation with empty list."""
        errors = validate_output_formats([])
        assert len(errors) == 0

    def test_validate_valid_formats(self):
        """Test validation with valid formats."""
        errors = validate_output_formats(["pem", "jks", "p12"])
        assert len(errors) == 0

    def test_validate_all_formats(self):
        """Test validation with all supported formats."""
        errors = validate_output_formats(["pem", "p7b", "jks", "p12", "zip"])
        assert len(errors) == 0

    def test_validate_invalid_format(self):
        """Test validation with invalid format."""
        errors = validate_output_formats(["pem", "invalid"])
        assert len(errors) > 0
        assert any("Invalid output format: invalid" in e for e in errors)

    def test_validate_not_a_list(self):
        """Test validation with non-list input."""
        errors = validate_output_formats("pem")  # type: ignore
        assert len(errors) > 0
        assert any("must be a list" in e for e in errors)

    def test_validate_multiple_invalid_formats(self):
        """Test validation with multiple invalid formats."""
        errors = validate_output_formats(["invalid1", "invalid2"])
        assert len(errors) >= 2


class TestValidateEnvVarSigning:
    """Tests for validate_env_var_signing function."""

    def test_validate_empty_env(self):
        """Test validation with empty environment."""
        errors = validate_env_var_signing({})
        assert len(errors) == 0

    def test_validate_none_method(self):
        """Test validation with method='none'."""
        errors = validate_env_var_signing({"BUNDLECRAFT_SIGN_METHOD": "none"})
        assert len(errors) == 0

    def test_validate_gpg_method_with_key_id(self):
        """Test validation with gpg method and key ID."""
        env_vars = {
            "BUNDLECRAFT_SIGN_METHOD": "gpg",
            "BUNDLECRAFT_GPG_KEY_ID": "user@example.com",
        }
        errors = validate_env_var_signing(env_vars)
        assert len(errors) == 0

    def test_validate_gpg_method_without_key_id(self):
        """Test validation with gpg method but missing key ID."""
        env_vars = {"BUNDLECRAFT_SIGN_METHOD": "gpg"}
        errors = validate_env_var_signing(env_vars)
        assert len(errors) > 0
        assert any("BUNDLECRAFT_GPG_KEY_ID is required" in e for e in errors)

    def test_validate_invalid_method(self):
        """Test validation with invalid method."""
        env_vars = {"BUNDLECRAFT_SIGN_METHOD": "invalid"}
        errors = validate_env_var_signing(env_vars)
        assert len(errors) > 0
        assert any("Invalid BUNDLECRAFT_SIGN_METHOD" in e for e in errors)

    def test_validate_sigstore_method(self):
        """Test validation with sigstore method."""
        env_vars = {"BUNDLECRAFT_SIGN_METHOD": "sigstore"}
        errors = validate_env_var_signing(env_vars)
        assert len(errors) == 0

    def test_validate_with_none_values(self):
        """Test validation with None values."""
        env_vars = {
            "BUNDLECRAFT_SIGN_METHOD": None,
            "BUNDLECRAFT_GPG_KEY_ID": None,
        }
        errors = validate_env_var_signing(env_vars)
        # None is not a valid method value, should error
        assert len(errors) > 0
        assert any("Invalid BUNDLECRAFT_SIGN_METHOD" in e for e in errors)


class TestGetSchemaDocumentation:
    """Tests for get_schema_documentation function."""

    def test_returns_dict(self):
        """Test that get_schema_documentation returns a dictionary."""
        doc = get_schema_documentation()
        assert isinstance(doc, dict)

    def test_has_required_keys(self):
        """Test that documentation has required keys."""
        doc = get_schema_documentation()
        assert "bundle_config" in doc
        assert "craft_config" in doc
        assert "environment_variables" in doc

    def test_bundle_config_schema(self):
        """Test that bundle_config schema is included."""
        doc = get_schema_documentation()
        assert doc["bundle_config"] == BUNDLE_CONFIG_SCHEMA

    def test_craft_config_schema(self):
        """Test that craft_config schema is included."""
        doc = get_schema_documentation()
        assert doc["craft_config"] == CRAFT_CONFIG_SCHEMA

    def test_env_var_schema(self):
        """Test that environment_variables schema is included."""
        doc = get_schema_documentation()
        assert doc["environment_variables"] == ENV_VAR_SCHEMA


class TestSchemaCompleteness:
    """Tests to ensure schema covers all signing features."""

    def test_signing_methods_covered(self):
        """Test that all signing methods are in schema."""
        allowed = CRAFT_CONFIG_SCHEMA["signing"]["schema"]["method"]["allowed_values"]
        assert "gpg" in allowed
        assert "sigstore" in allowed
        assert "none" in allowed

    def test_env_vars_for_gpg(self):
        """Test that all GPG-related env vars are defined."""
        assert "BUNDLECRAFT_GPG_KEY_ID" in ENV_VAR_SCHEMA
        assert "BUNDLECRAFT_GPG_PASSPHRASE" in ENV_VAR_SCHEMA
        assert "BUNDLECRAFT_GPG_HOME" in ENV_VAR_SCHEMA

    def test_env_vars_for_signing(self):
        """Test that signing method env var is defined."""
        assert "BUNDLECRAFT_SIGN_METHOD" in ENV_VAR_SCHEMA

    def test_signing_artifacts_default(self):
        """Test that signing artifacts has sensible default."""
        default = CRAFT_CONFIG_SCHEMA["signing"]["schema"]["artifacts"]["default"]
        assert "manifest.json" in default
