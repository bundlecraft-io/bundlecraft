from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def load_yaml(
    path: Path, required: bool = True, validate: Callable[[dict[str, Any], str], Any] | None = None
) -> dict[str, Any] | None:
    """Load and optionally validate a YAML configuration file.

    Args:
        path: Path to YAML file
        required: If True, raise error if file doesn't exist
        validate: Optional validation function that takes (data, path_str) and returns validated model

    Returns:
        Dictionary from YAML file, or None if not required and doesn't exist

    Raises:
        FileNotFoundError: If required=True and file doesn't exist
        RuntimeError: If PyYAML is not installed
        ValueError: If validation fails (from validate function)
    """
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing YAML file: {path}")
        return None
    try:
        import yaml  # PyYAML
    except ImportError as e:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml") from e
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # Optionally validate with schema
    if validate is not None:
        try:
            validate(data, str(path))
        except ValueError:
            raise  # Re-raise with original error message
        except Exception as e:
            raise ValueError(f"Config validation failed for {path}: {e}") from e

    return data


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_files(folder: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for s in suffixes:
        out.extend(folder.rglob(f"*{s}"))
    return out


def merge_configs(defaults: dict[str, Any], env: dict[str, Any]) -> dict[str, Any]:
    """Merge env config over defaults with deep merge for nested dicts.

    Precedence: defaults < env
    """
    import copy

    merged = copy.deepcopy(defaults)

    def deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge override into base."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    return deep_merge(merged, env)


def apply_filters(pem_blocks: list[str], filters_cfg: dict[str, Any]) -> list[str]:
    """Apply certificate filtering based on filter configuration.

    Supported filters:
    - unique_by_fingerprint: deduplicate by SHA256
    - not_expired_only: exclude expired certificates
    - ca_certs_only: only include CA certificates (BasicConstraints CA:TRUE)
    - root_certs_only: only include self-signed root CAs
    - signature_algorithms: include/exclude by signature algorithm OID or name
    - minimum_key_size_rsa: minimum RSA key size in bits
    - minimum_key_size_ecc: minimum ECC key size in bits
    """
    import datetime as dt

    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    filtered = pem_blocks[:]

    # Filter 1: unique_by_fingerprint
    if filters_cfg.get("unique_by_fingerprint"):
        filtered = _dedupe_by_fingerprint(filtered)

    # Filter 2-7: Parse certificates and apply filters
    parsed_certs: list[tuple[str, x509.Certificate]] = []
    for blk in filtered:
        try:
            cert = x509.load_pem_x509_certificate(blk.encode("utf-8"), default_backend())
            parsed_certs.append((blk, cert))
        except Exception:
            # Skip unparsable blocks
            continue

    # Filter 2: not_expired_only
    if filters_cfg.get("not_expired_only"):
        now = dt.datetime.now(dt.timezone.utc)
        parsed_certs = [(blk, cert) for blk, cert in parsed_certs if _get_not_after(cert) > now]

    # Filter 3: ca_certs_only
    if filters_cfg.get("ca_certs_only"):
        parsed_certs = [(blk, cert) for blk, cert in parsed_certs if _is_ca_cert(cert)]

    # Filter 4: root_certs_only
    if filters_cfg.get("root_certs_only"):
        parsed_certs = [(blk, cert) for blk, cert in parsed_certs if _is_root_cert(cert)]

    # Filter 5: signature_algorithms
    sig_alg_cfg = filters_cfg.get("signature_algorithms")
    if sig_alg_cfg and isinstance(sig_alg_cfg, dict):
        parsed_certs = _filter_by_signature_algorithm(parsed_certs, sig_alg_cfg)

    # Filter 6: minimum_key_size_rsa
    min_rsa = filters_cfg.get("minimum_key_size_rsa")
    if min_rsa is not None:
        parsed_certs = [
            (blk, cert) for blk, cert in parsed_certs if _check_rsa_key_size(cert, min_rsa)
        ]

    # Filter 7: minimum_key_size_ecc
    min_ecc = filters_cfg.get("minimum_key_size_ecc")
    if min_ecc is not None:
        parsed_certs = [
            (blk, cert) for blk, cert in parsed_certs if _check_ecc_key_size(cert, min_ecc)
        ]

    return [blk for blk, _ in parsed_certs]


def _dedupe_by_fingerprint(pem_blocks: list[str]) -> list[str]:
    """Deduplicate PEM blocks by SHA256 fingerprint, preserving order."""
    import base64
    import hashlib
    import re

    seen, out = set(), []
    b64re = re.compile(
        r"-----BEGIN CERTIFICATE-----\s*([A-Za-z0-9+/=\s]+)-----END CERTIFICATE-----",
        re.S,
    )
    for blk in pem_blocks:
        m = b64re.search(blk)
        if not m:
            continue
        der = base64.b64decode("".join(m.group(1).split()))
        h = hashlib.sha256(der).hexdigest()
        if h not in seen:
            seen.add(h)
            out.append(blk if blk.endswith("\n") else blk + "\n")
    return out


def _get_not_after(cert) -> any:
    """Get certificate expiry with timezone awareness."""
    import datetime as dt

    exp = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=dt.timezone.utc)
    return exp


def _is_ca_cert(cert) -> bool:
    """Check if certificate is a CA (BasicConstraints CA:TRUE)."""
    from cryptography.x509.oid import ExtensionOID

    try:
        bc = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
        return bc.value.ca
    except Exception:
        return False


def _is_root_cert(cert) -> bool:
    """Check if certificate is self-signed (root CA).

    A root certificate is self-signed: issuer == subject and
    signature validates against its own public key.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

    # Check if issuer == subject
    if cert.issuer != cert.subject:
        return False

    # Try to verify signature with its own public key
    try:
        public_key = cert.public_key()
        # For RSA
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
            return True
        # For EC
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                cert.signature, cert.tbs_certificate_bytes, ec.ECDSA(cert.signature_hash_algorithm)
            )
            return True
        else:
            # For other key types, just check issuer == subject
            return True
    except (InvalidSignature, Exception):
        return False


def _filter_by_signature_algorithm(
    parsed_certs: list[tuple[str, any]], sig_alg_cfg: dict[str, list[str]]
) -> list[tuple[str, any]]:
    """Filter by signature algorithm include/exclude lists.

    Config example:
      signature_algorithms:
        include: ["sha256WithRSAEncryption", "ecdsa-with-SHA256"]
        exclude: ["sha1WithRSAEncryption", "md5WithRSAEncryption"]
    """
    include_list = sig_alg_cfg.get("include") or []
    exclude_list = sig_alg_cfg.get("exclude") or []

    result = []
    for blk, cert in parsed_certs:
        sig_alg_name = cert.signature_algorithm_oid._name
        sig_alg_dotted = cert.signature_algorithm_oid.dotted_string

        # If include list exists, cert must be in it
        if include_list:
            if not any(
                pattern.lower() in sig_alg_name.lower() or pattern.lower() in sig_alg_dotted.lower()
                for pattern in include_list
            ):
                continue

        # If exclude list exists, cert must not be in it
        if exclude_list:
            if any(
                pattern.lower() in sig_alg_name.lower() or pattern.lower() in sig_alg_dotted.lower()
                for pattern in exclude_list
            ):
                continue

        result.append((blk, cert))

    return result


def _check_rsa_key_size(cert, min_size: int) -> bool:
    """Check if RSA key meets minimum size requirement."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    try:
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            return public_key.key_size >= min_size
        # Non-RSA keys pass this filter
        return True
    except Exception:
        return True


def _check_ecc_key_size(cert, min_size: int) -> bool:
    """Check if ECC key meets minimum size requirement."""
    from cryptography.hazmat.primitives.asymmetric import ec

    try:
        public_key = cert.public_key()
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            return public_key.curve.key_size >= min_size
        # Non-ECC keys pass this filter
        return True
    except Exception:
        return True
