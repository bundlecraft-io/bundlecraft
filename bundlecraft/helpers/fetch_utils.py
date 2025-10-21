#!/usr/bin/env python3
"""
fetch_utils.py
Retry and timeout utilities for fetch operations.

Provides:
- Configurable retry logic with exponential backoff
- Timeout handling for network operations
- Retry predicates for HTTP status codes and exceptions
"""

from __future__ import annotations

import random
import time
import urllib.error
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import click

# Default fetch configuration
DEFAULT_FETCH_CONFIG = {
    "timeout": 30,  # seconds
    "retries": 3,  # number of retry attempts
    "backoff_factor": 2.0,  # exponential backoff multiplier
    "retry_on_status": [429, 502, 503, 504],  # HTTP status codes to retry
}

T = TypeVar("T")


def calculate_backoff(attempt: int, backoff_factor: float = 2.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay with jitter.

    Args:
        attempt: Current retry attempt number (0-indexed)
        backoff_factor: Exponential multiplier
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds with random jitter
    """
    # Exponential backoff: backoff_factor ^ attempt
    delay = min(backoff_factor**attempt, max_delay)
    # Add jitter: randomize between 0.5x and 1.5x the calculated delay
    jitter = delay * (0.5 + random.random())
    return jitter


def should_retry_http_error(error: urllib.error.HTTPError, retry_on_status: list[int]) -> bool:
    """Check if an HTTP error should trigger a retry.

    Args:
        error: HTTPError exception
        retry_on_status: List of HTTP status codes that should trigger retry

    Returns:
        True if the error should be retried
    """
    return error.code in retry_on_status


def retry_with_backoff(
    retries: int = 3,
    backoff_factor: float = 2.0,
    retry_on_status: list[int] | None = None,
    timeout: int | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic with exponential backoff to a function.

    Args:
        retries: Number of retry attempts (default: 3)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        retry_on_status: HTTP status codes to retry (default: [429, 502, 503, 504])
        timeout: Timeout in seconds (passed to decorated function if supported)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(retries=3, backoff_factor=2.0)
        def fetch_data(url):
            return urllib.request.urlopen(url)
    """
    if retry_on_status is None:
        retry_on_status = DEFAULT_FETCH_CONFIG["retry_on_status"]

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Inject timeout if the function supports it and it's provided
            if timeout is not None and "timeout" in func.__code__.co_varnames:
                kwargs.setdefault("timeout", timeout)

            last_exception: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except urllib.error.HTTPError as e:
                    last_exception = e
                    if attempt >= retries:
                        # Out of retries
                        raise
                    if not should_retry_http_error(e, retry_on_status):
                        # Not a retryable error
                        raise
                    # Calculate backoff and retry
                    delay = calculate_backoff(attempt, backoff_factor)
                    click.echo(
                        f"  ⚠️  HTTP {e.code} error, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{retries})...",
                        err=True,
                    )
                    time.sleep(delay)
                except (urllib.error.URLError, OSError, TimeoutError) as e:
                    last_exception = e
                    if attempt >= retries:
                        # Out of retries
                        raise
                    # Network errors are generally retryable
                    delay = calculate_backoff(attempt, backoff_factor)
                    click.echo(
                        f"  ⚠️  Network error ({type(e).__name__}), retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{retries})...",
                        err=True,
                    )
                    time.sleep(delay)
                except Exception:
                    # Non-retryable exceptions should be raised immediately
                    raise
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error: exhausted retries without exception")

        return wrapper

    return decorator


def get_fetch_config(
    source_config: dict[str, Any] | None = None, defaults: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Get fetch configuration with source-specific overrides.

    Priority:
        1. Source-specific config (from fetch entry)
        2. Global defaults (from defaults.yaml)
        3. Built-in defaults

    Args:
        source_config: Source-specific fetch configuration
        defaults: Global defaults configuration

    Returns:
        Merged fetch configuration
    """
    config = DEFAULT_FETCH_CONFIG.copy()

    # Apply global defaults
    if defaults and "fetch" in defaults:
        fetch_defaults = defaults["fetch"]
        if isinstance(fetch_defaults, dict):
            config.update(fetch_defaults)

    # Apply source-specific overrides
    if source_config:
        for key in ["timeout", "retries", "backoff_factor", "retry_on_status"]:
            if key in source_config and source_config[key] is not None:
                config[key] = source_config[key]

    return config
