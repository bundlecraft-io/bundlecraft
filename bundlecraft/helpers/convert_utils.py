#!/usr/bin/env python3
"""
convert_utils.py
Handles format conversions for BundleCraft bundles.

IMPORTANT: BundleCraft processes CERTIFICATES and PUBLIC KEYS ONLY.
           Private keys are explicitly NOT supported and will be ignored if encountered.
           If you need private keys in your bundles, add them securely via external tooling.

Supports (inputs → outputs):
  • Inputs: PEM, DER, PKCS#7 (.p7b), Java KeyStore (.jks), PKCS#12 (.p12/.pfx)
  • Outputs: PEM, PKCS#7 (.p7b), JKS, PKCS#12 (.p12/.pfx), ZIP (tarball of PEMs)
  • Note: DER is accepted as input only (not output) - use P7B for binary bundle output

Strategy:
  1) Normalize any input into a canonical PEM bundle (certificates only).
  2) Reuse existing writers to emit bundle formats from that PEM bundle.
  3) Private keys are ignored and excluded from all operations.
"""

import os
import tarfile
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, pkcs7, pkcs12

# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def convert_to_formats(
    pem_path: Path,
    build_root: Path,
    formats: list[str],
    fmt_overrides: dict | None = None,
    output_basename: str | None = None,
    dry_run: bool = False,
):
    """
    Convert a canonical PEM bundle into one or more bundle formats.

    Args:
        pem_path (Path): Input PEM file path
        build_root (Path): Output directory
        formats (list[str]): Bundle formats (e.g., ["p7b", "jks", "p12"])
        fmt_overrides (dict|None): Optional per-format overrides (alias/password settings)
        output_basename (str|None): Base name for output files (default: input file stem)
        dry_run (bool): If True, show what would be done without executing
    """
    fmt_overrides = fmt_overrides or {}
    if output_basename is None:
        output_basename = pem_path.stem
    norm = [f.lower() for f in formats]

    for fmt in norm:
        if fmt in ("pem",):
            # Just copy/normalize the PEM into the output directory
            out_path = build_root / f"{output_basename}.pem"
            if dry_run:
                print(f"[dry-run] Would write PEM: {out_path}")
                continue
            if out_path.exists() and not fmt_overrides.get("force", False):
                raise FileExistsError(f"Output file exists: {out_path}. Use --force to overwrite.")
            # Proactively remove when forcing to avoid partial/append behaviors
            if out_path.exists() and fmt_overrides.get("force", False):
                try:
                    out_path.unlink()
                except Exception:
                    pass
            out_path.write_text(
                pem_path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8"
            )
            print(f"[INFO] Wrote PEM: {out_path}")
        elif fmt in ("p7b", "pkcs7"):
            if dry_run:
                print(f"[dry-run] Would create P7B: {build_root / f'{output_basename}.p7b'}")
                continue
            create_p7b(
                pem_path, build_root, output_basename, force=fmt_overrides.get("force", False)
            )
        elif fmt == "jks":
            if dry_run:
                print(f"[dry-run] Would create JKS: {build_root / f'{output_basename}.jks'}")
                continue
            create_jks(
                pem_path,
                build_root,
                output_basename,
                fmt_overrides.get("jks", {}),
                force=fmt_overrides.get("force", False),
            )
        elif fmt in ("p12", "pfx", "pkcs12"):
            if dry_run:
                print(f"[dry-run] Would create PKCS12: {build_root / f'{output_basename}.p12'}")
                continue
            create_pkcs12(
                pem_path,
                build_root,
                output_basename,
                fmt_overrides.get("pkcs12", {}),
                force=fmt_overrides.get("force", False),
            )
        elif fmt == "zip":
            if dry_run:
                print(f"[dry-run] Would create ZIP: {build_root / f'{output_basename}.zip'}")
                continue
            create_zip(
                pem_path, build_root, output_basename, force=fmt_overrides.get("force", False)
            )
        else:
            print(f"[WARN] Unknown format requested: {fmt}")


# ---------------------------------------------------------------------
# ZIP output (tarball of PEMs)
# ---------------------------------------------------------------------


def create_zip(pem_path: Path, build_root: Path, output_basename: str, force: bool = False):
    """
    Create a deterministic tarball (zip) containing each certificate as an individual PEM file.
    Filenames: {subject.CN}-{thumbprint}.pem

    Creates a deterministic archive with:
    - mtime=0 (epoch time)
    - uid=0, gid=0
    - uname='', gname=''
    - Sorted entries for consistent ordering
    - gzip mtime=0 for deterministic compression
    """
    import gzip
    import io

    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)
    if not blocks:
        print(f"[WARN] No certificates found in {pem_path}; skipping ZIP.")
        return

    tar_path = build_root / f"{output_basename}.tar.gz"
    if tar_path.exists() and not force:
        raise FileExistsError(f"Output file exists: {tar_path}. Use --force to overwrite.")

    # Collect all certificate data first, sorted by filename for determinism
    cert_files = []
    for blk in blocks:
        cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
        cn = _get_cn(cert)
        # Use SHA256 thumbprint for uniqueness
        from cryptography.hazmat.primitives import hashes

        thumb = cert.fingerprint(hashes.SHA256()).hex()[:16]
        safe_cn = _sanitize_alias(cn)
        fname = f"{safe_cn}-{thumb}.pem"
        cert_files.append((fname, blk))

    # Sort by filename for deterministic ordering
    cert_files.sort(key=lambda x: x[0])

    # Create tar in memory first
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for fname, blk in cert_files:
            # Write PEM to temp file for tar
            with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
                tmp.write(blk)
                tmp.flush()

                # Create TarInfo with normalized metadata for determinism
                tarinfo = tar.gettarinfo(tmp.name, arcname=fname)
                tarinfo.mtime = 0  # Epoch time for determinism
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.uname = ""
                tarinfo.gname = ""
                if tarinfo.pax_headers:
                    for key in ("atime", "ctime"):
                        tarinfo.pax_headers.pop(key, None)

                # Add file with normalized metadata
                with open(tmp.name, "rb") as f:
                    tar.addfile(tarinfo, f)
            os.unlink(tmp.name)

    # Write compressed tar with mtime=0 for gzip determinism
    tar_buffer.seek(0)
    with gzip.GzipFile(filename="", fileobj=open(tar_path, "wb"), mode="wb", mtime=0) as gz:
        gz.write(tar_buffer.read())

    print(f"[INFO] Created ZIP tarball: {tar_path}")


def convert_from_any(
    input_path: Path,
    output_dir: Path,
    formats: list[str],
    *,
    input_format: str | None = None,
    password: str | None = None,
    verbose: bool = False,
    force: bool = False,
    output_basename: str | None = None,
) -> None:
    """
    Normalize arbitrary input (PEM/P7B/JKS/P12) to a canonical PEM and convert to targets.

    IMPORTANT: Private keys are NEVER processed. Only certificates are extracted.
    - Password, if required, must be provided via env/argument; no prompting here.
    """
    base_name = input_path.stem
    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        pem_path, has_keys = normalize_to_pem(
            input_path,
            tmp_dir / f"{base_name}.pem",
            input_format=input_format,
            password=password,
            verbose=verbose,
        )
        if has_keys and verbose:
            print(
                "[WARN] Private key(s) detected in input and ignored (BundleCraft handles certificates only)"
            )

        fmt_overrides = {
            "pkcs12": {
                "password": password or os.environ.get("TRUST_P12_PASSWORD") or "changeit",
            },
            "jks": {
                "storepass": os.environ.get("TRUST_JKS_PASSWORD") or "changeit",
            },
            "force": force,
        }
        # Perform conversions while the normalized PEM exists
        convert_to_formats(pem_path, output_dir, formats, fmt_overrides, output_basename)


# ---------------------------------------------------------------------
# Conversion helpers (writers)
# ---------------------------------------------------------------------


def create_der(pem_path: Path, build_root: Path):
    """
    Convert PEM → DER (binary certificate format).

    If input has multiple certificates, creates multiple .der files (cert1.der, cert2.der, etc).
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)
    if not blocks:
        print(f"[WARN] No certificates found in {pem_path}; skipping DER.")
        return

    if len(blocks) == 1:
        # Single cert: use same base name
        out_path = build_root / f"{pem_path.stem}.der"
        if out_path.exists():
            out_path.unlink()
        cert = x509.load_pem_x509_certificate(blocks[0].encode(), default_backend())
        out_path.write_bytes(cert.public_bytes(Encoding.DER))
        print(f"[INFO] Created DER: {out_path}")
    else:
        # Multiple certs: create numbered files
        for idx, blk in enumerate(blocks, 1):
            out_path = build_root / f"{pem_path.stem}-cert{idx}.der"
            if out_path.exists():
                out_path.unlink()
            cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
            out_path.write_bytes(cert.public_bytes(Encoding.DER))
            print(f"[INFO] Created DER: {out_path}")


def create_p7b(pem_path: Path, build_root: Path, output_basename: str, force: bool = False):
    """
    Convert PEM → PKCS#7 (.p7b, DER) including ALL certs.

    Uses Python cryptography module to create PKCS#7 bundle.
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    out_path = build_root / f"{output_basename}.p7b"
    if out_path.exists() and not force:
        raise FileExistsError(f"Output file exists: {out_path}. Use --force to overwrite.")
    if out_path.exists() and force:
        try:
            out_path.unlink()
        except Exception:
            pass

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)
    if not blocks:
        print(f"[WARN] No certificates found in {pem_path}; skipping P7B.")
        return

    # Load all certificates from PEM blocks
    certs = []
    for blk in blocks:
        try:
            cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
            certs.append(cert)
        except Exception as e:
            print(f"[WARN] Failed to load certificate: {e}")
            continue

    if not certs:
        print(f"[WARN] No valid certificates found in {pem_path}; skipping P7B.")
        return

    # Create PKCS#7 bundle using cryptography
    from cryptography.hazmat.primitives.serialization import Encoding

    p7b_data = pkcs7.serialize_certificates(certs, Encoding.DER)
    out_path.write_bytes(p7b_data)

    print(f"[INFO] Created P7B: {out_path}")


def create_jks(
    pem_path: Path, build_root: Path, output_basename: str, overrides: dict, force: bool = False
):
    """
    Create a Java KeyStore (JKS) from a PEM bundle using pyjks.
    Imports each certificate individually with alias naming controlled by alias_format.
    """
    import jks
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    alias_format = overrides.get("alias_format", "{subject.CN}-{fingerprint}")
    storepass = (
        overrides.get("storepass")
        or os.environ.get(overrides.get("storepass_env", "TRUST_JKS_PASSWORD"))
        or "changeit"
    )

    out_path = build_root / f"{output_basename}.jks"
    if out_path.exists() and not force:
        raise FileExistsError(f"Output file exists: {out_path}. Use --force to overwrite.")
    if out_path.exists() and force:
        try:
            out_path.unlink()
        except Exception:
            pass

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)

    # Create a new JKS keystore
    keystore = jks.KeyStore.new("jks", [])

    for idx, blk in enumerate(blocks, 1):
        try:
            cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
            cn = _get_cn(cert)
            serial = f"{cert.serial_number:X}"
            from cryptography.hazmat.primitives import hashes

            fp_sha256 = cert.fingerprint(hashes.SHA256()).hex()
            fp_sha1 = cert.fingerprint(hashes.SHA1()).hex()
            alias = _format_alias(
                alias_format,
                cn,
                serial,
                fingerprint_sha1=fp_sha1,
                fingerprint_sha256=fp_sha256,
            )
            alias = _sanitize_alias(alias)

            # Convert PEM to DER for pyjks
            cert_der = cert.public_bytes(Encoding.DER)

            # Create a trusted certificate entry
            cert_entry = jks.TrustedCertEntry.new(alias, cert_der)
            keystore.entries[alias] = cert_entry

            print(f"  [JKS] ✓ Imported: {alias}")
        except Exception as e:
            print(f"  [JKS] ✗ Failed to import cert {idx}: {e}")

    # Save the keystore
    keystore.save(str(out_path), storepass)

    print(f"[INFO] Created JKS: {out_path}")


def create_pkcs12(
    pem_path: Path, build_root: Path, output_basename: str, overrides: dict, force: bool = False
):
    """
    Create a single PKCS#12 (.p12) containing ALL certificates from the PEM bundle.

    IMPORTANT: Private keys are NOT supported. Only certificates are included.
    Uses Python cryptography module to create PKCS#12 file.
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import (
        BestAvailableEncryption,
        NoEncryption,
    )

    alias_format = overrides.get("alias_format", "{subject.CN}-{fingerprint}")
    password = (
        overrides.get("password")
        or os.environ.get(overrides.get("password_env", "TRUST_P12_PASSWORD"))
        or "changeit"
    )

    out_path = build_root / f"{output_basename}.p12"
    if out_path.exists() and not force:
        raise FileExistsError(f"Output file exists: {out_path}. Use --force to overwrite.")
    if out_path.exists() and force:
        try:
            out_path.unlink()
        except Exception:
            pass

    text = pem_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_pem_blocks(text)
    if not blocks:
        print(f"[WARN] No certificates found in {pem_path}; skipping PKCS#12.")
        return

    # Load all certificates
    certs = []
    for blk in blocks:
        try:
            cert = x509.load_pem_x509_certificate(blk.encode(), default_backend())
            certs.append(cert)
        except Exception as e:
            print(f"[WARN] Failed to load certificate: {e}")
            continue

    if not certs:
        print(f"[WARN] No valid certificates found in {pem_path}; skipping PKCS#12.")
        return

    # Get alias from the first cert for naming
    first_cert = certs[0]
    cn = _get_cn(first_cert)
    serial = f"{first_cert.serial_number:X}"
    from cryptography.hazmat.primitives import hashes

    fp_sha256 = first_cert.fingerprint(hashes.SHA256()).hex()
    fp_sha1 = first_cert.fingerprint(hashes.SHA1()).hex()
    alias = _format_alias(
        alias_format,
        cn,
        serial,
        fingerprint_sha1=fp_sha1,
        fingerprint_sha256=fp_sha256,
    )
    alias = _sanitize_alias(alias)

    # Create PKCS#12 with no private key (certificates only)
    # When there's no private key, all certs go into the cas parameter
    encryption = BestAvailableEncryption(password.encode()) if password else NoEncryption()

    p12_data = pkcs12.serialize_key_and_certificates(
        name=alias.encode(),
        key=None,  # No private key
        cert=None,  # No primary cert (would require private key)
        cas=certs,  # All certificates as additional certs
        encryption_algorithm=encryption,
    )

    out_path.write_bytes(p12_data)
    print(f"[INFO] Created PKCS#12: {out_path}")


# ---------------------------------------------------------------------
# Normalization helpers (readers)
# ---------------------------------------------------------------------


def normalize_to_pem(
    input_path: Path,
    output_pem_path: Path,
    *,
    input_format: str | None = None,
    password: str | None = None,
    verbose: bool = False,
) -> tuple[Path, bool]:
    """
    Load input of various types and produce a canonical PEM bundle on disk (certificates only).

    IMPORTANT: Private keys are NEVER included. Only certificates are extracted.

    Returns (pem_path, has_private_keys) where has_private_keys indicates if keys were encountered and ignored.
    """
    fmt = (input_format or input_path.suffix.lstrip(".")).lower()
    # Normalize common aliases
    if fmt in {"pfx", "pkcs12"}:
        fmt = "p12"
    if fmt in {"pkcs7", "p7c"}:
        fmt = "p7b"
    # Many distros use .crt/.cer for PEM-encoded certs
    if fmt in {"crt", "cer"}:
        fmt = "pem"

    has_keys = False

    if fmt == "pem":
        text = input_path.read_text(encoding="utf-8", errors="ignore")
        certs = _split_pem_blocks(text)
        keys = _split_pem_key_blocks(text)
        if not certs:
            raise ValueError("No certificates found in PEM input")
        if keys:
            has_keys = True
        # Write certificates ONLY
        output_pem_path.write_text("".join(certs), encoding="utf-8")
        return output_pem_path, has_keys

    if fmt == "der":
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        data = input_path.read_bytes()
        try:
            # Try loading as a single DER certificate
            cert = x509.load_der_x509_certificate(data, default_backend())
            pem_block = cert.public_bytes(Encoding.PEM).decode("utf-8")
            output_pem_path.write_text(pem_block, encoding="utf-8")
            return output_pem_path, False
        except Exception as e:
            raise ValueError(f"Failed to load DER certificate: {e}") from e

    if fmt == "p7b":
        data = input_path.read_bytes()
        try:
            certs = pkcs7.load_pem_pkcs7_certificates(data)
        except ValueError:
            certs = pkcs7.load_der_pkcs7_certificates(data)
        if not certs:
            raise ValueError("No certificates found in PKCS#7 input")
        pem_blocks = [c.public_bytes(Encoding.PEM).decode("utf-8") for c in certs]
        output_pem_path.write_text("".join(pem_blocks), encoding="utf-8")
        return output_pem_path, False

    if fmt == "p12":
        data = input_path.read_bytes()
        pw = password or os.environ.get("TRUST_P12_PASSWORD")
        if pw is None:
            raise ValueError(
                "Password required for PKCS#12 input; set TRUST_P12_PASSWORD or provide --password"
            )
        # cryptography expects bytes for password
        pw_bytes = pw.encode()
        pkey, cert, addl = pkcs12.load_key_and_certificates(data, password=pw_bytes)
        certs = []
        if cert:
            certs.append(cert)
        if addl:
            certs.extend(addl)
        if not certs:
            raise ValueError("No certificates found in PKCS#12 input")
        # Check if private key was present
        if pkey is not None:
            has_keys = True
        # Write certificates ONLY (never include private key)
        pem_blocks = [c.public_bytes(Encoding.PEM).decode("utf-8") for c in certs]
        output_pem_path.write_text("".join(pem_blocks), encoding="utf-8")
        return output_pem_path, has_keys

    if fmt == "jks":
        import jks
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        pw = password or os.environ.get("TRUST_JKS_PASSWORD")
        if pw is None:
            raise ValueError(
                "Password required for JKS input; set TRUST_JKS_PASSWORD or provide --password"
            )

        # Load JKS using pyjks
        try:
            keystore = jks.KeyStore.load(str(input_path), pw)
        except Exception as e:
            raise RuntimeError(f"Failed to read JKS: {e}") from e

        # Extract certificates
        pem_blocks = []
        for alias, entry in keystore.entries.items():
            if isinstance(entry, jks.TrustedCertEntry):
                # Convert DER to PEM
                try:
                    cert = x509.load_der_x509_certificate(entry.cert, default_backend())
                    pem_block = cert.public_bytes(Encoding.PEM).decode("utf-8")
                    pem_blocks.append(pem_block)
                except Exception as e:
                    print(f"[WARN] Failed to load certificate '{alias}': {e}")
            elif isinstance(entry, jks.PrivateKeyEntry):
                # Private key entry detected - we skip the key but may extract cert chain
                has_keys = True
                # Try to extract certificate chain if available
                for cert_der in entry.cert_chain:
                    try:
                        cert = x509.load_der_x509_certificate(cert_der[1], default_backend())
                        pem_block = cert.public_bytes(Encoding.PEM).decode("utf-8")
                        pem_blocks.append(pem_block)
                    except Exception as e:
                        print(f"[WARN] Failed to load certificate from chain in '{alias}': {e}")

        if not pem_blocks:
            raise ValueError("No certificates found in JKS input")

        # Write certificates ONLY
        output_pem_path.write_text("".join(pem_blocks), encoding="utf-8")
        return output_pem_path, has_keys

    raise ValueError(f"Unsupported input format: {fmt}")


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


def _split_pem_key_blocks(text: str) -> list[str]:
    start, end = "-----BEGIN", "PRIVATE KEY-----"
    blocks, buf, inside = [], [], False
    for line in text.splitlines():
        if line.startswith(start) and end in line:
            inside, buf = True, [line]
        elif line.startswith("-----END") and end in line and inside:
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


def _format_alias(
    template: str,
    cn: str,
    serial: str,
    *,
    fingerprint_sha1: str | None = None,
    fingerprint_sha256: str | None = None,
) -> str:
    """Replace placeholders in alias templates safely.

    Supported placeholders:
      - {subject.CN}
      - {serial}
      - {fingerprint} (alias for {fingerprint_sha256})
      - {fingerprint_sha1}
      - {fingerprint_sha256}
    """
    cn = cn or "Unknown_CN"
    fp1 = fingerprint_sha1 or ""
    fp256 = fingerprint_sha256 or ""
    try:
        out = template
        out = out.replace("{subject.CN}", cn).replace("{serial}", serial)
        out = out.replace("{fingerprint_sha1}", fp1).replace("{fingerprint_sha256}", fp256)
        out = out.replace("{fingerprint}", fp256)
        return out
    except Exception:
        return f"{cn}-{serial}"
