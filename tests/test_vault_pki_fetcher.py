"""
Tests for Vault PKI fetcher.

Tests for:
- Basic PKI issuer certificate fetching
- Default and custom issuer references
- Token authentication
- Namespace support (Vault Enterprise)
- Error handling (missing issuer, auth errors)
"""

from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest

from bundlecraft.fetchers.vault_pki import fetch_vault_pki


def create_mock_vault_client():
    """Create a mock Vault client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "-----BEGIN CERTIFICATE-----\nISSUER_CERT\n-----END CERTIFICATE-----"
    mock_client.adapter.get = Mock(return_value=mock_response)
    return mock_client


class TestVaultPKIFetcherBasic:
    """Test basic Vault PKI fetching functionality."""

    def test_fetch_vault_pki_basic(self, tmp_path, monkeypatch):
        """Test basic Vault PKI issuer certificate fetch."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki(
                dest_dir=tmp_path,
                name="issuer-cert",
                mount_point="pki",
            )

            assert result.exists()
            assert result.name == "issuer-cert.pem"
            content = result.read_text()
            assert "ISSUER_CERT" in content

            # Verify correct endpoint was called
            mock_client.adapter.get.assert_called_once_with("/v1/pki/issuer/default/pem")

    def test_fetch_vault_pki_custom_issuer(self, tmp_path, monkeypatch):
        """Test fetching specific issuer by name."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            fetch_vault_pki(
                dest_dir=tmp_path,
                name="root-ca",
                mount_point="pki_root",
                issuer_ref="root-2024",
            )

            # Verify correct endpoint with custom issuer was called
            mock_client.adapter.get.assert_called_once_with("/v1/pki_root/issuer/root-2024/pem")

    def test_fetch_vault_pki_with_pem_extension(self, tmp_path, monkeypatch):
        """Test that .pem extension is not duplicated."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki(
                dest_dir=tmp_path,
                name="issuer-cert.pem",
                mount_point="pki",
            )

            assert result.name == "issuer-cert.pem"


class TestVaultPKIFetcherAuthentication:
    """Test Vault PKI authentication."""

    def test_fetch_with_custom_token_ref(self, tmp_path, monkeypatch):
        """Test Vault PKI with custom token environment variable."""
        monkeypatch.setenv("CUSTOM_VAULT_TOKEN", "hvs.custom_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
                token_ref="CUSTOM_VAULT_TOKEN",
            )

            # Verify client was created with correct token
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["token"] == "hvs.custom_token"

    def test_fetch_missing_token(self, tmp_path, monkeypatch):
        """Test that missing token raises error."""
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        with pytest.raises(click.ClickException, match="Vault token not found"):
            fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
            )

    def test_fetch_missing_addr(self, tmp_path, monkeypatch):
        """Test that missing Vault address raises error."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.delenv("VAULT_ADDR", raising=False)

        with pytest.raises(click.ClickException, match="Vault address is required"):
            fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
            )

    def test_fetch_with_explicit_addr(self, tmp_path, monkeypatch):
        """Test Vault PKI with explicit address in config."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        # Don't set VAULT_ADDR in environment

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
                addr="https://custom-vault.example.com:8200",
            )

            # Verify client was created with explicit address
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["url"] == "https://custom-vault.example.com:8200"


class TestVaultPKIFetcherNamespace:
    """Test Vault Enterprise namespace support."""

    def test_fetch_with_namespace(self, tmp_path, monkeypatch):
        """Test Vault PKI with namespace (Enterprise feature)."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
                namespace="admin/prod",
            )

            # Verify namespace was passed to client
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["namespace"] == "admin/prod"


class TestVaultPKIFetcherVerification:
    """Test Vault PKI TLS verification options."""

    def test_fetch_with_custom_ca_file(self, tmp_path, monkeypatch):
        """Test Vault PKI with custom CA certificate."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = create_mock_vault_client()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
                verify={"ca_file": "/path/to/vault-ca.pem"},
            )

            # Verify custom CA was passed to client
            call_kwargs = mock_hvac.Client.call_args[1]
            assert call_kwargs["verify"] == "/path/to/vault-ca.pem"


class TestVaultPKIFetcherErrors:
    """Test Vault PKI error handling."""

    def test_fetch_issuer_not_found(self, tmp_path, monkeypatch):
        """Test handling of missing issuer."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = Mock()

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.exceptions.InvalidPath = Exception
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            # Simulate InvalidPath exception
            mock_client.adapter.get.side_effect = Exception("404 Not Found")

            with pytest.raises(click.ClickException, match="Failed to fetch from Vault PKI"):
                fetch_vault_pki(
                    dest_dir=tmp_path,
                    name="test",
                    mount_point="pki",
                    issuer_ref="nonexistent",
                )

    def test_fetch_empty_certificate(self, tmp_path, monkeypatch):
        """Test handling of empty certificate response."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = ""
        mock_client.adapter.get = Mock(return_value=mock_response)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            with pytest.raises(click.ClickException, match="empty certificate"):
                fetch_vault_pki(
                    dest_dir=tmp_path,
                    name="test",
                    mount_point="pki",
                )

    def test_import_hvac_missing(self, tmp_path, monkeypatch):
        """Test that missing hvac raises helpful error."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_import.side_effect = click.ClickException(
                "Vault PKI fetcher requires 'hvac' package"
            )

            with pytest.raises(click.ClickException, match="hvac"):
                fetch_vault_pki(
                    dest_dir=tmp_path,
                    name="test",
                    mount_point="pki",
                )


class TestVaultPKIFetcherContentHandling:
    """Test Vault PKI certificate content handling."""

    def test_fetch_adds_trailing_newline(self, tmp_path, monkeypatch):
        """Test that certificate without trailing newline gets one added."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = Mock()
        mock_response = Mock()
        # Certificate without trailing newline
        mock_response.text = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        mock_client.adapter.get = Mock(return_value=mock_response)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
            )

            content = result.read_text()
            assert content.endswith("\n")

    def test_fetch_preserves_trailing_newline(self, tmp_path, monkeypatch):
        """Test that certificate with trailing newline keeps it."""
        monkeypatch.setenv("VAULT_TOKEN", "hvs.test_token")
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")

        mock_client = Mock()
        mock_response = Mock()
        # Certificate with trailing newline
        mock_response.text = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
        mock_client.adapter.get = Mock(return_value=mock_response)

        with patch("bundlecraft.fetchers.vault_pki._import_hvac") as mock_import:
            mock_hvac = Mock()
            mock_hvac.Client.return_value = mock_client
            mock_import.return_value = mock_hvac

            result = fetch_vault_pki(
                dest_dir=tmp_path,
                name="test",
                mount_point="pki",
            )

            content = result.read_text()
            # Should have exactly one trailing newline
            assert content.endswith("\n")
            assert not content.endswith("\n\n")
