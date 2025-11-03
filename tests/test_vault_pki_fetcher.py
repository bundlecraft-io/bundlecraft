"""
Comprehensive tests for Vault PKI Issuer fetcher.

Tests for:
- Basic certificate fetching from PKI issuer endpoint
- Unauthenticated access (documented behavior)
- Optional token-based authentication
- Mount point and issuer reference configuration
- TLS verification with custom CA certificates
- Vault namespace support (Enterprise feature)
- Timeout and retry configuration
- Error handling (network, auth, validation)
- Response validation
- Fetch config defaults (timeout, retries, backoff_factor, retry_on_status)
"""

import urllib.error
from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from bundlecraft.fetchers.vault_pki import fetch_vault_pki_issuer


def create_mock_hvac_client(cert_data: str = None):
    """Create a mock hvac client with proper response structure."""
    if cert_data is None:
        cert_data = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"

    mock_client = Mock()
    mock_adapter = Mock()
    mock_response = Mock()
    mock_response.text = cert_data
    mock_response.raise_for_status = Mock()
    mock_adapter.get.return_value = mock_response
    mock_client.adapter = mock_adapter
    return mock_client


class TestVaultPKIBasicFunctionality:
    """Test basic Vault PKI Issuer fetching functionality."""

    def test_fetch_default_issuer_success(self, tmp_path, monkeypatch):
        """Test fetching certificate from default PKI issuer."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        cert_pem = "-----BEGIN CERTIFICATE-----\nMIICert\n-----END CERTIFICATE-----"
        mock_client = create_mock_hvac_client(cert_pem)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test_cert",
                mount_point="pki",
                issuer_ref="default",
            )

            assert result.exists()
            assert result.suffix == ".pem"
            assert cert_pem in result.read_text()
            mock_adapter = mock_client.adapter
            mock_adapter.get.assert_called_once()
            call_args = mock_adapter.get.call_args
            assert "/v1/pki/issuer/default/pem" in call_args[0][0]

    def test_fetch_custom_mount_and_issuer(self, tmp_path, monkeypatch):
        """Test fetching from custom mount point and issuer reference."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        cert_pem = "-----BEGIN CERTIFICATE-----\nCustomIssuer\n-----END CERTIFICATE-----"
        mock_client = create_mock_hvac_client(cert_pem)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="custom_cert",
                mount_point="pki_int",
                issuer_ref="issuer-2023",
            )

            assert result.exists()
            mock_adapter = mock_client.adapter
            call_args = mock_adapter.get.call_args
            assert "/v1/pki_int/issuer/issuer-2023/pem" in call_args[0][0]

    def test_appends_pem_extension(self, tmp_path, monkeypatch):
        """Test that .pem extension is added if missing."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="mycert",  # No extension
            )

            assert result.name == "mycert.pem"

    def test_preserves_pem_extension(self, tmp_path, monkeypatch):
        """Test that existing .pem extension is preserved."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="mycert.pem",
            )

            assert result.name == "mycert.pem"


class TestVaultPKIAuthentication:
    """Test authentication options for Vault PKI Issuer."""

    def test_unauthenticated_access(self, tmp_path, monkeypatch):
        """Test unauthenticated access to PKI issuer endpoint (documented behavior)."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                token_ref=None,  # No authentication
            )

            assert result.exists()
            # Verify client was created with token=None
            mock_hvac.Client.assert_called_once()
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["token"] is None

    def test_optional_token_authentication(self, tmp_path, monkeypatch):
        """Test optional token-based authentication."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token_12345")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                token_ref="VAULT_TOKEN",
            )

            assert result.exists()
            # Verify client was created with the token
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["token"] == "hvs.test_token_12345"

    def test_missing_token_warning(self, tmp_path, monkeypatch, capsys):
        """Test that missing token generates warning but doesn't fail."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")
        # Ensure token env var is not set
        monkeypatch.delenv("VAULT_TOKEN", raising=False)

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                token_ref="VAULT_TOKEN",
            )

            assert result.exists()
            # Check that warning was printed
            captured = capsys.readouterr()
            assert "Token not found" in captured.err or "unauthenticated" in captured.err


class TestVaultPKIConfiguration:
    """Test configuration options for Vault PKI Issuer."""

    def test_vault_addr_from_config(self, tmp_path):
        """Test that Vault address can be specified in config."""
        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                addr="https://custom-vault.example.com:8200",
            )

            assert result.exists()
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["url"] == "https://custom-vault.example.com:8200"

    def test_vault_addr_from_env(self, tmp_path, monkeypatch):
        """Test that Vault address is read from VAULT_ADDR environment variable."""
        monkeypatch.setenv("VAULT_ADDR", "https://env-vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
            )

            assert result.exists()
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["url"] == "https://env-vault.example.com:8200"

    def test_vault_addr_required(self, tmp_path, monkeypatch):
        """Test that Vault address is required."""
        # Ensure VAULT_ADDR is not set
        monkeypatch.delenv("VAULT_ADDR", raising=False)

        with pytest.raises(click.ClickException, match="address is required"):
            fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                addr=None,
            )

    def test_custom_ca_verification(self, tmp_path, monkeypatch):
        """Test TLS verification with custom CA certificate."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                verify={"ca_file": "/path/to/custom-ca.pem"},
            )

            assert result.exists()
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["verify"] == "/path/to/custom-ca.pem"

    def test_vault_namespace_support(self, tmp_path, monkeypatch):
        """Test Vault namespace support (Enterprise feature)."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                namespace="production",
            )

            assert result.exists()
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["namespace"] == "production"


class TestVaultPKIRetryLogic:
    """Test retry and timeout configuration."""

    def test_respects_timeout_setting(self, tmp_path, monkeypatch):
        """Test that custom timeout is used."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        captured_timeout = None

        def mock_get(path, timeout=None):
            nonlocal captured_timeout
            captured_timeout = timeout
            response = Mock()
            response.text = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
            response.raise_for_status = Mock()
            return response

        mock_client = Mock()
        mock_adapter = Mock()
        mock_adapter.get = mock_get
        mock_client.adapter = mock_adapter

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                timeout=45,
            )

            assert result.exists()
            assert captured_timeout == 45

    def test_respects_retry_settings(self, tmp_path, monkeypatch):
        """Test that retry configuration is used."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        attempt_count = [0]

        def mock_get(path, timeout=None):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Temporary error")
            response = Mock()
            response.text = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
            response.raise_for_status = Mock()
            return response

        mock_client = Mock()
        mock_adapter = Mock()
        mock_adapter.get = mock_get
        mock_client.adapter = mock_adapter

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                retries=3,
                backoff_factor=0.1,  # Minimal backoff for testing
            )

            assert result.exists()
            assert attempt_count[0] == 3  # Should have retried twice

    def test_uses_fetch_defaults(self, tmp_path, monkeypatch):
        """Test that fetch defaults are applied."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            defaults = {
                "fetch": {
                    "timeout": 60,
                    "retries": 5,
                    "backoff_factor": 3.0,
                    "retry_on_status": [502, 503],
                }
            }

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
                defaults=defaults,
            )

            assert result.exists()


class TestVaultPKIErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_empty_response(self, tmp_path, monkeypatch):
        """Test handling of empty certificate response."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client("")  # Empty response

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            with pytest.raises(click.ClickException, match="empty certificate"):
                fetch_vault_pki_issuer(
                    dest_dir=tmp_path,
                    name="test",
                )

    def test_handles_http_error(self, tmp_path, monkeypatch):
        """Test handling of HTTP errors from Vault."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        def mock_get(path, timeout=None):
            response = Mock()
            response.raise_for_status.side_effect = Exception("404 Not Found")
            return response

        mock_client = Mock()
        mock_adapter = Mock()
        mock_adapter.get = mock_get
        mock_client.adapter = mock_adapter

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            with pytest.raises(click.ClickException, match="Failed to fetch"):
                fetch_vault_pki_issuer(
                    dest_dir=tmp_path,
                    name="test",
                    retries=0,
                )

    def test_handles_network_timeout(self, tmp_path, monkeypatch):
        """Test handling of network timeouts."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        def mock_get(path, timeout=None):
            raise TimeoutError("Connection timed out")

        mock_client = Mock()
        mock_adapter = Mock()
        mock_adapter.get = mock_get
        mock_client.adapter = mock_adapter

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            with pytest.raises((TimeoutError, click.ClickException)):
                fetch_vault_pki_issuer(
                    dest_dir=tmp_path,
                    name="test",
                    timeout=1,
                    retries=0,
                )

    def test_creates_destination_directory(self, tmp_path, monkeypatch):
        """Test that destination directory is created if it doesn't exist."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        dest_dir = tmp_path / "nested" / "path" / "to" / "certs"

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=dest_dir,
                name="test",
            )

            assert dest_dir.exists()
            assert result.parent == dest_dir

    def test_hvac_import_error(self, tmp_path, monkeypatch):
        """Test error when hvac package is not installed."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_import.side_effect = click.ClickException("hvac package required")

            with pytest.raises(click.ClickException, match="hvac"):
                fetch_vault_pki_issuer(
                    dest_dir=tmp_path,
                    name="test",
                )


class TestVaultPKIResponseValidation:
    """Test validation of certificate responses."""

    def test_validates_pem_format(self, tmp_path, monkeypatch):
        """Test that valid PEM data is accepted."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        valid_pem = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL0UG+mRKSzMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
-----END CERTIFICATE-----"""

        mock_client = create_mock_hvac_client(valid_pem)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
            )

            assert result.exists()
            content = result.read_text()
            assert "BEGIN CERTIFICATE" in content
            assert content.endswith("\n")  # Ensure trailing newline

    def test_adds_trailing_newline(self, tmp_path, monkeypatch):
        """Test that trailing newline is added if missing."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        # PEM without trailing newline
        pem_no_newline = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"

        mock_client = create_mock_hvac_client(pem_no_newline)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="test",
            )

            content = result.read_text()
            assert content.endswith("\n")


class TestVaultPKIProvenance:
    """Test that provenance recording works correctly."""

    def test_returns_correct_path(self, tmp_path, monkeypatch):
        """Test that the correct output path is returned for provenance."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_hvac_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki_issuer(
                dest_dir=tmp_path,
                name="provenance_test",
            )

            # Verify path is correct for provenance recording
            assert result.parent == tmp_path
            assert result.name == "provenance_test.pem"
            assert result.exists()
            assert result.is_file()
