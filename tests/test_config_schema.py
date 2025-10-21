"""Tests for BundleCraft configuration schema module."""

from bundlecraft.helpers.config_schema import (
    FETCHER_SCHEMAS,
    FETCHER_TYPE_API,
    FETCHER_TYPE_APPLE_ROOTS,
    FETCHER_TYPE_ARTIFACTORY,
    FETCHER_TYPE_AZURE_BLOB,
    FETCHER_TYPE_AZURE_KEYVAULT,
    FETCHER_TYPE_GCS,
    FETCHER_TYPE_GITHUB_RELEASE,
    FETCHER_TYPE_MICROSOFT_ROOTS,
    FETCHER_TYPE_MOZILLA_ROOTS,
    FETCHER_TYPE_S3,
    FETCHER_TYPE_URL,
    FETCHER_TYPE_VAULT,
    SUPPORTED_FETCHER_TYPES,
    get_all_fetcher_types,
    get_fetcher_categories,
    get_fetcher_schema,
    is_valid_fetcher_type,
)


class TestFetcherTypeConstants:
    """Test fetcher type constants."""

    def test_all_fetcher_types_defined(self):
        """Test that all fetcher types are defined as constants."""
        expected_types = {
            "url",
            "api",
            "vault",
            "s3",
            "azure_blob",
            "gcs",
            "artifactory",
            "github_release",
            "azure_keyvault",
            "mozilla_roots",
            "microsoft_roots",
            "apple_roots",
        }
        assert SUPPORTED_FETCHER_TYPES == expected_types

    def test_fetcher_type_constants_match_strings(self):
        """Test that fetcher type constants match their string values."""
        assert FETCHER_TYPE_URL == "url"
        assert FETCHER_TYPE_API == "api"
        assert FETCHER_TYPE_VAULT == "vault"
        assert FETCHER_TYPE_S3 == "s3"
        assert FETCHER_TYPE_AZURE_BLOB == "azure_blob"
        assert FETCHER_TYPE_GCS == "gcs"
        assert FETCHER_TYPE_ARTIFACTORY == "artifactory"
        assert FETCHER_TYPE_GITHUB_RELEASE == "github_release"
        assert FETCHER_TYPE_AZURE_KEYVAULT == "azure_keyvault"
        assert FETCHER_TYPE_MOZILLA_ROOTS == "mozilla_roots"
        assert FETCHER_TYPE_MICROSOFT_ROOTS == "microsoft_roots"
        assert FETCHER_TYPE_APPLE_ROOTS == "apple_roots"


class TestFetcherSchemas:
    """Test fetcher schema definitions."""

    def test_all_fetcher_types_have_schemas(self):
        """Test that all supported fetcher types have schema definitions."""
        for fetcher_type in SUPPORTED_FETCHER_TYPES:
            assert fetcher_type in FETCHER_SCHEMAS, f"Missing schema for {fetcher_type}"

    def test_schema_required_fields(self):
        """Test that schemas have required structure."""
        for fetcher_type, schema in FETCHER_SCHEMAS.items():
            assert "description" in schema, f"{fetcher_type} missing description"
            assert "required_fields" in schema, f"{fetcher_type} missing required_fields"
            assert "optional_fields" in schema, f"{fetcher_type} missing optional_fields"
            assert "example" in schema, f"{fetcher_type} missing example"
            assert isinstance(schema["required_fields"], list)
            assert isinstance(schema["optional_fields"], list)
            assert isinstance(schema["example"], dict)

    def test_s3_schema(self):
        """Test S3 fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_S3]
        assert schema["description"] == "Fetch from AWS S3 or S3-compatible storage"
        assert "bucket" in schema["required_fields"]
        assert "key" in schema["required_fields"]
        assert "region" in schema["optional_fields"]
        assert "endpoint_url" in schema["optional_fields"]
        assert "dependencies" in schema
        assert "boto3" in schema["dependencies"]

    def test_azure_blob_schema(self):
        """Test Azure Blob fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_AZURE_BLOB]
        assert "Azure Blob" in schema["description"]
        assert "container" in schema["required_fields"]
        assert "blob_name" in schema["required_fields"]
        assert "account_name" in schema["optional_fields"]
        assert "dependencies" in schema

    def test_gcs_schema(self):
        """Test GCS fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_GCS]
        assert "Google Cloud Storage" in schema["description"]
        assert "bucket" in schema["required_fields"]
        assert "blob_name" in schema["required_fields"]
        assert "project" in schema["optional_fields"]

    def test_artifactory_schema(self):
        """Test Artifactory fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_ARTIFACTORY]
        assert "Artifactory" in schema["description"]
        assert "url" in schema["required_fields"]
        assert "repository" in schema["optional_fields"]
        assert "path" in schema["optional_fields"]
        assert "token_ref" in schema["optional_fields"]

    def test_github_release_schema(self):
        """Test GitHub Release fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_GITHUB_RELEASE]
        assert "GitHub Releases" in schema["description"]
        assert "owner" in schema["required_fields"]
        assert "repo" in schema["required_fields"]
        assert "asset_name" in schema["required_fields"]
        assert "tag" in schema["optional_fields"]

    def test_azure_keyvault_schema(self):
        """Test Azure Key Vault fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_AZURE_KEYVAULT]
        assert "Azure Key Vault" in schema["description"]
        assert "vault_url" in schema["required_fields"]
        assert "certificate_name" in schema["required_fields"]
        assert "version" in schema["optional_fields"]

    def test_mozilla_roots_schema(self):
        """Test Mozilla roots fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_MOZILLA_ROOTS]
        assert "Mozilla" in schema["description"]
        assert len(schema["required_fields"]) == 0  # No required fields
        assert "url" in schema["optional_fields"]
        assert "default_url" in schema
        assert "curl.se" in schema["default_url"]

    def test_microsoft_roots_schema(self):
        """Test Microsoft roots fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_MICROSOFT_ROOTS]
        assert "Microsoft" in schema["description"]
        assert len(schema["required_fields"]) == 0
        assert "default_url" in schema
        assert "ccadb" in schema["default_url"].lower()

    def test_apple_roots_schema(self):
        """Test Apple roots fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_APPLE_ROOTS]
        assert "Apple" in schema["description"]
        assert len(schema["required_fields"]) == 0
        assert "default_url" in schema
        assert "ccadb" in schema["default_url"].lower()

    def test_vault_schema(self):
        """Test Vault fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_VAULT]
        assert "Vault" in schema["description"]
        assert "path" in schema["required_fields"]
        assert "mount_point" in schema["optional_fields"]
        assert "namespace" in schema["optional_fields"]

    def test_url_schema(self):
        """Test URL fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_URL]
        assert "url" in schema["required_fields"]
        assert "verify" in schema["optional_fields"]

    def test_api_schema(self):
        """Test API fetcher schema."""
        schema = FETCHER_SCHEMAS[FETCHER_TYPE_API]
        assert "API" in schema["description"]
        assert "endpoint" in schema["required_fields"]
        assert "token_ref" in schema["optional_fields"]


class TestSchemaExamples:
    """Test that schema examples are valid."""

    def test_all_schemas_have_valid_examples(self):
        """Test that all schema examples have required fields."""
        for fetcher_type, schema in FETCHER_SCHEMAS.items():
            example = schema["example"]
            assert "type" in example, f"{fetcher_type} example missing 'type'"
            assert example["type"] == fetcher_type, f"{fetcher_type} example has wrong type"
            assert "name" in example, f"{fetcher_type} example missing 'name'"

    def test_cloud_fetchers_have_install_instructions(self):
        """Test that cloud fetchers include installation instructions."""
        cloud_fetchers = [
            FETCHER_TYPE_S3,
            FETCHER_TYPE_AZURE_BLOB,
            FETCHER_TYPE_GCS,
            FETCHER_TYPE_AZURE_KEYVAULT,
        ]
        for fetcher_type in cloud_fetchers:
            schema = FETCHER_SCHEMAS[fetcher_type]
            assert "install" in schema, f"{fetcher_type} missing install instructions"
            assert "bundlecraft[cloud]" in schema["install"]


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_fetcher_schema_valid_type(self):
        """Test get_fetcher_schema with valid type."""
        schema = get_fetcher_schema("s3")
        assert schema is not None
        assert schema["description"] == "Fetch from AWS S3 or S3-compatible storage"

    def test_get_fetcher_schema_invalid_type(self):
        """Test get_fetcher_schema with invalid type."""
        schema = get_fetcher_schema("invalid_type")
        assert schema is None

    def test_is_valid_fetcher_type_valid(self):
        """Test is_valid_fetcher_type with valid types."""
        assert is_valid_fetcher_type("s3") is True
        assert is_valid_fetcher_type("azure_blob") is True
        assert is_valid_fetcher_type("mozilla_roots") is True
        assert is_valid_fetcher_type("url") is True

    def test_is_valid_fetcher_type_invalid(self):
        """Test is_valid_fetcher_type with invalid types."""
        assert is_valid_fetcher_type("invalid") is False
        assert is_valid_fetcher_type("") is False
        assert is_valid_fetcher_type("S3") is False  # Case sensitive

    def test_get_all_fetcher_types(self):
        """Test get_all_fetcher_types returns all types."""
        all_types = get_all_fetcher_types()
        assert isinstance(all_types, set)
        assert len(all_types) == 12  # Total number of supported fetchers
        assert "s3" in all_types
        assert "mozilla_roots" in all_types

    def test_get_all_fetcher_types_returns_copy(self):
        """Test that get_all_fetcher_types returns a copy."""
        types1 = get_all_fetcher_types()
        types2 = get_all_fetcher_types()
        assert types1 == types2
        assert types1 is not types2  # Different objects

    def test_get_fetcher_categories(self):
        """Test get_fetcher_categories returns correct structure."""
        categories = get_fetcher_categories()
        assert isinstance(categories, dict)
        assert "Cloud Storage" in categories
        assert "Artifact Repositories" in categories
        assert "Key Management" in categories
        assert "Public Root Programs" in categories
        assert "Generic Sources" in categories

    def test_get_fetcher_categories_cloud_storage(self):
        """Test Cloud Storage category contains correct fetchers."""
        categories = get_fetcher_categories()
        cloud_storage = categories["Cloud Storage"]
        assert FETCHER_TYPE_S3 in cloud_storage
        assert FETCHER_TYPE_AZURE_BLOB in cloud_storage
        assert FETCHER_TYPE_GCS in cloud_storage
        assert len(cloud_storage) == 3

    def test_get_fetcher_categories_artifact_repos(self):
        """Test Artifact Repositories category."""
        categories = get_fetcher_categories()
        artifact_repos = categories["Artifact Repositories"]
        assert FETCHER_TYPE_ARTIFACTORY in artifact_repos
        assert FETCHER_TYPE_GITHUB_RELEASE in artifact_repos
        assert len(artifact_repos) == 2

    def test_get_fetcher_categories_key_management(self):
        """Test Key Management category."""
        categories = get_fetcher_categories()
        key_mgmt = categories["Key Management"]
        assert FETCHER_TYPE_AZURE_KEYVAULT in key_mgmt
        assert FETCHER_TYPE_VAULT in key_mgmt
        assert len(key_mgmt) == 2

    def test_get_fetcher_categories_root_programs(self):
        """Test Public Root Programs category."""
        categories = get_fetcher_categories()
        root_programs = categories["Public Root Programs"]
        assert FETCHER_TYPE_MOZILLA_ROOTS in root_programs
        assert FETCHER_TYPE_MICROSOFT_ROOTS in root_programs
        assert FETCHER_TYPE_APPLE_ROOTS in root_programs
        assert len(root_programs) == 3

    def test_get_fetcher_categories_generic(self):
        """Test Generic Sources category."""
        categories = get_fetcher_categories()
        generic = categories["Generic Sources"]
        assert FETCHER_TYPE_URL in generic
        assert FETCHER_TYPE_API in generic
        assert len(generic) == 2


class TestTypeDefinitions:
    """Test TypedDict definitions."""

    def test_verify_config_structure(self):
        """Test that VerifyConfig can be imported and used."""
        from bundlecraft.helpers.config_schema import VerifyConfig

        # TypedDict doesn't enforce runtime validation, but we can verify it exists
        assert VerifyConfig is not None

    def test_base_fetcher_config_structure(self):
        """Test that BaseFetcherConfig exists."""
        from bundlecraft.helpers.config_schema import BaseFetcherConfig

        assert BaseFetcherConfig is not None

    def test_all_fetcher_config_types_defined(self):
        """Test that all fetcher-specific config types are defined."""
        from bundlecraft.helpers.config_schema import (
            APIFetcherConfig,
            ArtifactoryFetcherConfig,
            AzureBlobFetcherConfig,
            AzureKeyVaultFetcherConfig,
            GCSFetcherConfig,
            GitHubReleaseFetcherConfig,
            RootProgramFetcherConfig,
            S3FetcherConfig,
            URLFetcherConfig,
            VaultFetcherConfig,
        )

        # Verify all config types exist
        assert URLFetcherConfig is not None
        assert APIFetcherConfig is not None
        assert VaultFetcherConfig is not None
        assert S3FetcherConfig is not None
        assert AzureBlobFetcherConfig is not None
        assert GCSFetcherConfig is not None
        assert ArtifactoryFetcherConfig is not None
        assert GitHubReleaseFetcherConfig is not None
        assert AzureKeyVaultFetcherConfig is not None
        assert RootProgramFetcherConfig is not None
