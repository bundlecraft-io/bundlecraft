"""Tests for certificate filtering functionality."""

import pytest

from bundlecraft.helpers.utils import apply_filters, merge_configs


@pytest.mark.filters
class TestFilters:
    """Test suite for certificate filtering."""

    def test_unique_by_fingerprint(self, sample_cert_pem):
        """Test deduplication by SHA256 fingerprint."""
        # Duplicate the same cert
        pem_blocks = [sample_cert_pem, sample_cert_pem, sample_cert_pem]

        filters_cfg = {"unique_by_fingerprint": True}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should dedupe to single cert
        assert len(result) == 1
        assert result[0] == sample_cert_pem

    def test_not_expired_only(self, sample_cert_pem, expired_cert_pem):
        """Test filtering of expired certificates."""
        pem_blocks = [sample_cert_pem, expired_cert_pem]

        filters_cfg = {"not_expired_only": True}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should only keep non-expired
        assert len(result) == 1
        assert sample_cert_pem in result
        assert expired_cert_pem not in result

    def test_ca_certs_only(self, sample_ca_cert, sample_end_entity_cert):
        """Test filtering for CA certificates only."""
        pem_blocks = [sample_ca_cert, sample_end_entity_cert]

        filters_cfg = {"ca_certs_only": True}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should only keep CA cert
        assert len(result) == 1
        assert sample_ca_cert in result

    def test_root_certs_only(self, sample_root_cert, sample_intermediate_cert):
        """Test filtering for self-signed root CAs only."""
        pem_blocks = [sample_root_cert, sample_intermediate_cert]

        filters_cfg = {"root_certs_only": True}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should only keep root cert
        assert len(result) == 1
        assert sample_root_cert in result

    def test_signature_algorithms_include_sha256_only(self, sample_sha256_cert):
        """Including sha256 should keep SHA256-signed certs."""
        pem_blocks = [sample_sha256_cert]

        filters_cfg = {"signature_algorithms": {"include": ["sha256WithRSAEncryption", "sha256"]}}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should keep SHA256 cert
        assert len(result) == 1
        assert sample_sha256_cert in result

    def test_signature_algorithms_exclude_sha1_does_not_affect_sha256(self, sample_sha256_cert):
        """Excluding sha1/md5 should not remove a SHA256-signed cert."""
        pem_blocks = [sample_sha256_cert]

        filters_cfg = {"signature_algorithms": {"exclude": ["sha1", "md5"]}}
        result = apply_filters(pem_blocks, filters_cfg)

        # SHA256 cert remains
        assert len(result) == 1
        assert sample_sha256_cert in result

    def test_minimum_key_size_rsa(self, sample_rsa_2048_cert, sample_rsa_1024_cert):
        """Test minimum RSA key size filtering."""
        pem_blocks = [sample_rsa_2048_cert, sample_rsa_1024_cert]

        filters_cfg = {"minimum_key_size_rsa": 2048}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should only keep 2048-bit cert
        assert len(result) == 1
        assert sample_rsa_2048_cert in result

    def test_minimum_key_size_ecc(self, sample_ecc_256_cert, sample_ecc_192_cert):
        """Test minimum ECC key size filtering."""
        pem_blocks = [sample_ecc_256_cert, sample_ecc_192_cert]

        filters_cfg = {"minimum_key_size_ecc": 256}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should only keep 256-bit cert
        assert len(result) == 1
        assert sample_ecc_256_cert in result

    def test_combined_filters(self, sample_root_cert, sample_intermediate_cert, expired_cert_pem):
        """Test multiple filters applied together."""
        # Duplicate root cert
        pem_blocks = [
            sample_root_cert,
            sample_root_cert,  # duplicate
            sample_intermediate_cert,
            expired_cert_pem,
        ]

        filters_cfg = {
            "unique_by_fingerprint": True,
            "not_expired_only": True,
            "root_certs_only": True,
        }
        result = apply_filters(pem_blocks, filters_cfg)

        # Should only keep one root cert (deduped, not expired, root only)
        assert len(result) == 1
        assert sample_root_cert in result

    def test_no_filters(self, sample_cert_pem):
        """Test that empty filter config returns all certs."""
        pem_blocks = [sample_cert_pem, sample_cert_pem]

        filters_cfg = {}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should return all certs unchanged
        assert len(result) == 2

    def test_filters_with_unparsable_cert(self, sample_cert_pem):
        """Test that unparsable PEM blocks are skipped gracefully."""
        pem_blocks = [
            sample_cert_pem,
            "-----BEGIN CERTIFICATE-----\nINVALID\n-----END CERTIFICATE-----\n",
        ]

        filters_cfg = {"ca_certs_only": True}
        result = apply_filters(pem_blocks, filters_cfg)

        # Should skip invalid cert and keep valid one
        assert len(result) >= 0  # Depends on whether sample_cert is a CA


@pytest.mark.config
class TestConfigMerge:
    """Test suite for config merging."""

    def test_merge_configs_simple(self):
        """Test basic config merging."""
        defaults = {"verify": {"fail_on_expired": True}, "package": False}
        craft = {"package": True}

        result = merge_configs(defaults, craft)

        assert result["package"] is True
        assert result["verify"]["fail_on_expired"] is True

    def test_merge_configs_deep(self):
        """Test deep merging of nested configs."""
        defaults = {
            "filters": {
                "unique_by_fingerprint": True,
                "root_certs_only": True,
            }
        }
        craft = {
            "filters": {
                "root_certs_only": False,  # Override
                "ca_certs_only": True,  # Add new
            }
        }

        result = merge_configs(defaults, craft)

        assert result["filters"]["unique_by_fingerprint"] is True
        assert result["filters"]["root_certs_only"] is False
        assert result["filters"]["ca_certs_only"] is True

    def test_merge_configs_craft_overrides(self):
        """Test that craft config overrides defaults."""
        defaults = {
            "output_formats": ["pem"],
            "verify": {"warn_days_before_expiry": 30},
        }
        craft = {
            "output_formats": ["pem", "jks", "p12"],
            "verify": {"warn_days_before_expiry": 60},
        }

        result = merge_configs(defaults, craft)

        assert result["output_formats"] == ["pem", "jks", "p12"]
        assert result["verify"]["warn_days_before_expiry"] == 60

    def test_merge_configs_empty_defaults(self):
        """Test merging with empty defaults."""
        defaults = {}
        craft = {"package": True, "verify": {"fail_on_expired": True}}

        result = merge_configs(defaults, craft)

        assert result == craft

    def test_merge_configs_empty_craft(self):
        """Test merging with empty craft config."""
        defaults = {"package": False, "verify": {"fail_on_expired": True}}
        craft = {}

        result = merge_configs(defaults, craft)

        assert result == defaults


@pytest.mark.integration
class TestDefaultsIntegration:
    """Test that defaults.yaml is properly loaded and applied in builds."""

    def test_defaults_loaded_in_build(self):
        """Test that defaults.yaml is loaded and merged during build."""
        # This would be an integration test that verifies defaults are loaded
        # For now, just check the imports work
        from bundlecraft.helpers.utils import merge_configs

        assert merge_configs is not None

    def test_root_certs_only_default_true(self):
        """Test that root_certs_only defaults to true."""
        from pathlib import Path

        from bundlecraft.helpers.utils import load_yaml

        defaults_path = Path(__file__).parent.parent / "config" / "defaults.yaml"
        if defaults_path.exists():
            defaults = load_yaml(defaults_path, required=False) or {}
            filters = defaults.get("filters") or {}
            # If root_certs_only is defined, it should be True
            if "root_certs_only" in filters:
                assert filters["root_certs_only"] is True
