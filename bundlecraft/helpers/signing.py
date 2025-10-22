#!/usr/bin/env python3
"""
signing.py
GPG signing and verification utilities for BundleCraft release artifacts.

This module provides GPG/OpenPGP signature generation and verification
capabilities following the BYOK (Bring Your Own Key) model.

Key Features:
- Sign files using GPG with detached ASCII-armored signatures (.asc)
- Verify GPG signatures against files
- Support for custom GPG home directory and keyring
- Environment variable support for key ID and passphrase
- Clear error messages for missing keys or configuration

Security Notes:
- Never generates or stores keys automatically
- Uses user's GPG keyring by default (~/.gnupg)
- Supports both signing and encryption subkeys
- Passphrase can be provided via environment variable or prompt
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Optional dependency: python-gnupg
try:
    import gnupg as _gnupg  # type: ignore
except Exception:  # ImportError or other issues

    class _MissingGnupg:
        class GPG:  # minimal shim so tests can patch gnupg.GPG
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "python-gnupg is not installed. Install with 'pip install python-gnupg'."
                )

    _gnupg = _MissingGnupg()  # type: ignore

gnupg = _gnupg  # exposed name used throughout this module


def get_gpg_instance(gpg_home: Path | None = None) -> Any:
    """Get a GPG instance with the specified home directory.

    Args:
        gpg_home: Optional GPG home directory. Defaults to system default (~/.gnupg)

    Returns:
        gnupg.GPG instance
    """
    if gpg_home:
        return gnupg.GPG(gnupghome=str(gpg_home))
    return gnupg.GPG()


def sign_file(
    file_path: Path,
    key_id: str | None = None,
    passphrase: str | None = None,
    output_path: Path | None = None,
    gpg_home: Path | None = None,
) -> Path:
    """Sign a file using GPG and return the .asc signature path.

    Creates a detached ASCII-armored signature for the specified file.

    Args:
        file_path: Path to the file to sign
        key_id: GPG key ID to use for signing. If None, uses GPG_KEY_ID env var
        passphrase: Passphrase for the key. If None, uses GPG_PASSPHRASE env var
        output_path: Optional custom path for signature. Defaults to file_path + .asc
        gpg_home: Optional GPG home directory

    Returns:
        Path to the created signature file

    Raises:
        FileNotFoundError: If file_path doesn't exist
        ValueError: If key_id is not provided and GPG_KEY_ID env var is not set
        RuntimeError: If signing fails (key not found, wrong passphrase, etc.)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File to sign not found: {file_path}")

    # Get key ID from parameter or environment
    if key_id is None:
        key_id = os.environ.get("GPG_KEY_ID")

    if not key_id:
        raise ValueError(
            "GPG key ID not provided. Set --gpg-key-id or GPG_KEY_ID environment variable. "
            "To generate a GPG key, run: gpg --full-generate-key"
        )

    # Get passphrase from parameter or environment (optional)
    if passphrase is None:
        passphrase = os.environ.get("GPG_PASSPHRASE", "")

    # Determine output path
    if output_path is None:
        output_path = file_path.with_suffix(file_path.suffix + ".asc")

    # Get GPG instance
    gpg = get_gpg_instance(gpg_home)

    # Read file data
    with open(file_path, "rb") as f:
        data = f.read()

    # Sign the file
    signed = gpg.sign(
        data,
        keyid=key_id,
        passphrase=passphrase if passphrase else None,
        detach=True,
        clearsign=False,
    )

    if not signed.data:
        # Try to provide helpful error message
        error_msg = str(signed.stderr) if hasattr(signed, "stderr") else "Unknown error"
        if "secret key not available" in error_msg.lower() or "no secret key" in error_msg.lower():
            raise RuntimeError(
                f"GPG signing failed: Key '{key_id}' not found in keyring. "
                f"Available keys can be listed with: gpg --list-secret-keys"
            )
        elif "bad passphrase" in error_msg.lower():
            raise RuntimeError(
                "GPG signing failed: Invalid passphrase. "
                "Check GPG_PASSPHRASE environment variable or use correct passphrase."
            )
        else:
            raise RuntimeError(f"GPG signing failed: {error_msg}")

    # Write signature to file
    output_path.write_bytes(signed.data)

    return output_path


def verify_signature(
    file_path: Path,
    signature_path: Path | None = None,
    keyring: Path | None = None,
    gpg_home: Path | None = None,
) -> tuple[bool, str]:
    """Verify a GPG signature against a file.

    Args:
        file_path: Path to the signed file
        signature_path: Path to the signature file. Defaults to file_path + .asc
        keyring: Optional path to a public keyring file to import
        gpg_home: Optional GPG home directory

    Returns:
        Tuple of (verified: bool, message: str) where message contains details

    Raises:
        FileNotFoundError: If file_path or signature_path don't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File to verify not found: {file_path}")

    # Determine signature path
    if signature_path is None:
        signature_path = file_path.with_suffix(file_path.suffix + ".asc")

    if not signature_path.exists():
        raise FileNotFoundError(f"Signature file not found: {signature_path}")

    # Get GPG instance
    gpg = get_gpg_instance(gpg_home)

    # Import keyring if provided
    if keyring and keyring.exists():
        with open(keyring, "rb") as f:
            import_result = gpg.import_keys(f.read())
            if import_result.count == 0:
                return False, f"Failed to import keys from {keyring}"

    # Read file and signature
    with open(file_path, "rb") as f:
        data = f.read()

    with open(signature_path, "rb") as f:
        signature = f.read()

    # Verify signature
    verified = gpg.verify_data(signature, data)

    if verified.valid:
        key_id = verified.key_id if hasattr(verified, "key_id") else "unknown"
        username = verified.username if hasattr(verified, "username") else "unknown"
        return True, f"Valid signature from key {key_id} ({username})"
    else:
        status = verified.status if hasattr(verified, "status") else "unknown"
        return False, f"Invalid signature: {status}"


def list_available_keys(gpg_home: Path | None = None) -> list[dict]:
    """List available GPG secret keys in the keyring.

    Args:
        gpg_home: Optional GPG home directory

    Returns:
        List of dictionaries containing key information (keyid, uids, fingerprint, etc.)
    """
    gpg = get_gpg_instance(gpg_home)
    keys = gpg.list_keys(secret=True)
    return keys


def export_public_key(key_id: str, output_path: Path, gpg_home: Path | None = None) -> None:
    """Export a public key to a file.

    Args:
        key_id: GPG key ID to export
        output_path: Path where to write the exported public key
        gpg_home: Optional GPG home directory

    Raises:
        RuntimeError: If key export fails
    """
    gpg = get_gpg_instance(gpg_home)
    ascii_armored_key = gpg.export_keys(key_id)

    if not ascii_armored_key:
        raise RuntimeError(f"Failed to export public key for key ID: {key_id}")

    output_path.write_text(ascii_armored_key, encoding="utf-8")
