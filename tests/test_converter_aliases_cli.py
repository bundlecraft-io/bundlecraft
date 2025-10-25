"""End-to-end CLI tests for converter alias handling (.crt/.cer/.p7c)."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from bundlecraft.converter import main as convert_main


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.mark.parametrize("ext", ["crt", "cer"])
def test_cli_convert_accepts_crt_cer(cli_runner, tmp_path: Path, sample_cert_path: Path, ext: str):
    # Prepare input with .crt/.cer extension using valid PEM contents
    inp = tmp_path / f"input.{ext}"
    inp.write_text(Path(sample_cert_path).read_text(encoding="utf-8"), encoding="utf-8")
    outdir = tmp_path / "out"
    outdir.mkdir()

    result = cli_runner.invoke(
        convert_main,
        [
            "--input",
            str(inp),
            "--output-dir",
            str(outdir),
            "--output-format",
            "pem",
            "--output-basename",
            "alias-cli-test",
        ],
    )

    # Success pathway or graceful handling of environment (keep consistent with existing tests)
    assert result.exit_code in [0]
    # Output file should exist with the explicit basename
    assert (outdir / "alias-cli-test.pem").exists()


def test_cli_convert_accepts_p7c(cli_runner, tmp_path: Path, sample_cert_path: Path, monkeypatch):
    # Prepare dummy .p7c file
    p7c_file = tmp_path / "bundle.p7c"
    p7c_file.write_bytes(b"irrelevant")

    # Create a real certificate object to return via pkcs7 loader
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    cert = x509.load_pem_x509_certificate(Path(sample_cert_path).read_bytes(), default_backend())

    # Monkeypatch the pkcs7 loader to return our cert list (simulate valid pkcs7)
    from bundlecraft.helpers import convert_utils as cu

    monkeypatch.setattr(cu.pkcs7, "load_pem_pkcs7_certificates", lambda data: [cert])

    outdir = tmp_path / "out"
    outdir.mkdir()

    result = cli_runner.invoke(
        convert_main,
        [
            "--input",
            str(p7c_file),
            "--output-dir",
            str(outdir),
            "--output-format",
            "pem",
            "--output-basename",
            "alias-cli-test",
        ],
    )

    assert result.exit_code in [0]
    assert (outdir / "alias-cli-test.pem").exists()
