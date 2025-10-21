"""Tests for retry and timeout configuration in fetch operations."""

import time
import urllib.error

import pytest

from bundlecraft.helpers.fetch_utils import (
    DEFAULT_FETCH_CONFIG,
    calculate_backoff,
    get_fetch_config,
    retry_with_backoff,
    should_retry_http_error,
)


class TestBackoffCalculation:
    """Test exponential backoff calculation."""

    def test_backoff_increases_exponentially(self):
        """Test that backoff delay increases exponentially with attempts."""
        delays = [calculate_backoff(i, backoff_factor=2.0) for i in range(4)]
        # Each delay should be roughly double the previous (within jitter range)
        # delay = 2^attempt with jitter [0.5x, 1.5x]
        assert 0.5 <= delays[0] <= 1.5  # 2^0 = 1
        assert 1.0 <= delays[1] <= 3.0  # 2^1 = 2
        assert 2.0 <= delays[2] <= 6.0  # 2^2 = 4
        assert 4.0 <= delays[3] <= 12.0  # 2^3 = 8

    def test_backoff_respects_max_delay(self):
        """Test that backoff delay never exceeds max_delay."""
        delay = calculate_backoff(100, backoff_factor=2.0, max_delay=10.0)
        assert delay <= 15.0  # max_delay * 1.5 (jitter upper bound)

    def test_backoff_with_different_factors(self):
        """Test backoff with different backoff factors."""
        delay_2x = calculate_backoff(3, backoff_factor=2.0)
        delay_3x = calculate_backoff(3, backoff_factor=3.0)
        # 3x factor should produce larger delays
        # 2^3 = 8, 3^3 = 27
        assert delay_3x > delay_2x

    def test_backoff_jitter_provides_randomness(self):
        """Test that jitter provides randomness between calls."""
        delays = [calculate_backoff(2, backoff_factor=2.0) for _ in range(10)]
        # All delays should be in valid range
        for delay in delays:
            assert 2.0 <= delay <= 6.0  # 2^2 = 4, jitter [0.5x, 1.5x]
        # Delays should not all be identical (randomness check)
        assert len(set(delays)) > 1


class TestRetryPredicate:
    """Test HTTP error retry predicate."""

    def test_retry_on_configured_status_codes(self):
        """Test that configured status codes trigger retry."""
        retry_codes = [429, 502, 503, 504]
        for code in retry_codes:
            error = urllib.error.HTTPError("", code, "", {}, None)
            assert should_retry_http_error(error, retry_codes)

    def test_no_retry_on_non_configured_codes(self):
        """Test that non-configured status codes don't trigger retry."""
        retry_codes = [429, 502, 503, 504]
        non_retry_codes = [400, 401, 403, 404, 500]
        for code in non_retry_codes:
            error = urllib.error.HTTPError("", code, "", {}, None)
            assert not should_retry_http_error(error, retry_codes)

    def test_retry_on_custom_status_codes(self):
        """Test retry with custom status code configuration."""
        custom_codes = [408, 500, 503]
        error_408 = urllib.error.HTTPError("", 408, "", {}, None)
        error_500 = urllib.error.HTTPError("", 500, "", {}, None)
        error_404 = urllib.error.HTTPError("", 404, "", {}, None)

        assert should_retry_http_error(error_408, custom_codes)
        assert should_retry_http_error(error_500, custom_codes)
        assert not should_retry_http_error(error_404, custom_codes)


class TestRetryDecorator:
    """Test retry_with_backoff decorator."""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retries."""
        call_count = 0

        @retry_with_backoff(retries=3)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_http_error_with_retry_status(self):
        """Test retry on HTTP errors with retryable status codes."""
        call_count = 0

        @retry_with_backoff(retries=3, backoff_factor=1.1, retry_on_status=[503])
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise urllib.error.HTTPError("", 503, "Service Unavailable", {}, None)
            return "success"

        result = fails_then_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_http_error_with_non_retry_status(self):
        """Test no retry on HTTP errors with non-retryable status codes."""
        call_count = 0

        @retry_with_backoff(retries=3, retry_on_status=[503])
        def fails_with_404():
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError("", 404, "Not Found", {}, None)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fails_with_404()

        assert exc_info.value.code == 404
        assert call_count == 1  # No retries

    def test_retry_on_url_error(self):
        """Test retry on URLError (network errors)."""
        call_count = 0

        @retry_with_backoff(retries=3, backoff_factor=1.1)
        def fails_with_network_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise urllib.error.URLError("Network unreachable")
            return "success"

        result = fails_with_network_error()
        assert result == "success"
        assert call_count == 2

    def test_retry_exhaustion_raises_last_error(self):
        """Test that exhausting retries raises the last error."""
        call_count = 0

        @retry_with_backoff(retries=2, backoff_factor=1.1, retry_on_status=[503])
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError("", 503, "Service Unavailable", {}, None)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            always_fails()

        assert exc_info.value.code == 503
        assert call_count == 3  # Initial attempt + 2 retries

    def test_retry_on_timeout_error(self):
        """Test retry on TimeoutError."""
        call_count = 0

        @retry_with_backoff(retries=2, backoff_factor=1.1)
        def fails_with_timeout():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Connection timed out")
            return "success"

        result = fails_with_timeout()
        assert result == "success"
        assert call_count == 2

    def test_non_retryable_exception_raised_immediately(self):
        """Test that non-retryable exceptions are raised immediately."""
        call_count = 0

        @retry_with_backoff(retries=3)
        def fails_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid value")

        with pytest.raises(ValueError):
            fails_with_value_error()

        assert call_count == 1  # No retries

    def test_backoff_timing(self):
        """Test that backoff delays are applied between retries."""
        call_times = []

        @retry_with_backoff(retries=2, backoff_factor=1.5, retry_on_status=[503])
        def fails_twice():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise urllib.error.HTTPError("", 503, "Service Unavailable", {}, None)
            return "success"

        result = fails_twice()
        assert result == "success"
        assert len(call_times) == 3

        # Check that there's a delay between attempts (at least 0.5s for first backoff)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay1 >= 0.5  # 1.5^0 * 0.5 (jitter min)
        assert delay2 >= 0.75  # 1.5^1 * 0.5 (jitter min)


class TestFetchConfig:
    """Test fetch configuration merging."""

    def test_default_config(self):
        """Test that default config is used when no overrides provided."""
        config = get_fetch_config()
        assert config == DEFAULT_FETCH_CONFIG

    def test_global_defaults_override_builtin(self):
        """Test that global defaults override built-in defaults."""
        defaults = {"fetch": {"timeout": 60, "retries": 5}}
        config = get_fetch_config(defaults=defaults)
        assert config["timeout"] == 60
        assert config["retries"] == 5
        assert config["backoff_factor"] == 2.0  # Not overridden
        assert config["retry_on_status"] == [429, 502, 503, 504]  # Not overridden

    def test_source_config_overrides_defaults(self):
        """Test that source-specific config overrides defaults."""
        defaults = {"fetch": {"timeout": 60, "retries": 5}}
        source_config = {"timeout": 120, "backoff_factor": 3.0}
        config = get_fetch_config(source_config=source_config, defaults=defaults)
        assert config["timeout"] == 120  # Source override
        assert config["retries"] == 5  # From global defaults
        assert config["backoff_factor"] == 3.0  # Source override
        assert config["retry_on_status"] == [429, 502, 503, 504]  # Built-in default

    def test_partial_source_config_override(self):
        """Test that partial source config only overrides specified fields."""
        source_config = {"timeout": 90}
        config = get_fetch_config(source_config=source_config)
        assert config["timeout"] == 90
        assert config["retries"] == 3  # Default
        assert config["backoff_factor"] == 2.0  # Default
        assert config["retry_on_status"] == [429, 502, 503, 504]  # Default

    def test_custom_retry_status_codes(self):
        """Test custom retry status codes configuration."""
        source_config = {"retry_on_status": [408, 500, 502]}
        config = get_fetch_config(source_config=source_config)
        assert config["retry_on_status"] == [408, 500, 502]

    def test_priority_order(self):
        """Test priority: source > global defaults > built-in defaults."""
        defaults = {
            "fetch": {
                "timeout": 45,
                "retries": 4,
                "backoff_factor": 2.5,
            }
        }
        source_config = {"timeout": 15}  # Only override timeout
        config = get_fetch_config(source_config=source_config, defaults=defaults)

        assert config["timeout"] == 15  # Source wins
        assert config["retries"] == 4  # Global default
        assert config["backoff_factor"] == 2.5  # Global default
        assert config["retry_on_status"] == [429, 502, 503, 504]  # Built-in default


class TestConfigSchema:
    """Test configuration schema validation."""

    def test_fetch_retry_config_defaults(self):
        """Test FetchRetryConfig with default values."""
        from bundlecraft.helpers.config_schema import FetchRetryConfig

        config = FetchRetryConfig()
        assert config.timeout == 30
        assert config.retries == 3
        assert config.backoff_factor == 2.0
        assert config.retry_on_status == [429, 502, 503, 504]

    def test_fetch_retry_config_custom_values(self):
        """Test FetchRetryConfig with custom values."""
        from bundlecraft.helpers.config_schema import FetchRetryConfig

        config = FetchRetryConfig(
            timeout=60, retries=5, backoff_factor=3.0, retry_on_status=[500, 502, 503]
        )
        assert config.timeout == 60
        assert config.retries == 5
        assert config.backoff_factor == 3.0
        assert config.retry_on_status == [500, 502, 503]

    def test_fetch_retry_config_validation_timeout(self):
        """Test timeout validation in FetchRetryConfig."""
        from pydantic import ValidationError

        from bundlecraft.helpers.config_schema import FetchRetryConfig

        with pytest.raises(ValidationError):
            FetchRetryConfig(timeout=0)  # Too low

        with pytest.raises(ValidationError):
            FetchRetryConfig(timeout=700)  # Too high

    def test_fetch_retry_config_validation_retries(self):
        """Test retries validation in FetchRetryConfig."""
        from pydantic import ValidationError

        from bundlecraft.helpers.config_schema import FetchRetryConfig

        with pytest.raises(ValidationError):
            FetchRetryConfig(retries=-1)  # Negative

        with pytest.raises(ValidationError):
            FetchRetryConfig(retries=15)  # Too high

    def test_fetch_retry_config_validation_backoff_factor(self):
        """Test backoff_factor validation in FetchRetryConfig."""
        from pydantic import ValidationError

        from bundlecraft.helpers.config_schema import FetchRetryConfig

        with pytest.raises(ValidationError):
            FetchRetryConfig(backoff_factor=0.5)  # Too low

        with pytest.raises(ValidationError):
            FetchRetryConfig(backoff_factor=15.0)  # Too high

    def test_fetch_retry_config_validation_status_codes(self):
        """Test retry_on_status validation in FetchRetryConfig."""
        from pydantic import ValidationError

        from bundlecraft.helpers.config_schema import FetchRetryConfig

        # Valid status codes
        config = FetchRetryConfig(retry_on_status=[200, 404, 500])
        assert config.retry_on_status == [200, 404, 500]

        # Invalid status codes
        with pytest.raises(ValidationError):
            FetchRetryConfig(retry_on_status=[99, 500])  # 99 is invalid

        with pytest.raises(ValidationError):
            FetchRetryConfig(retry_on_status=[500, 600])  # 600 is invalid

    def test_defaults_config_includes_fetch(self):
        """Test that DefaultsConfig includes fetch configuration."""
        from bundlecraft.helpers.config_schema import DefaultsConfig

        config = DefaultsConfig()
        assert hasattr(config, "fetch")
        assert config.fetch.timeout == 30
        assert config.fetch.retries == 3

    def test_fetch_entry_includes_retry_fields(self):
        """Test that FetchEntry includes optional retry fields."""
        from bundlecraft.helpers.config_schema import FetchEntry

        entry = FetchEntry(
            name="test",
            type="url",
            url="https://example.com/cert.pem",
            timeout=60,
            retries=5,
            backoff_factor=3.0,
            retry_on_status=[500, 502],
        )
        assert entry.timeout == 60
        assert entry.retries == 5
        assert entry.backoff_factor == 3.0
        assert entry.retry_on_status == [500, 502]

    def test_fetch_entry_optional_retry_fields(self):
        """Test that retry fields in FetchEntry are optional."""
        from bundlecraft.helpers.config_schema import FetchEntry

        entry = FetchEntry(name="test", type="url", url="https://example.com/cert.pem")
        assert entry.timeout is None
        assert entry.retries is None
        assert entry.backoff_factor is None
        assert entry.retry_on_status is None
