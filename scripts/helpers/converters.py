#!/usr/bin/env python3
"""
converters.py
Handles format conversions for PKI-CA-Trust bundles.

Supports:
  • PEM → PKCS#7 (.p7b)
  • PEM → Java KeyStore (.jks)
  • PEM → PKCS#12 (.p12 / .pfx)

Requires:
  - openssl (for p7b / p12)
  - keytool (for jks)
"""

import os
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------

def convert_to_formats(
    pem_path: Path,
    build_root: Path,
    formats: list[str],
    fmt_overrides: dict | None = None,
):
    """
    Convert a canonical PEM bundle into one or more target formats.

    Args:
        pem_path (Path): Input PEM file path
        build_root (Path): Output directory
        formats (list[str]): Target formats (e.g., ["p7b", "jks", "p12"])
        fmt_overrides (dict|None): Optional per-format overrides (alias/password env)
    """
    fmt_overrides = fmt_overrides or {}
    norm = [f.lower() for f in formats]

    for fmt in norm:
        if fmt in ("p7b", "pkcs7"):
            create_p7b(pem_path, build_root)
        elif fmt == "jks":
            create_jks(pem_path, build_root, fmt_overrides.get("jks", {}))
        elif fmt in ("p12", "pfx", "pkcs12"):
            create_pkcs12(pem_path, build_root, fmt_overrides.get("pkcs12", {}))
        else:
            print(f"[WARN] Unknown format requested: {fmt}")


# ---------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------

def create_p7b(pem_path: Path, build_root: Path):
    """
    Convert PEM → PKCS#7 (.p7b, DER) including ALL certs.

    Use -certfile (not -in) so OpenSSL ingests the entire bundle.
    """
    import tempfile

    out_path = build_root / f"{pem_path.stem}.p7b"
    # Nuke stale output to avoid confusion
    if out_path.exists():
        out_path.unlink()

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)
    if not blocks:
        print(f"[WARN] No certificates found in {pem_path}; skipping P7B.")
        return

    with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
        tmp.write("".join(blocks))
        tmp.flush()
        cmd = [
            "openssl", "crl2pkcs7",
            "-nocrl",
            "-certfile", tmp.name,      # ← key change
            "-out", str(out_path),
            "-outform", "DER",
        ]
        subprocess.run(cmd, check=True)
    print(f"[INFO] Created P7B: {out_path}")


def create_jks(pem_path: Path, build_root: Path, overrides: dict):
    """
    Create a Java KeyStore (JKS) from a PEM bundle.
    Imports each certificate individually with alias naming controlled by alias_format.
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    import tempfile

    alias_format = overrides.get("alias_format", "{subject.CN}-{serial}")
    storepass_env = overrides.get("storepass_env", "TRUST_JKS_PASSWORD")
    storepass = os.environ.get(storepass_env) or "changeit"

    out_path = build_root / f"{pem_path.stem}.jks"
    # Remove existing keystore to avoid duplicate aliases across runs
    if out_path.exists():
        out_path.unlink()

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)

    with tempfile.TemporaryDirectory() as td:
        for idx, blk in enumerate(blocks, 1):
            try:
                cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
                cn = _get_cn(cert)
                serial = f"{cert.serial_number:X}"
                alias = _format_alias(alias_format, cn, serial)
                alias = _sanitize_alias(alias)

                tmp_pem = Path(td) / f"cert{idx}.pem"
                tmp_pem.write_text(blk, encoding="utf-8")

                cmd = [
                    "keytool", "-importcert",
                    "-noprompt",
                    "-alias", alias,
                    "-file", str(tmp_pem),
                    "-keystore", str(out_path),
                    "-storepass", storepass,
                ]
                subprocess.run(cmd, check=True)
                print(f"[INFO] Imported cert {idx}: {alias}")
            except Exception as e:
                print(f"[ERROR] Failed to import cert {idx}: {e}")

    print(f"[INFO] Created JKS: {out_path}")


def create_pkcs12(pem_path: Path, build_root: Path, overrides: dict):
    """
    Create a single PKCS#12 (.p12) containing ALL certificates from the PEM bundle.

    Use: -in (first cert) + -certfile (rest) to include entire set.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import tempfile

    alias_format = overrides.get("alias_format", "{subject.CN}-{serial}")
    password_env = overrides.get("password_env", "TRUST_P12_PASSWORD")
    password = os.environ.get(password_env) or "changeit"

    out_path = build_root / f"{pem_path.stem}.p12"
    # Remove existing to avoid stale results
    if out_path.exists():
        out_path.unlink()

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)
    if not blocks:
        print(f"[WARN] No certificates found in {pem_path}; skipping PKCS#12.")
        return

    # First + rest strategy
    first_pem = blocks[0]
    rest_pems = blocks[1:]

    with tempfile.TemporaryDirectory() as td:
        first_file = Path(td) / "first.pem"
        first_file.write_text(first_pem, encoding="utf-8")

        rest_file = None
        if rest_pems:
            rest_file = Path(td) / "rest.pem"
            rest_file.write_text("".join(rest_pems), encoding="utf-8")

        # Alias from the first cert
        first_cert = x509.load_pem_x509_certificate(first_pem.encode(), default_backend())
        cn = _get_cn(first_cert)
        serial = f"{first_cert.serial_number:X}"
        alias = _format_alias(alias_format, cn, serial)
        alias = _sanitize_alias(alias)

        cmd = [
            "openssl", "pkcs12", "-export",
            "-nokeys",
            "-in", str(first_file),
            "-out", str(out_path),
            "-passout", f"pass:{password}",
            "-name", alias,
        ]
        if rest_file:
            cmd[6:6] = ["-certfile", str(rest_file)]  # insert before -out

        subprocess.run(cmd, check=True)

    print(f"[INFO] Created PKCS#12: {out_path}")


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

def _split_pem_blocks(text: str) -> list[str]:
    start, end = "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"
    blocks, buf, inside = [], [], False
    for line in text.splitlines():
        if start in line:
            inside, buf = True, [line]
        elif end in line and inside:
            buf.append(line)
            blocks.append("\n".join(buf) + "\n")
            inside = False
        elif inside:
            buf.append(line)
    return blocks


def _get_cn(cert) -> str:
    """Extract CN or fallback to short subject string."""
    try:
        for attr in cert.subject:
            if attr.oid.dotted_string == "2.5.4.3":  # Common Name
                return attr.value
    except Exception:
        pass
    return cert.subject.rfc4514_string()[:64]


def _sanitize_alias(alias: str) -> str:
    """Make alias keytool/openssl safe."""
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in alias)[:80]


def _format_alias(template: str, cn: str, serial: str) -> str:
    """Replace {subject.CN} and {serial} placeholders safely."""
    cn = cn or "Unknown_CN"
    try:
        return (
            template
            .replace("{subject.CN}", cn)
            .replace("{serial}", serial)
        )
    except Exception:
        return f"{cn}-{serial}"
