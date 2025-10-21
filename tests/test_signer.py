"""
Tests for bundlecraft.signer module.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bundlecraft.signer import (
    SignerConfig,
    SigningError,
    _check_gpg_available,
    _check_sigstore_available,
    sign_file,
    sign_file_gpg,
    verify_file,
    verify_file_gpg,
)


class TestSignerConfig:
    """Tests for SignerConfig class."""

    def test_default_config(self):
        """Test default SignerConfig initialization."""
        config = SignerConfig()
        assert config.method == "none"
        assert config.gpg_key_id is None
        assert config.gpg_passphrase is None
        assert config.gpg_home is None

    def test_config_with_params(self):
        """Test SignerConfig with custom parameters."""
        config = SignerConfig(
            method="gpg",
            gpg_key_id="test-key-id",
            gpg_passphrase="test-pass",
            gpg_home="/tmp/gpg",
        )
        assert config.method == "gpg"
        assert config.gpg_key_id == "test-key-id"
        assert config.gpg_passphrase == "test-pass"
        assert config.gpg_home == "/tmp/gpg"

    def test_from_env_default(self):
        """Test from_env with no environment variables."""
        # Clear relevant env vars
        env_backup = {}
        env_vars = [
            "BUNDLECRAFT_SIGN_METHOD",
            "BUNDLECRAFT_GPG_KEY_ID",
            "BUNDLECRAFT_GPG_PASSPHRASE",
            "BUNDLECRAFT_GPG_HOME",
        ]
        for var in env_vars:
            env_backup[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            config = SignerConfig.from_env()
            assert config.method == "none"
            assert config.gpg_key_id is None
        finally:
            # Restore env
            for var, val in env_backup.items():
                if val is not None:
                    os.environ[var] = val

    def test_from_env_with_vars(self):
        """Test from_env with environment variables set."""
        env_backup = {}
        env_vars = {
            "BUNDLECRAFT_SIGN_METHOD": "gpg",
            "BUNDLECRAFT_GPG_KEY_ID": "env-key-id",
            "BUNDLECRAFT_GPG_PASSPHRASE": "env-pass",
            "BUNDLECRAFT_GPG_HOME": "/env/gpg",
        }

        # Backup and set env vars
        for var, val in env_vars.items():
            env_backup[var] = os.environ.get(var)
            os.environ[var] = val

        try:
            config = SignerConfig.from_env()
            assert config.method == "gpg"
            assert config.gpg_key_id == "env-key-id"
            assert config.gpg_passphrase == "env-pass"
            assert config.gpg_home == "/env/gpg"
        finally:
            # Restore env
            for var, val in env_backup.items():
                if val is not None:
                    os.environ[var] = val
                elif var in os.environ:
                    del os.environ[var]

    def test_from_env_invalid_method(self):
        """Test from_env with invalid signing method."""
        env_backup = os.environ.get("BUNDLECRAFT_SIGN_METHOD")
        os.environ["BUNDLECRAFT_SIGN_METHOD"] = "invalid-method"

        try:
            config = SignerConfig.from_env()
            # Should default to "none" with invalid method
            assert config.method == "none"
        finally:
            if env_backup is not None:
                os.environ["BUNDLECRAFT_SIGN_METHOD"] = env_backup
            elif "BUNDLECRAFT_SIGN_METHOD" in os.environ:
                del os.environ["BUNDLECRAFT_SIGN_METHOD"]


class TestToolAvailability:
    """Tests for tool availability checks."""

    def test_check_gpg_available(self):
        """Test GPG availability check."""
        # This test depends on system state; just check it returns a boolean
        result = _check_gpg_available()
        assert isinstance(result, bool)

    def test_check_sigstore_available(self):
        """Test Sigstore availability check."""
        # This test depends on system state; just check it returns a boolean
        result = _check_sigstore_available()
        assert isinstance(result, bool)


class TestGPGSigning:
    """Tests for GPG signing functionality."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to sign."""
        file_path = tmp_path / "test-file.txt"
        file_path.write_text("Test content for signing\n")
        return file_path

    def test_sign_file_gpg_not_available(self, sample_file):
        """Test GPG signing when GPG is not available."""
        with patch("bundlecraft.signer._check_gpg_available", return_value=False):
            with pytest.raises(SigningError, match="GPG is not available"):
                sign_file_gpg(sample_file)

    def test_sign_file_gpg_file_not_found(self, tmp_path):
        """Test GPG signing with non-existent file."""
        with patch("bundlecraft.signer._check_gpg_available", return_value=True):
            non_existent = tmp_path / "does-not-exist.txt"
            with pytest.raises(SigningError, match="File not found"):
                sign_file_gpg(non_existent)

    @pytest.mark.skipif(not _check_gpg_available(), reason="GPG not available")
    def test_sign_file_gpg_success(self, sample_file, tmp_path):
        """Test successful GPG signing with a test key."""
        # Create a temporary GPG home with a test key
        gpg_home = tmp_path / "gpg-home"
        gpg_home.mkdir()

        # Generate a test GPG key (non-interactive)
        gen_key_cmd = [
            "gpg",
            "--homedir",
            str(gpg_home),
            "--batch",
            "--passphrase",
            "",
            "--quick-gen-key",
            "test@bundlecraft.test",
            "rsa2048",
            "default",
            "0",
        ]

        try:
            subprocess.run(
                gen_key_cmd,
                capture_output=True,
                timeout=30,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pytest.skip("Failed to generate test GPG key")

        # List keys to get key ID
        list_keys_cmd = [
            "gpg",
            "--homedir",
            str(gpg_home),
            "--list-keys",
            "--with-colons",
        ]
        result = subprocess.run(
            list_keys_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Extract key ID from output
        key_id = None
        for line in result.stdout.splitlines():
            if line.startswith("fpr:"):
                key_id = line.split(":")[9]
                break

        if not key_id:
            pytest.skip("Failed to get test GPG key ID")

        # Test signing
        sig_path = sign_file_gpg(
            sample_file,
            key_id=key_id,
            passphrase="",
            gpg_home=str(gpg_home),
        )

        assert sig_path.exists()
        assert sig_path.suffix == ".asc"
        assert sig_path.parent == sample_file.parent

    def test_verify_file_gpg_not_available(self, sample_file):
        """Test GPG verification when GPG is not available."""
        with patch("bundlecraft.signer._check_gpg_available", return_value=False):
            with pytest.raises(SigningError, match="GPG is not available"):
                verify_file_gpg(sample_file)

    def test_verify_file_gpg_file_not_found(self, tmp_path):
        """Test GPG verification with non-existent file."""
        with patch("bundlecraft.signer._check_gpg_available", return_value=True):
            non_existent = tmp_path / "does-not-exist.txt"
            with pytest.raises(SigningError, match="File not found"):
                verify_file_gpg(non_existent)

    def test_verify_file_gpg_signature_not_found(self, sample_file):
        """Test GPG verification when signature file is missing."""
        with patch("bundlecraft.signer._check_gpg_available", return_value=True):
            with pytest.raises(SigningError, match="No signature file found"):
                verify_file_gpg(sample_file)


class TestSigningIntegration:
    """Integration tests for signing functionality."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to sign."""
        file_path = tmp_path / "test-artifact.json"
        file_path.write_text('{"test": "data"}\n')
        return file_path

    def test_sign_file_no_method(self, sample_file):
        """Test signing with method set to 'none'."""
        config = SignerConfig(method="none")
        result = sign_file(sample_file, config)
        assert result is None

    def test_sign_file_invalid_method(self, sample_file):
        """Test signing with invalid method."""
        config = SignerConfig(method="invalid")  # type: ignore
        with pytest.raises(SigningError, match="Unsupported signing method"):
            sign_file(sample_file, config)

    def test_verify_file_no_signature(self, sample_file):
        """Test verification when no signature file exists."""
        result = verify_file(sample_file)
        assert result is False

    @pytest.mark.skipif(not _check_gpg_available(), reason="GPG not available")
    def test_sign_and_verify_gpg_roundtrip(self, sample_file, tmp_path):
        """Test complete sign and verify roundtrip with GPG."""
        # Create a temporary GPG home with a test key
        gpg_home = tmp_path / "gpg-home"
        gpg_home.mkdir()

        # Generate a test GPG key
        gen_key_cmd = [
            "gpg",
            "--homedir",
            str(gpg_home),
            "--batch",
            "--passphrase",
            "",
            "--quick-gen-key",
            "test@bundlecraft.test",
            "rsa2048",
            "default",
            "0",
        ]

        try:
            subprocess.run(
                gen_key_cmd,
                capture_output=True,
                timeout=30,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pytest.skip("Failed to generate test GPG key")

        # Get key ID
        list_keys_cmd = [
            "gpg",
            "--homedir",
            str(gpg_home),
            "--list-keys",
            "--with-colons",
        ]
        result = subprocess.run(
            list_keys_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        key_id = None
        for line in result.stdout.splitlines():
            if line.startswith("fpr:"):
                key_id = line.split(":")[9]
                break

        if not key_id:
            pytest.skip("Failed to get test GPG key ID")

        # Sign the file
        config = SignerConfig(
            method="gpg",
            gpg_key_id=key_id,
            gpg_passphrase="",
            gpg_home=str(gpg_home),
        )
        sig_path = sign_file(sample_file, config)

        assert sig_path is not None
        assert sig_path.exists()

        # Verify the signature
        is_valid = verify_file_gpg(sample_file, gpg_home=str(gpg_home))
        assert is_valid is True


class TestCLIHelpers:
    """Tests for CLI helper functions."""

    def test_signing_error_exception(self):
        """Test SigningError exception."""
        error = SigningError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
