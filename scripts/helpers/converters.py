from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Dict, List
import re

def convert_to_formats(input_pem: Path, output_dir: Path, formats: List[str], overrides: Dict) -> None:
    for fmt in [f.lower() for f in formats]:
        if fmt == "p7b":
            convert_to_p7b(input_pem, output_dir / "ca-trust.p7b")
        elif fmt == "der":
            convert_to_der_bundle(input_pem, output_dir / "ca-trust.der")
        elif fmt == "jks":
            pw = (overrides.get("jks") or {}).get("keystore_password") or "changeit"
            convert_to_jks(input_pem, output_dir / "ca-trust.jks", password=pw)
        else:
            print(f"[WARN] Unknown format requested: {fmt} (skipping)")

def _which(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None

def convert_to_p7b(input_pem: Path, output_file: Path) -> None:
    if not _which("openssl"):
        print("[WARN] openssl not found in PATH; skipping PKCS#7 conversion.")
        return
    cmd = [
        "openssl", "crl2pkcs7",
        "-nocrl", "-certfile", str(input_pem),
        "-outform", "DER", "-out", str(output_file)
    ]
    print(f"[INFO] Converting PEM → P7B")
    subprocess.run(cmd, check=False)
    if output_file.exists():
        print(f"[INFO] Wrote: {output_file}")

def convert_to_der_bundle(input_pem: Path, output_file: Path) -> None:
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        print("[WARN] cryptography not installed; skipping DER conversion.")
        return
    text = input_pem.read_text(encoding="utf-8", errors="ignore")
    start, end = "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"
    if start not in text or end not in text:
        print("[WARN] No certificate found for DER conversion.")
        return
    first = text[text.index(start): text.index(end) + len(end)] + "\n"
    cert = x509.load_pem_x509_certificate(first.encode(), default_backend())
    output_file.write_bytes(cert.public_bytes(encoding=x509.Encoding.DER))
    print(f"[INFO] Wrote: {output_file}")

def convert_to_jks(input_pem: Path, output_file: Path, password: str = "changeit") -> None:
    if not _which("keytool"):
        print("[WARN] keytool not found in PATH; skipping JKS conversion.")
        return

    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    text = input_pem.read_text(encoding="utf-8", errors="ignore")
    blocks = re.findall(
        r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
        text, flags=re.S
    )
    tmp_dir = output_file.parent / ".tmp_jks"
    tmp_dir.mkdir(exist_ok=True)
    aliases = set()

    def make_alias(cert: x509.Certificate) -> str:
        cn = None
        try:
            cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        except Exception:
            cn = "Unknown"
        alias = re.sub(r"[^A-Za-z0-9_-]", "", cn) or "Unknown"
        base = alias
        i = 1
        while alias in aliases:
            i += 1
            alias = f"{base}_{i}"
        aliases.add(alias)
        return alias

    if output_file.exists():
        output_file.unlink()

    for i, body in enumerate(blocks, 1):
        pem = f"-----BEGIN CERTIFICATE-----{body}-----END CERTIFICATE-----\n"
        try:
            cert = x509.load_pem_x509_certificate(pem.encode(), default_backend())
        except Exception:
            continue
        alias = make_alias(cert)
        pem_file = tmp_dir / f"{alias}.pem"
        pem_file.write_text(pem, encoding="utf-8")
        cmd = [
            "keytool", "-importcert", "-noprompt",
            "-alias", alias,
            "-file", str(pem_file),
            "-keystore", str(output_file),
            "-storepass", password
        ]
        print(f"[INFO] keytool import alias: {alias}")
        subprocess.run(cmd, check=False)

    for f in tmp_dir.glob("*.pem"):
        f.unlink()
    tmp_dir.rmdir()

    if output_file.exists():
        print(f"[INFO] Wrote: {output_file}")
