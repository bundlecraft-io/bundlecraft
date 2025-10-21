"""Integration test demonstrating retry functionality with mock server."""

import urllib.error
from unittest.mock import Mock, patch

import pytest

from bundlecraft.fetchers.http import fetch_url


class TestRetryIntegration:
    """Integration tests demonstrating retry behavior with simulated failures."""

    def test_fetch_succeeds_after_transient_failures(self, tmp_path):
        """Test that fetch succeeds after retrying transient HTTP 503 errors."""
        dest_dir = tmp_path / "fetched"
        dest_dir.mkdir()

        # Mock urlopen to fail twice with 503, then succeed
        call_count = 0

        def mock_urlopen(request, context=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise urllib.error.HTTPError(
                    request.full_url, 503, "Service Unavailable", {}, None
                )
            # Third attempt succeeds
            mock_response = Mock()
            mock_response.read.return_value = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            result = fetch_url(
                "https://example.com/cert.pem",
                dest_dir,
                name="test",
                retries=3,
                backoff_factor=1.1,  # Fast backoff for testing
            )

        assert result.exists()
        assert call_count == 3  # Failed twice, succeeded on third attempt
        assert result.read_text() == "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"

    def test_fetch_fails_after_exhausting_retries(self, tmp_path):
        """Test that fetch fails after exhausting all retry attempts."""
        dest_dir = tmp_path / "fetched"
        dest_dir.mkdir()

        # Mock urlopen to always fail with 503
        def mock_urlopen(request, context=None, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 503, "Service Unavailable", {}, None)

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                fetch_url(
                    "https://example.com/cert.pem",
                    dest_dir,
                    name="test",
                    retries=2,
                    backoff_factor=1.1,  # Fast backoff for testing
                )

        assert exc_info.value.code == 503

    def test_fetch_respects_custom_timeout(self, tmp_path):
        """Test that fetch respects custom timeout configuration."""
        dest_dir = tmp_path / "fetched"
        dest_dir.mkdir()

        # Mock urlopen to verify timeout is passed
        actual_timeout = None

        def mock_urlopen(request, context=None, timeout=None):
            nonlocal actual_timeout
            actual_timeout = timeout
            mock_response = Mock()
            mock_response.read.return_value = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            fetch_url(
                "https://example.com/cert.pem",
                dest_dir,
                name="test",
                timeout=90,
            )

        assert actual_timeout == 90

    def test_fetch_with_config_override(self, tmp_path):
        """Test that per-source config overrides defaults."""
        dest_dir = tmp_path / "fetched"
        dest_dir.mkdir()

        # Mock urlopen to fail with 408, which is not in default retry list
        call_count = 0

        def mock_urlopen(request, context=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError(request.full_url, 408, "Request Timeout", {}, None)
            mock_response = Mock()
            mock_response.read.return_value = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response

        # Default retry_on_status doesn't include 408, so first attempt should fail immediately
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                fetch_url(
                    "https://example.com/cert.pem",
                    dest_dir,
                    name="test",
                    retries=3,
                )
        assert exc_info.value.code == 408
        assert call_count == 1  # No retries for 408 by default

        # Reset counter
        call_count = 0

        # Now retry with custom retry_on_status that includes 408
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            result = fetch_url(
                "https://example.com/cert.pem",
                dest_dir,
                name="test2",
                retries=3,
                backoff_factor=1.1,
                retry_on_status=[408, 503],  # Include 408
            )

        assert result.exists()
        assert call_count == 2  # Failed once with 408, retried and succeeded

    def test_fetch_file_url_no_retry(self, tmp_path):
        """Test that file:// URLs don't trigger retry logic."""
        source_file = tmp_path / "source.pem"
        source_file.write_text("-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n")

        dest_dir = tmp_path / "fetched"
        dest_dir.mkdir()

        # File URLs should work without retry logic
        result = fetch_url(
            f"file://{source_file}",
            dest_dir,
            name="test",
            retries=0,  # No retries needed for local files
        )

        assert result.exists()
        assert result.read_text() == "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
