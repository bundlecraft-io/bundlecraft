#!/usr/bin/env python3
"""
exit_codes.py
Standardized exit codes for BundleCraft CLI.

Exit codes follow Unix conventions and provide clear error categorization
for CI/CD integration and automation.

Exit Code Ranges:
    0         - Success
    1         - General/unspecified error
    2-9       - Configuration errors
    10-19     - Input/Output errors
    20-29     - Network/fetch errors
    30-39     - Validation errors
    40-49     - Build/conversion errors
    50-59     - Runtime errors
"""

import sys


class ExitCode:
    """Standardized exit codes for BundleCraft CLI.

    These exit codes provide a consistent way to communicate command outcomes
    to calling processes, particularly useful for CI/CD integration.

    Usage:
        from bundlecraft.helpers.exit_codes import ExitCode, exit_with_code

        # Exit with a specific code
        exit_with_code(ExitCode.CONFIG_ERROR, "Invalid configuration file")

        # Or use sys.exit directly
        sys.exit(ExitCode.SUCCESS)
    """

    # Success
    SUCCESS = 0  # Operation completed successfully

    # General errors
    GENERAL_ERROR = 1  # Unspecified error (catch-all)

    # Configuration errors (2-9)
    CONFIG_ERROR = 2  # Invalid configuration (schema, syntax)
    CONFIG_NOT_FOUND = 3  # Missing required config file

    # Input/Output errors (10-19)
    INPUT_ERROR = 10  # Invalid input arguments
    OUTPUT_ERROR = 11  # Cannot write output files

    # Network/fetch errors (20-29)
    NETWORK_ERROR = 20  # Network connection failure
    AUTH_ERROR = 21  # Authentication/authorization failure
    FETCH_ERROR = 22  # Remote fetch failed (non-network)

    # Validation errors (30-39)
    VALIDATION_ERROR = 30  # Certificate validation failed
    EXPIRED_CERT = 31  # Certificate(s) expired
    INVALID_CERT = 32  # Malformed certificate

    # Build/conversion errors (40-49)
    BUILD_ERROR = 40  # Build process failed
    CONVERSION_ERROR = 41  # Format conversion failed

    # Runtime errors (50-59)
    DEPENDENCY_ERROR = 50  # Missing required dependency
    PERMISSION_ERROR = 51  # Insufficient permissions


# Mapping of exit codes to human-readable descriptions
EXIT_CODE_DESCRIPTIONS = {
    ExitCode.SUCCESS: "Success",
    ExitCode.GENERAL_ERROR: "General error",
    ExitCode.CONFIG_ERROR: "Configuration error",
    ExitCode.CONFIG_NOT_FOUND: "Configuration file not found",
    ExitCode.INPUT_ERROR: "Invalid input",
    ExitCode.OUTPUT_ERROR: "Output error",
    ExitCode.NETWORK_ERROR: "Network error",
    ExitCode.AUTH_ERROR: "Authentication error",
    ExitCode.FETCH_ERROR: "Fetch error",
    ExitCode.VALIDATION_ERROR: "Validation error",
    ExitCode.EXPIRED_CERT: "Expired certificate",
    ExitCode.INVALID_CERT: "Invalid certificate",
    ExitCode.BUILD_ERROR: "Build error",
    ExitCode.CONVERSION_ERROR: "Conversion error",
    ExitCode.DEPENDENCY_ERROR: "Dependency error",
    ExitCode.PERMISSION_ERROR: "Permission error",
}


def exit_with_code(code: int, message: str = None) -> None:
    """Exit the program with a specific exit code and optional message.

    Args:
        code: Exit code from ExitCode class
        message: Optional error message to print to stderr before exiting

    Example:
        exit_with_code(ExitCode.CONFIG_ERROR, "Invalid config file: missing 'name' field")
    """
    if message:
        print(f"[ERROR] {message}", file=sys.stderr)

    sys.exit(code)


def get_exit_code_description(code: int) -> str:
    """Get human-readable description for an exit code.

    Args:
        code: Exit code to describe

    Returns:
        Description string for the exit code
    """
    return EXIT_CODE_DESCRIPTIONS.get(code, f"Unknown exit code: {code}")
