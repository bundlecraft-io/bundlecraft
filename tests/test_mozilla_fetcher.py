"""Tests for Mozilla CA Bundle fetcher."""

from pathlib import Path

from bundlecraft.fetchers.mozilla import MOZILLA_CA_BUNDLE_URL, fetch_mozilla


class TestMozillaFetcher:
    """Test the Mozilla CA Bundle fetcher."""

    def test_mozilla_url_hardcoded(self):
        """Test that Mozilla fetcher hardcodes the correct URL."""
        assert MOZILLA_CA_BUNDLE_URL == "https://curl.se/ca/cacert.pem"

    def test_mozilla_fetcher_signature(self):
        """Test that Mozilla fetcher has the expected function signature."""
        # Verify function accepts expected parameters
        import inspect

        sig = inspect.signature(fetch_mozilla)
        params = list(sig.parameters.keys())

        # Check for essential parameters
        assert "dest_dir" in params
        assert "name" in params
        assert "verify" in params
        assert "timeout" in params
        assert "retries" in params
        assert "backoff_factor" in params
        assert "retry_on_status" in params
        assert "defaults" in params

    def test_mozilla_default_name(self):
        """Test that Mozilla fetcher uses 'mozilla' as default name."""
        # We can't actually fetch without network, but we can verify the implementation
        # delegates to fetch_url with the correct URL
        from unittest.mock import patch

        dest_dir = Path("/tmp/test")
        verify_config = {"sha256": "abc123"}

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch:
            mock_fetch.return_value = dest_dir / "mozilla.pem"

            _ = fetch_mozilla(
                dest_dir=dest_dir,
                verify=verify_config,
                timeout=60,
                retries=5,
            )

            # Verify fetch_url was called with the correct parameters
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args

            # Check URL is hardcoded
            assert call_args.kwargs["url"] == MOZILLA_CA_BUNDLE_URL
            # Check default name is "mozilla"
            assert call_args.kwargs["name"] == "mozilla"
            # Check verify config is passed through
            assert call_args.kwargs["verify"] == verify_config
            # Check timeout/retries are passed through
            assert call_args.kwargs["timeout"] == 60
            assert call_args.kwargs["retries"] == 5

    def test_mozilla_custom_name(self):
        """Test that Mozilla fetcher respects custom name parameter."""
        from unittest.mock import patch

        dest_dir = Path("/tmp/test")
        custom_name = "my-mozilla-bundle"

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch:
            mock_fetch.return_value = dest_dir / f"{custom_name}.pem"

            fetch_mozilla(
                dest_dir=dest_dir,
                name=custom_name,
            )

            # Verify custom name is passed through
            call_args = mock_fetch.call_args
            assert call_args.kwargs["name"] == custom_name

    def test_mozilla_respects_fetch_configs(self):
        """Test that Mozilla fetcher respects all fetch configuration parameters."""
        from unittest.mock import patch

        dest_dir = Path("/tmp/test")

        # Test all fetch config parameters
        test_params = {
            "timeout": 120,
            "retries": 10,
            "backoff_factor": 3.0,
            "retry_on_status": [500, 502, 503],
            "defaults": {"fetch": {"timeout": 30}},
        }

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch:
            mock_fetch.return_value = dest_dir / "mozilla.pem"

            fetch_mozilla(dest_dir=dest_dir, **test_params)

            # Verify all parameters are passed to fetch_url
            call_args = mock_fetch.call_args
            assert call_args.kwargs["timeout"] == 120
            assert call_args.kwargs["retries"] == 10
            assert call_args.kwargs["backoff_factor"] == 3.0
            assert call_args.kwargs["retry_on_status"] == [500, 502, 503]
            assert call_args.kwargs["defaults"] == {"fetch": {"timeout": 30}}

    def test_mozilla_with_verification(self):
        """Test that Mozilla fetcher supports verification options."""
        from unittest.mock import patch

        dest_dir = Path("/tmp/test")

        # Test verification options
        verify_config = {
            "sha256": "abc123def456",  # pragma: allowlist secret
            "ca_file": "custom-ca.pem",
            "tls_fingerprint_sha256": "fingerprint123",
        }

        with patch("bundlecraft.fetchers.mozilla.fetch_url") as mock_fetch:
            mock_fetch.return_value = dest_dir / "mozilla.pem"

            fetch_mozilla(dest_dir=dest_dir, verify=verify_config)

            # Verify verification config is passed through
            call_args = mock_fetch.call_args
            assert call_args.kwargs["verify"] == verify_config
