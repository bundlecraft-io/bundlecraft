#!/usr/bin/env python3
"""
signer.py
----------------
Sign and verify artifacts using GPG or Sigstore.

Features:
- GPG signing of manifest.json and package artifacts
- Sigstore signing (when sigstore is available)
- Signature verification for both GPG and Sigstore
- Environment-based signing configuration
- CLI integration for sign/verify operations
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal

import click

# --- logging setup ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SigningMethod = Literal["gpg", "sigstore", "none"]


class SigningError(Exception):
    """Base exception for signing operations."""

    pass


class SignerConfig:
    """Configuration for signing operations."""

    def __init__(
        self,
        method: SigningMethod = "none",
        gpg_key_id: str | None = None,
        gpg_passphrase: str | None = None,
        gpg_home: str | None = None,
    ):
        self.method = method
        self.gpg_key_id = gpg_key_id
        self.gpg_passphrase = gpg_passphrase
        self.gpg_home = gpg_home

    @classmethod
    def from_env(cls) -> "SignerConfig":
        """Create SignerConfig from environment variables.

        Environment variables:
        - BUNDLECRAFT_SIGN_METHOD: "gpg", "sigstore", or "none" (default)
        - BUNDLECRAFT_GPG_KEY_ID: GPG key ID for signing
        - BUNDLECRAFT_GPG_PASSPHRASE: Passphrase for GPG key
        - BUNDLECRAFT_GPG_HOME: Custom GPG home directory
        """
        method = os.environ.get("BUNDLECRAFT_SIGN_METHOD", "none").lower()
        if method not in ("gpg", "sigstore", "none"):
            logger.warning(f"Invalid BUNDLECRAFT_SIGN_METHOD: {method}, using 'none'")
            method = "none"

        return cls(
            method=method,  # type: ignore
            gpg_key_id=os.environ.get("BUNDLECRAFT_GPG_KEY_ID"),
            gpg_passphrase=os.environ.get("BUNDLECRAFT_GPG_PASSPHRASE"),
            gpg_home=os.environ.get("BUNDLECRAFT_GPG_HOME"),
        )


def _check_gpg_available() -> bool:
    """Check if GPG is available in the system."""
    return shutil.which("gpg") is not None


def _check_sigstore_available() -> bool:
    """Check if Sigstore (cosign) is available in the system."""
    return shutil.which("cosign") is not None


def sign_file_gpg(
    file_path: Path,
    key_id: str | None = None,
    passphrase: str | None = None,
    gpg_home: str | None = None,
    armor: bool = True,
    detach: bool = True,
) -> Path:
    """Sign a file using GPG.

    Args:
        file_path: Path to the file to sign
        key_id: GPG key ID to use for signing
        passphrase: Passphrase for the GPG key
        gpg_home: Custom GPG home directory
        armor: Create ASCII-armored signature
        detach: Create detached signature

    Returns:
        Path to the signature file

    Raises:
        SigningError: If signing fails
    """
    if not _check_gpg_available():
        raise SigningError("GPG is not available. Please install GnuPG.")

    if not file_path.exists():
        raise SigningError(f"File not found: {file_path}")

    # Determine signature extension
    if armor:
        sig_ext = ".asc" if detach else ".gpg"
    else:
        sig_ext = ".sig" if detach else ".gpg"

    sig_path = file_path.with_suffix(file_path.suffix + sig_ext)

    # Build GPG command
    cmd = ["gpg", "--batch", "--yes"]

    if gpg_home:
        cmd.extend(["--homedir", gpg_home])

    if armor:
        cmd.append("--armor")

    if detach:
        cmd.append("--detach-sign")
    else:
        cmd.append("--sign")

    if key_id:
        cmd.extend(["--local-user", key_id])

    if passphrase:
        cmd.extend(["--pinentry-mode", "loopback", "--passphrase-fd", "0"])

    cmd.extend(["--output", str(sig_path), str(file_path)])

    try:
        if passphrase:
            subprocess.run(
                cmd,
                input=passphrase.encode(),
                capture_output=True,
                text=False,
                timeout=30,
                check=True,
            )
        else:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        logger.info(f"✅ GPG signature created: {sig_path.name}")
        return sig_path
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr
        raise SigningError(f"GPG signing failed: {stderr}") from e
    except subprocess.TimeoutExpired as e:
        raise SigningError("GPG signing timed out") from e


def verify_file_gpg(
    file_path: Path,
    sig_path: Path | None = None,
    gpg_home: str | None = None,
) -> bool:
    """Verify a GPG signature.

    Args:
        file_path: Path to the signed file
        sig_path: Path to the signature file (auto-detected if None)
        gpg_home: Custom GPG home directory

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SigningError: If verification fails due to missing files or GPG errors
    """
    if not _check_gpg_available():
        raise SigningError("GPG is not available. Please install GnuPG.")

    if not file_path.exists():
        raise SigningError(f"File not found: {file_path}")

    # Auto-detect signature file if not provided
    if sig_path is None:
        # Try common signature extensions
        for ext in [".asc", ".sig", ".gpg"]:
            candidate = file_path.with_suffix(file_path.suffix + ext)
            if candidate.exists():
                sig_path = candidate
                break

        if sig_path is None:
            raise SigningError(f"No signature file found for: {file_path}")

    if not sig_path.exists():
        raise SigningError(f"Signature file not found: {sig_path}")

    # Build GPG command
    cmd = ["gpg", "--batch", "--verify"]

    if gpg_home:
        cmd.extend(["--homedir", gpg_home])

    cmd.extend([str(sig_path), str(file_path)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info(f"✅ GPG signature valid: {file_path.name}")
            return True
        else:
            logger.warning(f"⚠️  GPG signature invalid: {file_path.name}")
            logger.debug(f"GPG output: {result.stderr}")
            return False
    except subprocess.TimeoutExpired as e:
        raise SigningError("GPG verification timed out") from e


def sign_file_sigstore(file_path: Path) -> Path:
    """Sign a file using Sigstore (cosign).

    Args:
        file_path: Path to the file to sign

    Returns:
        Path to the signature file

    Raises:
        SigningError: If signing fails
    """
    if not _check_sigstore_available():
        raise SigningError(
            "Sigstore (cosign) is not available. Please install cosign: "
            "https://docs.sigstore.dev/cosign/installation"
        )

    if not file_path.exists():
        raise SigningError(f"File not found: {file_path}")

    sig_path = file_path.with_suffix(file_path.suffix + ".sig")

    # Build cosign command (uses keyless signing by default)
    cmd = [
        "cosign",
        "sign-blob",
        "--output-signature",
        str(sig_path),
        str(file_path),
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        logger.info(f"✅ Sigstore signature created: {sig_path.name}")
        return sig_path
    except subprocess.CalledProcessError as e:
        raise SigningError(f"Sigstore signing failed: {e.stderr}") from e
    except subprocess.TimeoutExpired as e:
        raise SigningError("Sigstore signing timed out") from e


def verify_file_sigstore(file_path: Path, sig_path: Path | None = None) -> bool:
    """Verify a Sigstore signature.

    Args:
        file_path: Path to the signed file
        sig_path: Path to the signature file (auto-detected if None)

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SigningError: If verification fails due to missing files
    """
    if not _check_sigstore_available():
        raise SigningError(
            "Sigstore (cosign) is not available. Please install cosign: "
            "https://docs.sigstore.dev/cosign/installation"
        )

    if not file_path.exists():
        raise SigningError(f"File not found: {file_path}")

    # Auto-detect signature file if not provided
    if sig_path is None:
        sig_path = file_path.with_suffix(file_path.suffix + ".sig")

    if not sig_path.exists():
        raise SigningError(f"Signature file not found: {sig_path}")

    # Build cosign command
    cmd = ["cosign", "verify-blob", "--signature", str(sig_path), str(file_path)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info(f"✅ Sigstore signature valid: {file_path.name}")
            return True
        else:
            logger.warning(f"⚠️  Sigstore signature invalid: {file_path.name}")
            logger.debug(f"Cosign output: {result.stderr}")
            return False
    except subprocess.TimeoutExpired as e:
        raise SigningError("Sigstore verification timed out") from e


def sign_file(file_path: Path, config: SignerConfig) -> Path | None:
    """Sign a file using the configured signing method.

    Args:
        file_path: Path to the file to sign
        config: Signing configuration

    Returns:
        Path to the signature file, or None if signing is disabled

    Raises:
        SigningError: If signing fails
    """
    if config.method == "none":
        logger.debug(f"Signing disabled, skipping: {file_path.name}")
        return None

    if config.method == "gpg":
        return sign_file_gpg(
            file_path,
            key_id=config.gpg_key_id,
            passphrase=config.gpg_passphrase,
            gpg_home=config.gpg_home,
        )
    elif config.method == "sigstore":
        return sign_file_sigstore(file_path)
    else:
        raise SigningError(f"Unsupported signing method: {config.method}")


def verify_file(
    file_path: Path, method: SigningMethod | None = None, config: SignerConfig | None = None
) -> bool:
    """Verify a file signature using the specified method.

    Args:
        file_path: Path to the signed file
        method: Signing method to use (auto-detect if None)
        config: Signing configuration (uses environment if None)

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SigningError: If verification fails due to errors
    """
    if config is None:
        config = SignerConfig.from_env()

    # Auto-detect method from signature file if not specified
    if method is None:
        for ext, detected_method in [(".asc", "gpg"), (".sig", "gpg")]:
            if file_path.with_suffix(file_path.suffix + ext).exists():
                method = detected_method
                break

        # Check for Sigstore signature
        if method is None and file_path.with_suffix(file_path.suffix + ".sig").exists():
            method = "sigstore"

    if method is None:
        logger.warning(f"No signature file found for: {file_path.name}")
        return False

    if method == "gpg":
        return verify_file_gpg(file_path, gpg_home=config.gpg_home)
    elif method == "sigstore":
        return verify_file_sigstore(file_path)
    else:
        raise SigningError(f"Unsupported verification method: {method}")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--sign",
    "operation",
    flag_value="sign",
    default=True,
    help="Sign a file (default)",
)
@click.option(
    "--verify",
    "operation",
    flag_value="verify",
    help="Verify a file signature",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the file to sign or verify",
)
@click.option(
    "--method",
    "-m",
    type=click.Choice(["gpg", "sigstore"], case_sensitive=False),
    help="Signing method (defaults to env BUNDLECRAFT_SIGN_METHOD or auto-detect for verify)",
)
@click.option(
    "--gpg-key-id",
    help="GPG key ID for signing (defaults to env BUNDLECRAFT_GPG_KEY_ID)",
)
@click.option(
    "--gpg-passphrase",
    help="GPG key passphrase (defaults to env BUNDLECRAFT_GPG_PASSPHRASE)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def main(operation, file_path, method, gpg_key_id, gpg_passphrase, verbose):
    """Sign or verify artifact signatures using GPG or Sigstore."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    click.secho("\n🔐 BundleCraft Signer\n--------------------", fg="cyan")

    # Build config from CLI args and environment
    config = SignerConfig.from_env()

    # Override with CLI args if provided
    if method:
        config.method = method.lower()  # type: ignore
    if gpg_key_id:
        config.gpg_key_id = gpg_key_id
    if gpg_passphrase:
        config.gpg_passphrase = gpg_passphrase

    try:
        if operation == "sign":
            if config.method == "none":
                click.secho(
                    "⚠️  No signing method specified. Use --method or set BUNDLECRAFT_SIGN_METHOD",
                    fg="yellow",
                )
                return

            click.echo(f"Signing file: {file_path}")
            click.echo(f"Method: {config.method}")

            sig_path = sign_file(file_path, config)
            if sig_path:
                click.secho(f"✅ Signature created: {sig_path}", fg="green")
        else:  # verify
            click.echo(f"Verifying file: {file_path}")

            is_valid = verify_file(file_path, method=config.method if method else None, config=config)  # type: ignore

            if is_valid:
                click.secho("✅ Signature verification: PASSED", fg="green")
            else:
                click.secho("❌ Signature verification: FAILED", fg="red")
                exit(1)

    except SigningError as e:
        click.secho(f"❌ Error: {e}", fg="red", err=True)
        exit(1)


if __name__ == "__main__":
    main()
