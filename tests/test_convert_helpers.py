#!/usr/bin/env python3
"""
test_convert_helpers.py
Unit tests for convert_utils.py helper functions.
"""


from cryptography import x509
from cryptography.hazmat.backends import default_backend

from bundlecraft.helpers.convert_utils import (
    _format_alias,
    _get_cn,
    _sanitize_alias,
    _split_pem_blocks,
    _split_pem_key_blocks,
)


class TestSplitPemBlocks:
    """Test PEM certificate block splitting."""

    def test_split_single_cert(self, sample_cert_path):
        """Test splitting a single certificate."""
        text = sample_cert_path.read_text()
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 1
        assert blocks[0].startswith("-----BEGIN CERTIFICATE-----")
        assert blocks[0].endswith("-----END CERTIFICATE-----\n")

    def test_split_multiple_certs(self, multi_cert_bundle):
        """Test splitting multiple certificates."""
        text = multi_cert_bundle.read_text()
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 2

    def test_split_empty_string(self):
        """Test splitting empty string."""
        blocks = _split_pem_blocks("")
        assert len(blocks) == 0

    def test_split_no_complete_blocks(self):
        """Test splitting text with incomplete blocks."""
        text = "-----BEGIN CERTIFICATE-----\nIncomplete block"
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 0

    def test_split_with_noise(self):
        """Test splitting with extra text around certificates."""
        text = """Header text here
-----BEGIN CERTIFICATE-----
CERT1
-----END CERTIFICATE-----
Middle text
-----BEGIN CERTIFICATE-----
CERT2
-----END CERTIFICATE-----
Footer"""
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 2


class TestSplitPemKeyBlocks:
    """Test PEM private key block splitting."""

    def test_split_rsa_private_key(self):
        """Test splitting RSA private key."""
        text = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 1
        assert "RSA PRIVATE KEY" in blocks[0]

    def test_split_ec_private_key(self):
        """Test splitting EC private key."""
        text = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEII...
-----END EC PRIVATE KEY-----"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 1
        assert "EC PRIVATE KEY" in blocks[0]

    def test_split_generic_private_key(self):
        """Test splitting generic PRIVATE KEY."""
        text = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkq...
-----END PRIVATE KEY-----"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 1
        assert "PRIVATE KEY" in blocks[0]

    def test_split_multiple_keys(self):
        """Test splitting multiple private keys."""
        text = """-----BEGIN RSA PRIVATE KEY-----
KEY1
-----END RSA PRIVATE KEY-----
-----BEGIN EC PRIVATE KEY-----
KEY2
-----END EC PRIVATE KEY-----"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 2

    def test_split_no_keys(self):
        """Test splitting text with no private keys."""
        text = """-----BEGIN CERTIFICATE-----
CERT
-----END CERTIFICATE-----"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 0

    def test_split_incomplete_key(self):
        """Test splitting incomplete private key block."""
        text = """-----BEGIN RSA PRIVATE KEY-----
Incomplete"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 0

    def test_split_encrypted_key(self):
        """Test splitting encrypted private key."""
        text = """-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFLTBXBgkq...
-----END ENCRYPTED PRIVATE KEY-----"""
        blocks = _split_pem_key_blocks(text)
        assert len(blocks) == 1
        assert "ENCRYPTED PRIVATE KEY" in blocks[0]


class TestGetCn:
    """Test Common Name extraction from certificates."""

    def test_get_cn_from_valid_cert(self, sample_cert_path):
        """Test extracting CN from a valid certificate."""
        text = sample_cert_path.read_text()
        cert = x509.load_pem_x509_certificate(text.encode(), default_backend())
        cn = _get_cn(cert)
        assert cn is not None
        assert len(cn) > 0

    def test_get_cn_fallback_to_subject(self, intermediate_cert_path):
        """Test CN extraction with fallback to subject string."""
        text = intermediate_cert_path.read_text()
        cert = x509.load_pem_x509_certificate(text.encode(), default_backend())
        cn = _get_cn(cert)
        # Should return CN or truncated subject string
        assert cn is not None
        assert len(cn) <= 64

    def test_get_cn_max_length(self, sample_cert_path):
        """Test that CN is truncated to max 64 chars."""
        text = sample_cert_path.read_text()
        cert = x509.load_pem_x509_certificate(text.encode(), default_backend())
        cn = _get_cn(cert)
        assert len(cn) <= 64


class TestSanitizeAlias:
    """Test alias sanitization for keytool/openssl."""

    def test_sanitize_alphanumeric(self):
        """Test sanitizing alphanumeric strings."""
        result = _sanitize_alias("ValidAlias123")
        assert result == "ValidAlias123"

    def test_sanitize_with_allowed_chars(self):
        """Test sanitizing with allowed special characters."""
        result = _sanitize_alias("alias-name_v1.0")
        assert result == "alias-name_v1.0"

    def test_sanitize_with_spaces(self):
        """Test sanitizing aliases with spaces."""
        result = _sanitize_alias("my alias name")
        assert result == "my_alias_name"
        assert " " not in result

    def test_sanitize_with_special_chars(self):
        """Test sanitizing aliases with special characters."""
        result = _sanitize_alias("alias@#$%name")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result
        # Should replace with underscores
        assert "_" in result

    def test_sanitize_max_length(self):
        """Test that aliases are truncated to 80 characters."""
        long_alias = "a" * 100
        result = _sanitize_alias(long_alias)
        assert len(result) == 80

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string."""
        result = _sanitize_alias("")
        assert result == ""

    def test_sanitize_unicode(self):
        """Test sanitizing unicode characters."""
        result = _sanitize_alias("aliás_ñame_中文")
        # isalnum() allows unicode letters, so they're preserved
        assert result == "aliás_ñame_中文"

    def test_sanitize_dots_and_dashes(self):
        """Test that dots and dashes are preserved."""
        result = _sanitize_alias("sub.domain-alias.v1")
        assert result == "sub.domain-alias.v1"


class TestFormatAlias:
    """Test alias template formatting."""

    def test_format_alias_with_cn_and_serial(self):
        """Test formatting alias with CN and serial placeholders."""
        template = "{subject.CN}-{serial}"
        result = _format_alias(template, "TestCA", "123456")
        assert result == "TestCA-123456"

    def test_format_alias_cn_only(self):
        """Test formatting alias with CN only."""
        template = "{subject.CN}"
        result = _format_alias(template, "MyCA", "789")
        assert result == "MyCA"

    def test_format_alias_serial_only(self):
        """Test formatting alias with serial only."""
        template = "cert-{serial}"
        result = _format_alias(template, "CA", "abc123")
        assert result == "cert-abc123"

    def test_format_alias_no_placeholders(self):
        """Test formatting alias with no placeholders."""
        template = "static-alias"
        result = _format_alias(template, "CA", "123")
        assert result == "static-alias"

    def test_format_alias_multiple_placeholders(self):
        """Test formatting with multiple placeholder instances."""
        template = "{subject.CN}_{serial}_{subject.CN}"
        result = _format_alias(template, "Root", "999")
        assert result == "Root_999_Root"

    def test_format_alias_empty_cn(self):
        """Test formatting when CN is empty."""
        template = "{subject.CN}-{serial}"
        result = _format_alias(template, "", "123")
        assert result == "Unknown_CN-123"

    def test_format_alias_none_cn(self):
        """Test formatting when CN is None."""
        template = "{subject.CN}-{serial}"
        result = _format_alias(template, None, "123")
        assert result == "Unknown_CN-123"

    def test_format_alias_complex_template(self):
        """Test formatting with complex template."""
        template = "CA-{subject.CN}-serial-{serial}-end"
        result = _format_alias(template, "IntermediateCA", "abcd")
        assert result == "CA-IntermediateCA-serial-abcd-end"

    def test_format_alias_error_handling(self):
        """Test that errors result in fallback format."""
        template = "{subject.CN}-{serial}"
        # Should handle edge cases gracefully
        result = _format_alias(template, "Valid", "123")
        assert "Valid" in result or "Unknown_CN" in result
