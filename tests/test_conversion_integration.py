#!/usr/bin/env python3
"""
Integration tests for certificate format conversion without openssl dependency.

Tests the complete conversion workflow using only Python cryptography module.
"""

import os
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, timezone

from bundlecraft.helpers.convert_utils import (
    create_p7b,
    create_pkcs12,
    normalize_to_pem,
)
from bundlecraft.helpers.verify_utils import _count_certs_in_file


def generate_test_cert(cn: str, days_valid: int = 365):
    """Generate a test certificate"""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BundleCraft Test"),
    ])
    
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=days_valid))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture
def test_certs(tmp_path):
    """Create test certificates"""
    certs = []
    for i in range(1, 4):
        cert_pem = generate_test_cert(f"Test CA {i}")
        certs.append(cert_pem)
    
    # Single cert file
    single_cert = tmp_path / "single.pem"
    single_cert.write_text(certs[0])
    
    # Multi cert bundle
    multi_cert = tmp_path / "multi.pem"
    multi_cert.write_text("".join(certs))
    
    return {
        "single": single_cert,
        "multi": multi_cert,
        "count_single": 1,
        "count_multi": 3,
    }


class TestP7BConversion:
    """Test P7B (PKCS#7) conversion without openssl"""
    
    def test_single_cert_to_p7b(self, test_certs, tmp_path):
        """Convert single certificate to P7B"""
        create_p7b(test_certs["single"], tmp_path, "single_bundle", force=True)
        
        p7b_file = tmp_path / "single_bundle.p7b"
        assert p7b_file.exists()
        assert p7b_file.stat().st_size > 0
        
        # Verify certificate count
        count = _count_certs_in_file(p7b_file)
        assert count == test_certs["count_single"]
    
    def test_multi_cert_to_p7b(self, test_certs, tmp_path):
        """Convert multiple certificates to P7B"""
        create_p7b(test_certs["multi"], tmp_path, "multi_bundle", force=True)
        
        p7b_file = tmp_path / "multi_bundle.p7b"
        assert p7b_file.exists()
        assert p7b_file.stat().st_size > 0
        
        # Verify certificate count
        count = _count_certs_in_file(p7b_file)
        assert count == test_certs["count_multi"]
    
    def test_p7b_to_pem_roundtrip(self, test_certs, tmp_path):
        """Test P7B to PEM conversion roundtrip"""
        # Create P7B
        create_p7b(test_certs["multi"], tmp_path, "roundtrip", force=True)
        
        p7b_file = tmp_path / "roundtrip.p7b"
        output_pem = tmp_path / "roundtrip_from_p7b.pem"
        
        # Normalize back to PEM
        result_pem, has_keys = normalize_to_pem(p7b_file, output_pem, input_format="p7b")
        
        assert result_pem == output_pem
        assert not has_keys
        assert output_pem.exists()
        
        # Verify certificate count matches
        text = output_pem.read_text()
        cert_count = text.count("-----BEGIN CERTIFICATE-----")
        assert cert_count == test_certs["count_multi"]


class TestP12Conversion:
    """Test PKCS#12 conversion without openssl"""
    
    def test_single_cert_to_p12(self, test_certs, tmp_path, monkeypatch):
        """Convert single certificate to P12"""
        overrides = {"password": "testpassword"}
        create_pkcs12(test_certs["single"], tmp_path, "single_bundle", overrides, force=True)
        
        p12_file = tmp_path / "single_bundle.p12"
        assert p12_file.exists()
        assert p12_file.stat().st_size > 0
        
        # Verify certificate count
        monkeypatch.setenv("TRUST_P12_PASSWORD", "testpassword")
        count = _count_certs_in_file(p12_file)
        assert count == test_certs["count_single"]
    
    def test_multi_cert_to_p12(self, test_certs, tmp_path, monkeypatch):
        """Convert multiple certificates to P12"""
        overrides = {"password": "testpassword"}
        create_pkcs12(test_certs["multi"], tmp_path, "multi_bundle", overrides, force=True)
        
        p12_file = tmp_path / "multi_bundle.p12"
        assert p12_file.exists()
        assert p12_file.stat().st_size > 0
        
        # Verify certificate count
        monkeypatch.setenv("TRUST_P12_PASSWORD", "testpassword")
        count = _count_certs_in_file(p12_file)
        assert count == test_certs["count_multi"]
    
    def test_p12_to_pem_roundtrip(self, test_certs, tmp_path):
        """Test P12 to PEM conversion roundtrip"""
        # Create P12
        overrides = {"password": "testpassword"}
        create_pkcs12(test_certs["multi"], tmp_path, "roundtrip", overrides, force=True)
        
        p12_file = tmp_path / "roundtrip.p12"
        output_pem = tmp_path / "roundtrip_from_p12.pem"
        
        # Normalize back to PEM
        result_pem, has_keys = normalize_to_pem(
            p12_file, output_pem, input_format="p12", password="testpassword"
        )
        
        assert result_pem == output_pem
        assert not has_keys
        assert output_pem.exists()
        
        # Verify certificate count matches
        text = output_pem.read_text()
        cert_count = text.count("-----BEGIN CERTIFICATE-----")
        assert cert_count == test_certs["count_multi"]
    
    def test_p12_with_default_password(self, test_certs, tmp_path, monkeypatch):
        """Test P12 creation with default password"""
        # The test_env fixture sets TRUST_P12_PASSWORD="test-password" by default
        # So we create with that password and verify we can read it back
        overrides = {}  # Use default password from environment
        create_pkcs12(test_certs["single"], tmp_path, "default_pw", overrides, force=True)
        
        p12_file = tmp_path / "default_pw.p12"
        assert p12_file.exists()
        
        # Should be readable with the same password from environment (test-password)
        count = _count_certs_in_file(p12_file)
        assert count == test_certs["count_single"]


class TestForceOverwrite:
    """Test force overwrite functionality"""
    
    def test_p7b_force_overwrite(self, test_certs, tmp_path):
        """Test P7B force overwrite"""
        # Create first file
        create_p7b(test_certs["single"], tmp_path, "test", force=True)
        p7b_file = tmp_path / "test.p7b"
        first_size = p7b_file.stat().st_size
        
        # Overwrite with different content
        create_p7b(test_certs["multi"], tmp_path, "test", force=True)
        second_size = p7b_file.stat().st_size
        
        # Size should be different (multi cert is larger)
        assert second_size > first_size
    
    def test_p7b_no_force_raises(self, test_certs, tmp_path):
        """Test P7B without force raises FileExistsError"""
        create_p7b(test_certs["single"], tmp_path, "test", force=True)
        
        with pytest.raises(FileExistsError, match="Use --force to overwrite"):
            create_p7b(test_certs["single"], tmp_path, "test", force=False)
    
    def test_p12_force_overwrite(self, test_certs, tmp_path):
        """Test P12 force overwrite"""
        overrides = {"password": "test"}
        
        # Create first file
        create_pkcs12(test_certs["single"], tmp_path, "test", overrides, force=True)
        p12_file = tmp_path / "test.p12"
        first_size = p12_file.stat().st_size
        
        # Overwrite with different content
        create_pkcs12(test_certs["multi"], tmp_path, "test", overrides, force=True)
        second_size = p12_file.stat().st_size
        
        # Size should be different
        assert second_size != first_size
    
    def test_p12_no_force_raises(self, test_certs, tmp_path):
        """Test P12 without force raises FileExistsError"""
        overrides = {"password": "test"}
        create_pkcs12(test_certs["single"], tmp_path, "test", overrides, force=True)
        
        with pytest.raises(FileExistsError, match="Use --force to overwrite"):
            create_pkcs12(test_certs["single"], tmp_path, "test", overrides, force=False)


class TestEmptyInput:
    """Test handling of empty or invalid input"""
    
    def test_p7b_with_empty_pem(self, tmp_path, capsys):
        """Test P7B creation with empty PEM file"""
        empty_pem = tmp_path / "empty.pem"
        empty_pem.write_text("")
        
        create_p7b(empty_pem, tmp_path, "empty", force=True)
        
        # Should print warning and not create P7B
        captured = capsys.readouterr()
        assert "No certificates found" in captured.out
        assert not (tmp_path / "empty.p7b").exists()
    
    def test_p12_with_empty_pem(self, tmp_path, capsys):
        """Test P12 creation with empty PEM file"""
        empty_pem = tmp_path / "empty.pem"
        empty_pem.write_text("")
        
        overrides = {"password": "test"}
        create_pkcs12(empty_pem, tmp_path, "empty", overrides, force=True)
        
        # Should print warning and not create P12
        captured = capsys.readouterr()
        assert "No certificates found" in captured.out
        assert not (tmp_path / "empty.p12").exists()
    
    def test_p7b_with_invalid_cert(self, tmp_path, capsys):
        """Test P7B creation with invalid certificate"""
        invalid_pem = tmp_path / "invalid.pem"
        invalid_pem.write_text("-----BEGIN CERTIFICATE-----\nINVALID\n-----END CERTIFICATE-----\n")
        
        create_p7b(invalid_pem, tmp_path, "invalid", force=True)
        
        # Should print warning about failed cert and not create P7B
        captured = capsys.readouterr()
        assert "Failed to load certificate" in captured.out or "No valid certificates" in captured.out
