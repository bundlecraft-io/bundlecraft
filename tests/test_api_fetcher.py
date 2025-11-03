"""
Comprehensive tests for API fetcher to improve coverage from 18% to 70%+.

Tests for:
- HTTPS requirement enforcement
- Bearer token authentication
- Header customization
- TLS fingerprint verification
- Timeout and retry configuration
- Error handling (network, auth, validation)
- Different response formats
"""

import urllib.error
import urllib.request
from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from bundlecraft.fetchers.api import _tls_leaf_fingerprint_sha256, fetch_api


def create_mock_response(data: bytes) -> Mock:
    """Create a mock response object that supports context manager protocol."""
    mock_response = Mock()
    mock_response.read.return_value = data
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    return mock_response


class TestAPIFetcherHTTPS:
    """Test HTTPS enforcement."""

    def test_requires_https_endpoint(self, tmp_path):
        """Test that HTTP endpoints are rejected."""
        with pytest.raises((click.ClickException, ValueError), match="HTTPS"):
            fetch_api(
                endpoint="http://insecure.example.com/api/certs",
                dest_dir=tmp_path,
                name="test",
            )

    def test_accepts_https_endpoint(self, tmp_path):
        """Test that HTTPS endpoints are accepted."""
        mock_response = create_mock_response(
            b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
        )

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://secure.example.com/api/certs",
                dest_dir=tmp_path,
                name="test",
                timeout=5,
            )

            assert result.exists()
            assert result.suffix == ".pem"


class TestAPIFetcherAuthentication:
    """Test bearer token authentication."""

    def test_uses_token_from_environment(self, tmp_path, monkeypatch):
        """Test that token is read from environment variable."""
        test_token = "secret_api_token_12345"
        monkeypatch.setenv("TEST_API_TOKEN", test_token)

        mock_response = create_mock_response(b"CERT DATA")

        captured_request = None

        def mock_urlopen(request, *args, **kwargs):
            nonlocal captured_request
            captured_request = request
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                token_ref="TEST_API_TOKEN",
                timeout=5,
            )

            # Verify Authorization header was set
            assert captured_request is not None
            assert "Authorization" in captured_request.headers
            assert f"Bearer {test_token}" in captured_request.headers["Authorization"]

    def test_fails_when_token_missing(self, tmp_path, monkeypatch):
        """Test that missing token environment variable raises error."""
        # Ensure the env var is not set
        monkeypatch.delenv("MISSING_TOKEN", raising=False)

        with pytest.raises(
            (click.ClickException, KeyError, ValueError), match="Missing API token|not set"
        ):
            fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                token_ref="MISSING_TOKEN",
            )

    def test_works_without_token(self, tmp_path):
        """Test that API fetch works without authentication."""
        mock_response = create_mock_response(b"PUBLIC CERT DATA")

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://api.example.com/public/certs",
                dest_dir=tmp_path,
                name="test",
                token_ref=None,
                timeout=5,
            )

            assert result.exists()


class TestAPIFetcherHeaders:
    """Test custom header handling."""

    def test_default_accept_header(self, tmp_path):
        """Test that default Accept header is set."""
        mock_response = create_mock_response(b"CERT")

        captured_request = None

        def mock_urlopen(request, *args, **kwargs):
            nonlocal captured_request
            captured_request = request
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                timeout=5,
            )

            assert "Accept" in captured_request.headers

    def test_custom_headers(self, tmp_path):
        """Test that custom headers are included."""
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "X-API-Version": "v2",
        }

        mock_response = create_mock_response(b"CERT")

        captured_request = None

        def mock_urlopen(request, *args, **kwargs):
            nonlocal captured_request
            captured_request = request
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                headers=custom_headers,
                timeout=5,
            )

            # Headers are case-insensitive, so check with lowercase
            for key, value in custom_headers.items():
                # Headers may be normalized to different cases
                header_found = any(k.lower() == key.lower() for k in captured_request.headers)
                assert header_found, f"Header {key} not found in request"
                # Get the actual key used in the request
                actual_key = next(k for k in captured_request.headers if k.lower() == key.lower())
                assert captured_request.headers[actual_key] == value


class TestAPIFetcherTLSVerification:
    """Test TLS fingerprint verification."""

    def test_tls_fingerprint_extraction(self):
        """Test that TLS fingerprint can be extracted (unit test with mock)."""
        # Mock socket and SSL context
        mock_cert_der = b"MOCK_CERT_DER_DATA"

        with patch("socket.create_connection"):
            with patch("ssl.create_default_context") as mock_ssl_ctx:
                mock_ssock = Mock()
                mock_ssock.getpeercert.return_value = mock_cert_der

                # Create a proper context manager mock
                mock_wrapped_socket = MagicMock()
                mock_wrapped_socket.__enter__.return_value = mock_ssock
                mock_wrapped_socket.__exit__.return_value = False

                mock_ctx = Mock()
                mock_ctx.wrap_socket.return_value = mock_wrapped_socket
                mock_ssl_ctx.return_value = mock_ctx

                fingerprint = _tls_leaf_fingerprint_sha256("example.com", 443)

                assert isinstance(fingerprint, str)
                assert len(fingerprint) == 64  # SHA256 hex length

    def test_verify_tls_fingerprint_match(self, tmp_path, monkeypatch):
        """Test successful verification when fingerprint matches."""
        expected_fingerprint = "a" * 64  # Mock SHA256 hash

        mock_response = create_mock_response(b"CERT DATA")

        with patch("urllib.request.urlopen", return_value=mock_response):
            with patch(
                "bundlecraft.fetchers.api._tls_leaf_fingerprint_sha256",
                return_value=expected_fingerprint,
            ):
                result = fetch_api(
                    endpoint="https://api.example.com/certs",
                    dest_dir=tmp_path,
                    name="test",
                    verify={"tls_fingerprint_sha256": expected_fingerprint},
                    timeout=5,
                )

                assert result.exists()

    def test_verify_tls_fingerprint_mismatch(self, tmp_path):
        """Test error when TLS fingerprint doesn't match."""
        expected_fingerprint = "a" * 64
        actual_fingerprint = "b" * 64

        # Note: fingerprint check happens before the actual fetch, so we don't need to mock urlopen
        with patch(
            "bundlecraft.fetchers.api._tls_leaf_fingerprint_sha256",
            return_value=actual_fingerprint,
        ):
            with pytest.raises(
                (click.ClickException, ValueError), match="fingerprint|mismatch|TLS"
            ):
                fetch_api(
                    endpoint="https://api.example.com/certs",
                    dest_dir=tmp_path,
                    name="test",
                    verify={"tls_fingerprint_sha256": expected_fingerprint},
                    timeout=5,
                )


class TestAPIFetcherRetryLogic:
    """Test retry and timeout configuration."""

    def test_respects_timeout_setting(self, tmp_path):
        """Test that custom timeout is used."""
        mock_response = create_mock_response(b"CERT")

        captured_timeout = None

        def mock_urlopen(request, timeout=None, *args, **kwargs):
            nonlocal captured_timeout
            captured_timeout = timeout
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                timeout=30,
            )

            assert captured_timeout == 30

    def test_retries_on_transient_errors(self, tmp_path):
        """Test that transient errors trigger retries."""
        attempt_count = [0]

        def mock_urlopen(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise urllib.error.URLError("Temporary network error")
            return create_mock_response(b"CERT")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            result = fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                retries=3,
                timeout=5,
            )

            assert result.exists()
            assert attempt_count[0] == 3  # Should have retried twice


class TestAPIFetcherErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_404_not_found(self, tmp_path):
        """Test handling of 404 errors."""

        def mock_urlopen(*args, **kwargs):
            raise urllib.error.HTTPError(
                "https://api.example.com/certs", 404, "Not Found", {}, None
            )

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises((urllib.error.HTTPError, click.ClickException)):
                fetch_api(
                    endpoint="https://api.example.com/certs",
                    dest_dir=tmp_path,
                    name="test",
                    timeout=5,
                )

    def test_handles_401_unauthorized(self, tmp_path, monkeypatch):
        """Test handling of authentication errors."""
        monkeypatch.setenv("API_TOKEN", "invalid_token")

        def mock_urlopen(*args, **kwargs):
            raise urllib.error.HTTPError(
                "https://api.example.com/certs", 401, "Unauthorized", {}, None
            )

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises((urllib.error.HTTPError, click.ClickException)):
                fetch_api(
                    endpoint="https://api.example.com/certs",
                    dest_dir=tmp_path,
                    name="test",
                    token_ref="API_TOKEN",
                    timeout=5,
                )

    def test_handles_network_timeout(self, tmp_path):
        """Test handling of network timeouts."""

        def mock_urlopen(*args, **kwargs):
            raise urllib.error.URLError("Connection timed out")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises((urllib.error.URLError, click.ClickException)):
                fetch_api(
                    endpoint="https://api.example.com/certs",
                    dest_dir=tmp_path,
                    name="test",
                    timeout=1,
                    retries=0,  # Don't retry for this test
                )

    def test_handles_empty_response(self, tmp_path):
        """Test handling of empty API responses."""
        mock_response = create_mock_response(b"")

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                timeout=5,
            )

            # File should be created but empty
            assert result.exists()
            assert result.stat().st_size == 0

    def test_creates_destination_directory(self, tmp_path):
        """Test that destination directory is created if it doesn't exist."""
        dest_dir = tmp_path / "nested" / "path" / "to" / "certs"

        mock_response = create_mock_response(b"CERT")

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=dest_dir,
                name="test",
                timeout=5,
            )

            assert dest_dir.exists()
            assert result.parent == dest_dir


class TestAPIFetcherOutputFormats:
    """Test handling of different output formats."""

    def test_appends_pem_extension(self, tmp_path):
        """Test that .pem extension is added if missing."""
        mock_response = create_mock_response(b"CERT")

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="mycert",  # No extension
                timeout=5,
            )

            assert result.name == "mycert.pem"

    def test_preserves_pem_extension(self, tmp_path):
        """Test that existing .pem extension is preserved."""
        mock_response = create_mock_response(b"CERT")

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="mycert.pem",
                timeout=5,
            )

            assert result.name == "mycert.pem"
            # Should not become mycert.pem.pem

    def test_handles_binary_response(self, tmp_path):
        """Test handling of binary certificate data."""
        # DER-encoded certificate (binary)
        binary_cert = b"\x30\x82\x03\x48\x30\x82\x02\x30"

        mock_response = create_mock_response(binary_cert)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_api(
                endpoint="https://api.example.com/certs",
                dest_dir=tmp_path,
                name="test",
                timeout=5,
            )

            assert result.exists()
            assert result.read_bytes() == binary_cert
