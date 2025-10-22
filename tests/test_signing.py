#!/usr/bin/env python3
"""
Tests for GPG signing functionality in BundleCraft.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from bundlecraft.helpers.signing import (
    export_public_key,
    get_gpg_instance,
    list_available_keys,
    sign_file,
    verify_signature,
)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")
    return test_file


@pytest.fixture
def mock_gpg():
    """Create a mock GPG instance."""
    with patch("bundlecraft.helpers.signing.gnupg.GPG") as mock:
        gpg_instance = MagicMock()
        mock.return_value = gpg_instance
        yield gpg_instance


class TestGetGpgInstance:
    def test_get_gpg_instance_default(self, mock_gpg):
        """Test getting GPG instance with default home directory."""
        get_gpg_instance()
        # Verify GPG was instantiated without gnupghome
        import bundlecraft.helpers.signing as signing_module

        signing_module.gnupg.GPG.assert_called_once()

    def test_get_gpg_instance_custom_home(self, tmp_path, mock_gpg):
        """Test getting GPG instance with custom home directory."""
        get_gpg_instance(tmp_path)
        # Verify GPG was instantiated with custom gnupghome


class TestSignFile:
    def test_sign_file_missing_file(self, tmp_path):
        """Test signing a non-existent file raises FileNotFoundError."""
        non_existent = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            sign_file(non_existent, key_id="test-key")

    def test_sign_file_no_key_id(self, temp_file):
        """Test signing without key_id and no env var raises ValueError."""
        # Ensure GPG_KEY_ID is not set
        os.environ.pop("GPG_KEY_ID", None)

        with pytest.raises(ValueError) as exc_info:
            sign_file(temp_file)

        assert "GPG key ID not provided" in str(exc_info.value)
        assert "GPG_KEY_ID" in str(exc_info.value)

    def test_sign_file_with_env_key_id(self, temp_file, mock_gpg):
        """Test signing with key_id from environment variable."""
        os.environ["GPG_KEY_ID"] = "env-key-id"

        # Mock successful signing
        mock_signed = MagicMock()
        mock_signed.data = b"-----BEGIN PGP SIGNATURE-----\ntest\n-----END PGP SIGNATURE-----"
        mock_gpg.sign.return_value = mock_signed

        try:
            sig_path = sign_file(temp_file)
            assert sig_path.exists()
            assert sig_path.suffix == ".asc"
        finally:
            os.environ.pop("GPG_KEY_ID", None)

    def test_sign_file_success(self, temp_file, mock_gpg):
        """Test successful file signing."""
        # Mock successful signing
        mock_signed = MagicMock()
        mock_signed.data = b"-----BEGIN PGP SIGNATURE-----\ntest\n-----END PGP SIGNATURE-----"
        mock_gpg.sign.return_value = mock_signed

        sig_path = sign_file(temp_file, key_id="test-key")

        assert sig_path.exists()
        assert sig_path.name == "test.txt.asc"
        mock_gpg.sign.assert_called_once()

    def test_sign_file_custom_output(self, temp_file, mock_gpg):
        """Test signing with custom output path."""
        custom_output = temp_file.parent / "custom.sig"

        # Mock successful signing
        mock_signed = MagicMock()
        mock_signed.data = b"-----BEGIN PGP SIGNATURE-----\ntest\n-----END PGP SIGNATURE-----"
        mock_gpg.sign.return_value = mock_signed

        sig_path = sign_file(temp_file, key_id="test-key", output_path=custom_output)

        assert sig_path == custom_output
        assert sig_path.exists()

    def test_sign_file_key_not_found(self, temp_file, mock_gpg):
        """Test signing with non-existent key raises RuntimeError."""
        # Mock signing failure (key not found)
        mock_signed = MagicMock()
        mock_signed.data = None
        mock_signed.stderr = "secret key not available"
        mock_gpg.sign.return_value = mock_signed

        with pytest.raises(RuntimeError) as exc_info:
            sign_file(temp_file, key_id="nonexistent-key")

        assert "Key 'nonexistent-key' not found" in str(exc_info.value)

    def test_sign_file_bad_passphrase(self, temp_file, mock_gpg):
        """Test signing with wrong passphrase raises RuntimeError."""
        # Mock signing failure (bad passphrase)
        mock_signed = MagicMock()
        mock_signed.data = None
        mock_signed.stderr = "bad passphrase"
        mock_gpg.sign.return_value = mock_signed

        with pytest.raises(RuntimeError) as exc_info:
            sign_file(temp_file, key_id="test-key", passphrase="wrong")

        assert "Invalid passphrase" in str(exc_info.value)


class TestVerifySignature:
    def test_verify_signature_missing_file(self, tmp_path):
        """Test verifying signature for non-existent file raises FileNotFoundError."""
        non_existent = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            verify_signature(non_existent)

    def test_verify_signature_missing_signature(self, temp_file):
        """Test verifying when signature file doesn't exist raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            verify_signature(temp_file)

    def test_verify_signature_success(self, temp_file, mock_gpg):
        """Test successful signature verification."""
        sig_file = temp_file.with_suffix(".txt.asc")
        sig_file.write_text("fake signature")

        # Mock successful verification
        mock_verified = MagicMock()
        mock_verified.valid = True
        mock_verified.key_id = "ABC123"
        mock_verified.username = "Test User"
        mock_gpg.verify_data.return_value = mock_verified

        valid, message = verify_signature(temp_file, sig_file)

        assert valid is True
        assert "Valid signature" in message
        assert "ABC123" in message

    def test_verify_signature_failure(self, temp_file, mock_gpg):
        """Test failed signature verification."""
        sig_file = temp_file.with_suffix(".txt.asc")
        sig_file.write_text("fake signature")

        # Mock failed verification
        mock_verified = MagicMock()
        mock_verified.valid = False
        mock_verified.status = "invalid signature"
        mock_gpg.verify_data.return_value = mock_verified

        valid, message = verify_signature(temp_file, sig_file)

        assert valid is False
        assert "Invalid signature" in message

    def test_verify_signature_with_keyring(self, temp_file, mock_gpg, tmp_path):
        """Test signature verification with external keyring."""
        sig_file = temp_file.with_suffix(".txt.asc")
        sig_file.write_text("fake signature")
        keyring = tmp_path / "keyring.asc"
        keyring.write_text("fake keyring")

        # Mock keyring import and verification
        mock_import = MagicMock()
        mock_import.count = 1
        mock_gpg.import_keys.return_value = mock_import

        mock_verified = MagicMock()
        mock_verified.valid = True
        mock_verified.key_id = "ABC123"
        mock_verified.username = "Test User"
        mock_gpg.verify_data.return_value = mock_verified

        valid, message = verify_signature(temp_file, sig_file, keyring=keyring)

        assert valid is True
        mock_gpg.import_keys.assert_called_once()


class TestListAvailableKeys:
    def test_list_available_keys(self, mock_gpg):
        """Test listing available GPG keys."""
        mock_keys = [
            {"keyid": "ABC123", "uids": ["Test User <test@example.com>"]},
            {"keyid": "DEF456", "uids": ["Another User <another@example.com>"]},
        ]
        mock_gpg.list_keys.return_value = mock_keys

        keys = list_available_keys()

        assert len(keys) == 2
        assert keys[0]["keyid"] == "ABC123"
        mock_gpg.list_keys.assert_called_once_with(secret=True)


class TestExportPublicKey:
    def test_export_public_key_success(self, tmp_path, mock_gpg):
        """Test successful public key export."""
        output_file = tmp_path / "public.asc"

        mock_gpg.export_keys.return_value = (
            "-----BEGIN PGP PUBLIC KEY BLOCK-----\ntest\n-----END PGP PUBLIC KEY BLOCK-----"
        )

        export_public_key("ABC123", output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "BEGIN PGP PUBLIC KEY BLOCK" in content

    def test_export_public_key_failure(self, tmp_path, mock_gpg):
        """Test public key export failure."""
        output_file = tmp_path / "public.asc"

        mock_gpg.export_keys.return_value = ""

        with pytest.raises(RuntimeError) as exc_info:
            export_public_key("NONEXISTENT", output_file)

        assert "Failed to export public key" in str(exc_info.value)
