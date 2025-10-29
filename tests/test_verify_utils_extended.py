"""
Extended tests for bundlecraft/helpers/verify_utils.py

Focuses on improving coverage from 19% to 70%+, covering:
- verifier() function with various scenarios
- verify_manifest() and checksum validation
- Certificate expiry checking and date handling
- Error handling for parse errors and missing files
- Helper functions: _split_pem_blocks, _check_output_files, _compare_output_counts
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from bundlecraft.helpers.exit_codes import ExitCode
from bundlecraft.helpers.verify_utils import (
    _check_output_files,
    _compare_output_counts,
    _count_certs_in_file,
    _sha256_file,
    _split_pem_blocks,
    verifier,
    verify_manifest,
)


# Helper to generate test certificates
def generate_test_cert_pem(days_valid=365, subject_cn="Test CA"):
    """Generate a test certificate in PEM format"""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, subject_cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Org"),
        ]
    )

    now = datetime.now(timezone.utc)
    # For expired certs, set both dates in the past
    if days_valid < 0:
        not_before = now + timedelta(days=days_valid) - timedelta(days=365)
        not_after = now + timedelta(days=days_valid)
    else:
        not_before = now
        not_after = now + timedelta(days=days_valid)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


class TestVerifierFunction:
    """Test the main verifier() function"""

    def test_verifier_target_not_found(self, capsys):
        """Test verifier with non-existent target"""
        result = verifier(Path("/nonexistent/path"))
        assert result == ExitCode.INPUT_ERROR
        captured = capsys.readouterr()
        assert "Target not found" in captured.err

    def test_verifier_single_valid_pem(self, tmp_path, capsys):
        """Test verifier with a single valid PEM file"""
        pem_file = tmp_path / "valid.pem"
        pem_content = generate_test_cert_pem(days_valid=365)
        pem_file.write_text(pem_content)

        result = verifier(pem_file)
        assert result == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "All certificates valid" in captured.out
        assert "Verified 1 certificate" in captured.out

    def test_verifier_expired_certificate(self, tmp_path, capsys):
        """Test verifier detects expired certificates"""
        pem_file = tmp_path / "expired.pem"
        pem_content = generate_test_cert_pem(days_valid=-30)  # Expired 30 days ago
        pem_file.write_text(pem_content)

        result = verifier(pem_file, fail_on_expired=True)
        assert result == ExitCode.EXPIRED_CERT
        captured = capsys.readouterr()
        assert "Expired:" in captured.out
        assert "Verification failed" in captured.out

    def test_verifier_expiring_soon(self, tmp_path, capsys):
        """Test verifier warns about certificates expiring soon"""
        pem_file = tmp_path / "expiring.pem"
        pem_content = generate_test_cert_pem(days_valid=15)  # Expires in 15 days
        pem_file.write_text(pem_content)

        result = verifier(pem_file, warn_days=30)
        assert result == ExitCode.GENERAL_ERROR
        captured = capsys.readouterr()
        assert "Expiring soon" in captured.out
        assert "days left" in captured.out

    def test_verifier_directory_with_multiple_pems(self, tmp_path, capsys):
        """Test verifier on directory with multiple PEM files"""
        for i in range(3):
            pem_file = tmp_path / f"cert{i}.pem"
            pem_content = generate_test_cert_pem(days_valid=365, subject_cn=f"Test CA {i}")
            pem_file.write_text(pem_content)

        result = verifier(tmp_path)
        assert result == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "Verified 3 certificate" in captured.out

    def test_verifier_directory_no_pems(self, tmp_path, capsys):
        """Test verifier on directory with no PEM files"""
        result = verifier(tmp_path)
        assert result == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "No PEM files found" in captured.out

    def test_verifier_unsupported_file_type(self, tmp_path, capsys):
        """Test verifier rejects unsupported file types"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a certificate")

        result = verifier(txt_file)
        assert result == ExitCode.INPUT_ERROR
        captured = capsys.readouterr()
        assert "Unsupported file type" in captured.err

    def test_verifier_invalid_pem_content(self, tmp_path, capsys):
        """Test verifier handles invalid PEM content gracefully"""
        pem_file = tmp_path / "invalid.pem"
        pem_file.write_text(
            "-----BEGIN CERTIFICATE-----\nInvalidBase64Content\n-----END CERTIFICATE-----\n"
        )

        result = verifier(pem_file)
        assert result == ExitCode.INVALID_CERT
        captured = capsys.readouterr()
        assert "Parse error" in captured.out
        assert "Errors = 1" in captured.out

    def test_verifier_multiple_certs_in_single_pem(self, tmp_path, capsys):
        """Test verifier handles multiple certificates in one PEM file"""
        pem_file = tmp_path / "bundle.pem"
        cert1 = generate_test_cert_pem(days_valid=365, subject_cn="CA 1")
        cert2 = generate_test_cert_pem(days_valid=365, subject_cn="CA 2")
        pem_file.write_text(cert1 + cert2)

        result = verifier(pem_file)
        assert result == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "Verified 2 certificate" in captured.out

    def test_verifier_fail_on_expired_false(self, tmp_path, capsys):
        """Test verifier with fail_on_expired=False continues despite expired certs"""
        pem_file = tmp_path / "expired.pem"
        pem_content = generate_test_cert_pem(days_valid=-30)
        pem_file.write_text(pem_content)

        result = verifier(pem_file, fail_on_expired=False)
        # With fail_on_expired=False and no other errors, should succeed
        # The condition is: if errors or (expired and fail_on_expired)
        # So with fail_on_expired=False, expired certs are reported but don't fail
        assert result == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "Expired:" in captured.out
        assert "All certificates valid" in captured.out


class TestVerifyManifest:
    """Test manifest verification functionality"""

    def test_verify_manifest_success(self, tmp_path, capsys):
        """Test successful manifest verification"""
        # Create test file and manifest
        test_file = tmp_path / "bundle.pem"
        test_content = generate_test_cert_pem()
        test_file.write_text(test_content)

        # Calculate SHA256
        import hashlib

        sha256_hash = hashlib.sha256(test_content.encode()).hexdigest()

        # Create manifest
        manifest = tmp_path / "manifest.json"
        manifest_data = {
            "files": [{"path": "bundle.pem", "sha256": sha256_hash, "size": len(test_content)}]
        }
        manifest.write_text(json.dumps(manifest_data))

        result = verify_manifest(manifest)
        assert result is True
        captured = capsys.readouterr()
        assert "Verified: bundle.pem" in captured.out
        assert "Manifest verification successful" in captured.out

    def test_verify_manifest_missing_file(self, tmp_path, capsys):
        """Test manifest verification with missing file"""
        manifest = tmp_path / "manifest.json"
        manifest_data = {"files": [{"path": "missing.pem", "sha256": "a" * 64, "size": 1000}]}
        manifest.write_text(json.dumps(manifest_data))

        result = verify_manifest(manifest)
        assert result is False
        captured = capsys.readouterr()
        assert "Missing file" in captured.out

    def test_verify_manifest_hash_mismatch(self, tmp_path, capsys):
        """Test manifest verification detects hash mismatches"""
        test_file = tmp_path / "bundle.pem"
        test_file.write_text(generate_test_cert_pem())

        manifest = tmp_path / "manifest.json"
        manifest_data = {
            "files": [
                {
                    "path": "bundle.pem",
                    "sha256": "0" * 64,  # Wrong hash
                    "size": 100,
                }
            ]
        }
        manifest.write_text(json.dumps(manifest_data))

        result = verify_manifest(manifest)
        assert result is False
        captured = capsys.readouterr()
        assert "Hash mismatch" in captured.out

    def test_verify_manifest_missing_manifest_file(self, tmp_path, capsys):
        """Test verify_manifest when manifest.json doesn't exist"""
        manifest = tmp_path / "manifest.json"
        result = verify_manifest(manifest)
        assert result is False
        captured = capsys.readouterr()
        assert "Manifest file missing" in captured.out

    def test_verify_manifest_malformed_json(self, tmp_path, capsys):
        """Test verify_manifest with malformed JSON"""
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{ invalid json }")

        result = verify_manifest(manifest)
        assert result is False
        captured = capsys.readouterr()
        assert "Failed to parse manifest" in captured.out

    def test_verify_manifest_no_files_field(self, tmp_path, capsys):
        """Test verify_manifest with missing 'files' field"""
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"version": "1.0"}))

        result = verify_manifest(manifest)
        assert result is False
        captured = capsys.readouterr()
        assert "No 'files' field found" in captured.out

    def test_verify_manifest_skips_manifest_itself(self, tmp_path, capsys):
        """Test that manifest verification skips manifest.json itself"""
        manifest = tmp_path / "manifest.json"
        manifest_data = {"files": [{"path": "manifest.json", "sha256": "a" * 64, "size": 100}]}
        manifest.write_text(json.dumps(manifest_data))

        result = verify_manifest(manifest)
        assert result is True  # Should succeed as it skips manifest.json
        captured = capsys.readouterr()
        assert "Skipping manifest file" in captured.out

    def test_verify_manifest_with_checksums_file(self, tmp_path, capsys):
        """Test manifest verification also checks checksums.sha256"""
        test_file = tmp_path / "bundle.pem"
        test_content = generate_test_cert_pem()
        test_file.write_text(test_content)

        import hashlib

        sha256_hash = hashlib.sha256(test_content.encode()).hexdigest()

        # Create manifest
        manifest = tmp_path / "manifest.json"
        manifest_data = {
            "files": [{"path": "bundle.pem", "sha256": sha256_hash, "size": len(test_content)}]
        }
        manifest.write_text(json.dumps(manifest_data))

        # Create checksums file
        checksums = tmp_path / "checksums.sha256"
        checksums.write_text(f"{sha256_hash}  bundle.pem\n")

        result = verify_manifest(manifest)
        assert result is True


class TestSplitPemBlocks:
    """Test _split_pem_blocks helper function"""

    def test_split_single_certificate(self):
        """Test splitting a single certificate"""
        pem = generate_test_cert_pem()
        blocks = _split_pem_blocks(pem)
        assert len(blocks) == 1
        assert "-----BEGIN CERTIFICATE-----" in blocks[0]
        assert "-----END CERTIFICATE-----" in blocks[0]

    def test_split_multiple_certificates(self):
        """Test splitting multiple certificates"""
        pem1 = generate_test_cert_pem(subject_cn="CA 1")
        pem2 = generate_test_cert_pem(subject_cn="CA 2")
        combined = pem1 + pem2
        blocks = _split_pem_blocks(combined)
        assert len(blocks) == 2

    def test_split_empty_string(self):
        """Test splitting empty string returns empty list"""
        blocks = _split_pem_blocks("")
        assert blocks == []

    def test_split_non_certificate_pem(self):
        """Test that non-certificate PEM blocks are ignored"""
        pem = "-----BEGIN PRIVATE KEY-----\ndata\n-----END PRIVATE KEY-----\n"
        blocks = _split_pem_blocks(pem)
        assert blocks == []


class TestCheckOutputFiles:
    """Test _check_output_files helper"""

    def test_check_output_files_all_valid(self, tmp_path):
        """Test all output files are valid"""
        (tmp_path / "bundle.p7b").write_bytes(b"some data")
        (tmp_path / "bundle.p12").write_bytes(b"some data")

        result = _check_output_files(tmp_path)
        assert result is True

    def test_check_output_files_empty_p7b(self, tmp_path, capsys):
        """Test detection of empty P7B file"""
        (tmp_path / "bundle.p7b").write_bytes(b"")
        result = _check_output_files(tmp_path)
        assert result is False
        captured = capsys.readouterr()
        assert "Empty or missing output file" in captured.out

    def test_check_output_files_empty_p12(self, tmp_path, capsys):
        """Test detection of empty P12 file"""
        (tmp_path / "bundle.p12").write_bytes(b"")
        result = _check_output_files(tmp_path)
        assert result is False
        captured = capsys.readouterr()
        assert "Empty or missing output file" in captured.out

    def test_check_output_files_no_files(self, tmp_path):
        """Test when no output files exist (should pass)"""
        result = _check_output_files(tmp_path)
        assert result is True


class TestSha256File:
    """Test _sha256_file helper function"""

    def test_sha256_file_calculates_correctly(self, tmp_path):
        """Test SHA256 calculation is correct"""
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        import hashlib

        expected_hash = hashlib.sha256(test_content).hexdigest()
        actual_hash = _sha256_file(test_file)
        assert actual_hash == expected_hash

    def test_sha256_file_large_file(self, tmp_path):
        """Test SHA256 calculation on large file (chunked reading)"""
        test_file = tmp_path / "large.bin"
        # Create a file larger than the 8192 chunk size
        test_content = b"x" * 20000
        test_file.write_bytes(test_content)

        import hashlib

        expected_hash = hashlib.sha256(test_content).hexdigest()
        actual_hash = _sha256_file(test_file)
        assert actual_hash == expected_hash


class TestCountCertsInFile:
    """Test _count_certs_in_file for various formats"""

    def test_count_certs_pem(self, tmp_path):
        """Test counting certificates in PEM file"""
        pem_file = tmp_path / "bundle.pem"
        cert1 = generate_test_cert_pem(subject_cn="CA 1")
        cert2 = generate_test_cert_pem(subject_cn="CA 2")
        pem_file.write_text(cert1 + cert2)

        count = _count_certs_in_file(pem_file)
        assert count == 2

    def test_count_certs_empty_pem(self, tmp_path):
        """Test counting certificates in empty PEM file"""
        pem_file = tmp_path / "empty.pem"
        pem_file.write_text("")

        count = _count_certs_in_file(pem_file)
        assert count == 0

    @patch("subprocess.run")
    def test_count_certs_p7b(self, mock_run, tmp_path):
        """Test counting certificates in P7B file"""
        p7b_file = tmp_path / "bundle.p7b"
        p7b_file.write_bytes(b"fake p7b data")

        # Mock subprocess to return 2 certificates
        mock_result = Mock()
        mock_result.stdout = (
            "-----BEGIN CERTIFICATE-----\ndata1\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\ndata2\n-----END CERTIFICATE-----\n"
        )
        mock_run.return_value = mock_result

        count = _count_certs_in_file(p7b_file)
        assert count == 2
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_count_certs_p12(self, mock_run, tmp_path):
        """Test counting certificates in P12 file"""
        p12_file = tmp_path / "bundle.p12"
        p12_file.write_bytes(b"fake p12 data")

        # Mock subprocess to return 3 certificates
        mock_result = Mock()
        mock_result.stdout = "-----BEGIN CERTIFICATE-----\n" * 3
        mock_run.return_value = mock_result

        count = _count_certs_in_file(p12_file)
        assert count == 3
        mock_run.assert_called_once()

    @patch("jks.KeyStore.load")
    def test_count_certs_jks(self, mock_jks_load, tmp_path):
        """Test counting certificates in JKS file using pyjks"""
        jks_file = tmp_path / "bundle.jks"
        jks_file.write_bytes(b"fake jks data")

        # Mock jks.KeyStore with 1 TrustedCertEntry
        import jks
        mock_keystore = Mock()
        mock_entry = Mock(spec=jks.TrustedCertEntry)
        mock_keystore.entries = {"cert1": mock_entry}
        mock_jks_load.return_value = mock_keystore

        count = _count_certs_in_file(jks_file)
        assert count == 1
        mock_jks_load.assert_called_once()

    @patch("subprocess.run")
    def test_count_certs_subprocess_error(self, mock_run, tmp_path, capsys):
        """Test handling of subprocess errors"""
        p7b_file = tmp_path / "bad.p7b"
        p7b_file.write_bytes(b"invalid data")

        mock_run.side_effect = subprocess.CalledProcessError(1, "openssl")

        count = _count_certs_in_file(p7b_file)
        assert count == 0
        captured = capsys.readouterr()
        assert "Could not count certs" in captured.out


class TestCompareOutputCounts:
    """Test _compare_output_counts helper"""

    def test_compare_output_counts_all_match(self, tmp_path, capsys):
        """Test when all format counts match"""
        # Create test files with same cert count
        cert = generate_test_cert_pem()
        (tmp_path / "bundle.pem").write_text(cert)
        (tmp_path / "bundle.p7b").write_bytes(b"fake")
        (tmp_path / "bundle.p12").write_bytes(b"fake")

        with patch("bundlecraft.helpers.verify_utils._count_certs_in_file", return_value=1):
            _compare_output_counts(tmp_path)
            captured = capsys.readouterr()
            assert "count OK" in captured.out

    def test_compare_output_counts_mismatch(self, tmp_path, capsys):
        """Test when format counts don't match"""
        cert = generate_test_cert_pem()
        (tmp_path / "bundle.pem").write_text(cert)
        (tmp_path / "bundle.p7b").write_bytes(b"fake")

        def mock_count(file_path):
            if file_path.suffix == ".pem":
                return 3
            return 2

        with patch("bundlecraft.helpers.verify_utils._count_certs_in_file", side_effect=mock_count):
            _compare_output_counts(tmp_path)
            captured = capsys.readouterr()
            assert "count mismatch" in captured.out

    def test_compare_output_counts_no_files(self, tmp_path, capsys):
        """Test when no output files exist"""
        _compare_output_counts(tmp_path)
        captured = capsys.readouterr()
        assert "No outputs found" in captured.out
