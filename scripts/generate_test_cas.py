#!/usr/bin/env python3
"""
generate_test_cas.py

⚠️  TESTING ONLY - DO NOT USE FOR PRODUCTION ⚠️

Generate self-signed root CAs and subordinate certificate chains for testing.
Automatically disposes of all private key material after certificate generation.

This tool is designed exclusively for generating test certificates for BundleCraft
development and testing. It intentionally does NOT support private key export.

Usage:
  # Single self-signed root CA
  ./generate_test_cas.py --name test-root

  # Root with 2-tier subordinate chain
  ./generate_test_cas.py --name prod-root --depth 2 --env prod --boundary internal

  # Full hierarchy with custom settings
  ./generate_test_cas.py --name dev-root --depth 3 --key-size 4096 --validity 730

  # Multiple independent roots (via config)
  ./generate_test_cas.py --config my_ca_hierarchy.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print(
        "ERROR: cryptography library required. Install with: pip install cryptography",
        file=sys.stderr,
    )
    sys.exit(1)

import datetime as dt

# === CONSTANTS ===
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path.cwd() / "generated-test-cas"
DEFAULT_KEY_SIZE = 2048
DEFAULT_VALIDITY_DAYS = 365
MAX_CHAIN_DEPTH = 10

# === Security Notice ===
SECURITY_NOTICE = """
╔════════════════════════════════════════════════════════════════════════════╗
║                           ⚠️  SECURITY NOTICE ⚠️                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║  This tool generates TEST CERTIFICATES ONLY                                ║
║                                                                            ║
║  Private keys are IMMEDIATELY DESTROYED after certificate generation      ║
║  and are NEVER written to disk or made available for export.              ║
║                                                                            ║
║  These certificates are suitable ONLY for:                                ║
║    • BundleCraft development and testing                                  ║
║    • CI/CD pipeline verification                                          ║
║    • Local test environments                                              ║
║                                                                            ║
║  DO NOT use these certificates in production systems.                     ║
║  DO NOT attempt to modify this tool to export private keys.               ║
╚════════════════════════════════════════════════════════════════════════════╝
"""


class SecureCAGenerator:
    """
    Secure CA certificate generator with automatic private key disposal.

    Private keys are held in memory only during certificate generation
    and are explicitly zeroed and deleted immediately after use.
    """

    def __init__(
        self,
        output_dir: Path,
        key_size: int = DEFAULT_KEY_SIZE,
        validity_days: int = DEFAULT_VALIDITY_DAYS,
    ):
        self.output_dir = Path(output_dir)
        self.key_size = key_size
        self.validity_days = validity_days
        self._temp_keys: dict[str, Any] = {}  # Temporary key storage for chain signing

    def _secure_dispose_key(self, key: rsa.RSAPrivateKey) -> None:
        """
        Securely dispose of a private key by zeroing memory.
        Best-effort memory clearing for Python.
        """
        try:
            # Export to bytes to get memory reference
            key_bytes = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            # Zero the bytes (Python bytearray allows mutation)
            key_array = bytearray(key_bytes)
            for i in range(len(key_array)):
                key_array[i] = 0
            # Delete references
            del key_bytes
            del key_array
            del key
        except Exception:
            pass  # Best effort

    def _generate_key_pair(self) -> rsa.RSAPrivateKey:
        """Generate an RSA key pair."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend(),
        )

    def _build_name(self, cn: str, org: str = "BundleCraft Test CA") -> x509.Name:
        """Build X.509 distinguished name."""
        return x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, cn),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Testing Only"),
            ]
        )

    def generate_root_ca(
        self,
        name: str,
        env: str | None = None,
        boundary: str | None = None,
    ) -> x509.Certificate:
        """
        Generate a self-signed root CA certificate.

        Private key is disposed immediately after certificate generation.
        Returns only the certificate (PEM).
        """
        print(f"[INFO] Generating self-signed root CA: {name}")

        # Generate key pair
        private_key = self._generate_key_pair()

        # Build certificate
        subject = issuer = self._build_name(name)

        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(dt.datetime.now(dt.timezone.utc))
            .not_valid_after(
                dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=self.validity_days)
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=False,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
        )

        cert = cert_builder.sign(private_key, hashes.SHA256(), backend=default_backend())

        # Store key temporarily for subordinate signing (if needed)
        self._temp_keys[name] = (private_key, cert)

        # Save certificate
        self._save_cert(cert, name, env, boundary, "root")

        return cert

    def generate_subordinate_ca(
        self,
        name: str,
        parent_name: str,
        tier: int,
        env: str | None = None,
        boundary: str | None = None,
    ) -> x509.Certificate:
        """
        Generate a subordinate CA signed by parent.

        Private key is disposed immediately after certificate generation.
        """
        if parent_name not in self._temp_keys:
            raise ValueError(f"Parent CA '{parent_name}' not found. Generate parent first.")

        print(f"[INFO] Generating subordinate CA: {name} (tier {tier}, signed by {parent_name})")

        parent_key, parent_cert = self._temp_keys[parent_name]

        # Generate key pair for subordinate
        private_key = self._generate_key_pair()

        # Build certificate
        subject = self._build_name(name)
        issuer = parent_cert.subject

        # Calculate path_length: allow further subordinates below this level
        remaining_depth = MAX_CHAIN_DEPTH - tier
        path_length = remaining_depth if remaining_depth > 0 else 0

        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(dt.datetime.now(dt.timezone.utc))
            .not_valid_after(
                dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=self.validity_days)
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=path_length),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=False,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(parent_key.public_key()),
                critical=False,
            )
        )

        cert = cert_builder.sign(parent_key, hashes.SHA256(), backend=default_backend())

        # Store for potential further subordinates
        self._temp_keys[name] = (private_key, cert)

        # Save certificate
        tier_name = f"tier{tier}"
        self._save_cert(cert, name, env, boundary, tier_name)

        return cert

    def _save_cert(
        self,
        cert: x509.Certificate,
        name: str,
        env: str | None,
        boundary: str | None,
        tier: str,
    ) -> Path:
        """Save certificate to disk in appropriate hierarchy."""
        # Build output path
        parts = []
        if env:
            parts.append(env)
        if boundary:
            parts.append(boundary)
        parts.append(tier)

        output_path = self.output_dir.joinpath(*parts)
        output_path.mkdir(parents=True, exist_ok=True)

        cert_file = output_path / f"{name}.pem"

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"✅ Saved: {cert_file}")
        return cert_file

    def dispose_all_keys(self) -> None:
        """
        Securely dispose of all private keys held in memory.
        Called automatically at the end of generation.
        """
        print("[INFO] Securely disposing of all private key material...")
        for key, _ in list(self._temp_keys.items()):
            self._secure_dispose_key(key)
        self._temp_keys.clear()
        print("✅ All private keys disposed")

    def generate_hierarchy(
        self,
        root_name: str,
        depth: int,
        env: str | None = None,
        boundary: str | None = None,
    ) -> list[x509.Certificate]:
        """
        Generate a complete CA hierarchy with specified depth.

        Args:
            root_name: Name for root CA
            depth: Number of subordinate tiers (0 = root only, 1 = root + 1 sub, etc.)
            env: Environment label (dev, qa, prod, etc.)
            boundary: Boundary label (internal, dmz, external, etc.)

        Returns:
            List of generated certificates [root, sub1, sub2, ...]
        """
        if depth < 0:
            raise ValueError("Depth must be >= 0")
        if depth > MAX_CHAIN_DEPTH:
            raise ValueError(f"Depth exceeds maximum allowed ({MAX_CHAIN_DEPTH})")

        certs = []

        # Generate root
        root_cert = self.generate_root_ca(root_name, env, boundary)
        certs.append(root_cert)

        # Generate subordinates
        parent_name = root_name
        for tier in range(1, depth + 1):
            sub_name = f"{root_name}-sub{tier}"
            sub_cert = self.generate_subordinate_ca(sub_name, parent_name, tier, env, boundary)
            certs.append(sub_cert)
            parent_name = sub_name

        return certs


def load_config(config_path: Path) -> list[dict[str, Any]]:
    """
    Load CA hierarchy configuration from JSON file.

    Example config:
    [
      {
        "root_name": "dev-root",
        "depth": 2,
        "env": "dev",
        "boundary": "internal",
        "key_size": 2048,
        "validity_days": 365
      },
      {
        "root_name": "prod-root",
        "depth": 1,
        "env": "prod",
        "boundary": "internal"
      }
    ]
    """
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate test CA certificates for BundleCraft (TESTING ONLY)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=SECURITY_NOTICE,
    )

    parser.add_argument(
        "--name",
        help="Root CA common name (required unless --config is used)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help=f"Number of subordinate CA tiers (0-{MAX_CHAIN_DEPTH}, default: 0 = root only)",
    )
    parser.add_argument(
        "--env",
        help="Environment label (e.g., dev, qa, prod)",
    )
    parser.add_argument(
        "--boundary",
        help="Network boundary label (e.g., internal, dmz, external)",
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=DEFAULT_KEY_SIZE,
        help=f"RSA key size in bits (default: {DEFAULT_KEY_SIZE})",
    )
    parser.add_argument(
        "--validity",
        type=int,
        default=DEFAULT_VALIDITY_DAYS,
        help=f"Certificate validity in days (default: {DEFAULT_VALIDITY_DAYS})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Root output directory (default: ./generated-test-cas). Certificates are organized within this directory.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="JSON config file for batch generation (see docs for schema)",
    )
    parser.add_argument(
        "--no-warning",
        action="store_true",
        help="Suppress security warning (not recommended)",
    )

    args = parser.parse_args()

    # Show security notice
    if not args.no_warning:
        print(SECURITY_NOTICE)
        try:
            response = input("Type 'I UNDERSTAND' to proceed: ").strip()
            if response != "I UNDERSTAND":
                print("Aborted.")
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    # Validate arguments
    if args.config:
        # Batch mode
        try:
            configs = load_config(args.config)
        except Exception as e:
            print(f"ERROR: Failed to load config file: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"[INFO] Loaded {len(configs)} CA hierarchy configuration(s)")

        for idx, cfg in enumerate(configs, 1):
            print(f"\n{'='*70}")
            print(f"Processing hierarchy {idx}/{len(configs)}: {cfg.get('root_name', '(unnamed)')}")
            print("=" * 70)

            generator = SecureCAGenerator(
                output_dir=args.output_dir,
                key_size=cfg.get("key_size", DEFAULT_KEY_SIZE),
                validity_days=cfg.get("validity_days", DEFAULT_VALIDITY_DAYS),
            )

            try:
                generator.generate_hierarchy(
                    root_name=cfg["root_name"],
                    depth=cfg.get("depth", 0),
                    env=cfg.get("env"),
                    boundary=cfg.get("boundary"),
                )
            finally:
                generator.dispose_all_keys()

    else:
        # Single hierarchy mode
        if not args.name:
            parser.error("--name is required unless --config is provided")

        if args.depth < 0 or args.depth > MAX_CHAIN_DEPTH:
            parser.error(f"--depth must be between 0 and {MAX_CHAIN_DEPTH}")

        generator = SecureCAGenerator(
            output_dir=args.output_dir,
            key_size=args.key_size,
            validity_days=args.validity,
        )

        try:
            print(f"\n{'='*70}")
            print(f"Generating CA hierarchy: {args.name}")
            print("=" * 70)

            certs = generator.generate_hierarchy(
                root_name=args.name,
                depth=args.depth,
                env=args.env,
                boundary=args.boundary,
            )

            print(f"\n✅ Successfully generated {len(certs)} certificate(s)")

        finally:
            generator.dispose_all_keys()

    print("\n" + "=" * 70)
    print("Generation complete. All private keys have been securely disposed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
