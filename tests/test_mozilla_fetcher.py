"""
Tests for Mozilla root store fetcher.

Tests for:
- Basic Mozilla CA bundle fetching
- Default naming
- Verification options
- Delegation to URL fetcher
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bundlecraft.fetchers.mozilla import MOZILLA_CA_BUNDLE_URL, fetch_mozilla


class TestMozillaFetcher:
    """Test Mozilla root store fetcher."""

    def test_fetch_mozilla_basic(self, tmp_path):
        """Test basic Mozilla CA bundle fetch."""
        mock_path = tmp_path / "mozilla-roots.pem"

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path
            mock_path.write_text("-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----")

            result = fetch_mozilla(
                dest_dir=tmp_path,
            )

            assert result == mock_path
            # Verify fetch_url was called with Mozilla URL
            call_args = mock_fetch_url.call_args
            assert call_args[0][0] == MOZILLA_CA_BUNDLE_URL
            assert call_args[1]["name"] == "mozilla-roots"

    def test_fetch_mozilla_custom_name(self, tmp_path):
        """Test Mozilla fetch with custom name."""
        mock_path = tmp_path / "custom-name.pem"

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path

            fetch_mozilla(
                dest_dir=tmp_path,
                name="custom-name",
            )

            # Verify custom name was passed
            call_args = mock_fetch_url.call_args
            assert call_args[1]["name"] == "custom-name"

    def test_fetch_mozilla_with_verification(self, tmp_path):
        """Test Mozilla fetch with SHA256 verification."""
        mock_path = tmp_path / "mozilla-roots.pem"

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path

            verify_config = {"sha256": "abc123def456"}
            fetch_mozilla(
                dest_dir=tmp_path,
                verify=verify_config,
            )

            # Verify verification config was passed
            call_args = mock_fetch_url.call_args
            assert call_args[1]["verify"] == verify_config

    def test_fetch_mozilla_with_timeout(self, tmp_path):
        """Test Mozilla fetch with custom timeout."""
        mock_path = tmp_path / "mozilla-roots.pem"

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path

            fetch_mozilla(
                dest_dir=tmp_path,
                timeout=60,
            )

            # Verify timeout was passed
            call_args = mock_fetch_url.call_args
            assert call_args[1]["timeout"] == 60

    def test_fetch_mozilla_with_retries(self, tmp_path):
        """Test Mozilla fetch with custom retry configuration."""
        mock_path = tmp_path / "mozilla-roots.pem"

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path

            fetch_mozilla(
                dest_dir=tmp_path,
                retries=5,
                backoff_factor=3.0,
                retry_on_status=[429, 503],
            )

            # Verify retry config was passed
            call_args = mock_fetch_url.call_args
            assert call_args[1]["retries"] == 5
            assert call_args[1]["backoff_factor"] == 3.0
            assert call_args[1]["retry_on_status"] == [429, 503]

    def test_mozilla_url_constant(self):
        """Test that Mozilla URL constant is correct."""
        assert MOZILLA_CA_BUNDLE_URL == "https://curl.se/ca/cacert.pem"

    def test_fetch_mozilla_passes_root(self, tmp_path):
        """Test that root path is passed to fetch_url."""
        mock_path = tmp_path / "mozilla-roots.pem"
        root_path = Path("/custom/root")

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path

            fetch_mozilla(
                dest_dir=tmp_path,
                root=root_path,
            )

            # Verify root was passed
            call_args = mock_fetch_url.call_args
            assert call_args[1]["root"] == root_path

    def test_fetch_mozilla_passes_defaults(self, tmp_path):
        """Test that defaults config is passed to fetch_url."""
        mock_path = tmp_path / "mozilla-roots.pem"
        defaults = {"fetch": {"timeout": 45, "retries": 4}}

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch_url:
            mock_fetch_url.return_value = mock_path

            fetch_mozilla(
                dest_dir=tmp_path,
                defaults=defaults,
            )

            # Verify defaults were passed
            call_args = mock_fetch_url.call_args
            assert call_args[1]["defaults"] == defaults
