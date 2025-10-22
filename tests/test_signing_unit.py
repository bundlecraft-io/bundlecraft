"""Unit tests for bundlecraft.helpers.signing using a fake gnupg backend.

Covers success/invalid verification paths, keyring import failure,
and missing file error handling without requiring real GPG.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from bundlecraft.helpers import signing


class FakeGPG:
    def __init__(self, *args, **kwargs):
        self._import_count = 1
        self._verify_valid = True
        self._verify_status = "OK"
        self._verify_key_id = "DEADBEEF"
        self._verify_username = "Test User <test@example.com>"

    # Used by sign_file path (not tested here)
    def sign(self, *args, **kwargs):  # pragma: no cover - not exercised here
        return SimpleNamespace(data=b"sig", stderr="")

    def import_keys(self, data: bytes):
        return SimpleNamespace(count=self._import_count)

    def verify_data(self, signature: bytes, data: bytes):
        return SimpleNamespace(
            valid=self._verify_valid,
            status=self._verify_status,
            key_id=self._verify_key_id,
            username=self._verify_username,
        )


@pytest.fixture
def tmp_file(tmp_path: Path) -> Path:
    p = tmp_path / "file.pem"
    p.write_text("data")
    (tmp_path / "file.pem.asc").write_text("sig")
    return p


def test_verify_signature_success(monkeypatch, tmp_file):
    fake = FakeGPG()

    def fake_get_gpg_instance(_home=None):
        return fake

    monkeypatch.setattr(signing, "get_gpg_instance", fake_get_gpg_instance)

    ok, msg = signing.verify_signature(tmp_file)
    assert ok is True
    assert "Valid signature" in msg
    assert fake._verify_key_id in msg


def test_verify_signature_invalid(monkeypatch, tmp_file):
    fake = FakeGPG()
    fake._verify_valid = False
    fake._verify_status = "BAD"

    def fake_get_gpg_instance(_home=None):
        return fake

    monkeypatch.setattr(signing, "get_gpg_instance", fake_get_gpg_instance)

    ok, msg = signing.verify_signature(tmp_file)
    assert ok is False
    assert "Invalid signature" in msg
    assert "BAD" in msg


def test_verify_signature_missing_files(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        signing.verify_signature(tmp_path / "missing.pem")

    f = tmp_path / "f.pem"
    f.write_text("x")
    with pytest.raises(FileNotFoundError):
        signing.verify_signature(f)  # missing .asc


def test_verify_signature_keyring_import_failure(monkeypatch, tmp_file, tmp_path: Path):
    fake = FakeGPG()
    fake._import_count = 0  # simulate import failure

    def fake_get_gpg_instance(_home=None):
        return fake

    monkeypatch.setattr(signing, "get_gpg_instance", fake_get_gpg_instance)

    keyring = tmp_path / "pubring.gpg"
    keyring.write_bytes(b"pubkey")

    ok, msg = signing.verify_signature(tmp_file, keyring=keyring)
    assert ok is False
    assert "Failed to import keys" in msg
