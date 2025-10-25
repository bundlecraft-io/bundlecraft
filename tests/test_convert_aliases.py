"""Tests for format alias handling in convert_utils.normalize_to_pem.

Covers:
- .crt and .cer treated as PEM
- .p7c treated as PKCS#7 (alias of p7b)
"""

from pathlib import Path

import pytest

from bundlecraft.helpers.convert_utils import normalize_to_pem


def _read_fixture_cert(name: str) -> str:
    here = Path(__file__).parent / "data" / "certs" / name
    return here.read_text(encoding="utf-8")


@pytest.mark.parametrize("ext", ["crt", "cer"])
def test_normalize_alias_pem_extensions(tmp_path: Path, ext: str):
    """.crt and .cer should be treated as PEM inputs."""
    pem_text = _read_fixture_cert("sample.pem")
    inp = tmp_path / f"sample.{ext}"
    inp.write_text(pem_text, encoding="utf-8")

    out_pem = tmp_path / "out.pem"
    out, has_keys = normalize_to_pem(inp, out_pem)

    assert out == out_pem
    text = out.read_text(encoding="utf-8")
    assert "BEGIN CERTIFICATE" in text
    assert "PRIVATE KEY" not in text
    assert has_keys is False


def test_normalize_p7c_alias_to_p7b(tmp_path: Path, monkeypatch):
    """.p7c should be handled via the PKCS#7 loader (alias of p7b)."""
    pem_text = _read_fixture_cert("valid-root.pem")

    # Create a real x509.Certificate from PEM for the mocked loader to return
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    cert = x509.load_pem_x509_certificate(pem_text.encode(), default_backend())

    # Mock pkcs7 loader to return our certificate list regardless of input bytes
    from bundlecraft.helpers import convert_utils as cu

    monkeypatch.setattr(cu.pkcs7, "load_pem_pkcs7_certificates", lambda data: [cert])

    # Write a dummy .p7c file (content is irrelevant due to mocking)
    inp = tmp_path / "bundle.p7c"
    inp.write_bytes(b"dummy-pkcs7")

    out_pem = tmp_path / "out.pem"
    out, has_keys = normalize_to_pem(inp, out_pem)

    assert out == out_pem
    text = out.read_text(encoding="utf-8")
    assert "BEGIN CERTIFICATE" in text
    assert has_keys is False
