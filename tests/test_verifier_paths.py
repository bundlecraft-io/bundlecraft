import json
import logging
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from bundlecraft.verifier import CHECKSUM_FILE, verify_directory
from bundlecraft.verifier import main as verifier_main


def write_checksums(dirpath: Path, mapping: dict[str, str]) -> None:
    lines = [f"{h}  {name}\n" for name, h in mapping.items()]
    (dirpath / CHECKSUM_FILE).write_text("".join(lines), encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


class TestVerifyDirectory:
    def test_missing_checksums_file_fails(self, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        build = tmp_path / "build"
        build.mkdir()
        ok = verify_directory(build)
        assert ok is False
        # Error logged about missing checksums
        assert any("Missing checksums.sha256" in r.message for r in caplog.records)

    def test_success_with_matching_hashes_and_counts(self, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        build = tmp_path / "build"
        build.mkdir()
        # Create one PEM and one non-deterministic artifact to be skipped
        pem = build / "bundle.pem"
        pem.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
        (build / "package.tar.gz").write_bytes(b"tarball")
        # Checksums
        checksums = {pem.name: sha256_bytes(pem.read_bytes())}
        write_checksums(build, checksums)
        # Run verify
        ok = verify_directory(build, verbose=True, check_counts=True)
        assert ok is True
        assert any("verified successfully" in r.message for r in caplog.records)
        # Skipped artifact noted
        assert any("Skipping package.tar.gz" in r.message for r in caplog.records)
        # Cert counts logged
        assert any("Certificate count" in r.message for r in caplog.records)

    def test_hash_mismatch_detected(self, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        build = tmp_path / "build"
        build.mkdir()
        pem = build / "bundle.pem"
        pem.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
        write_checksums(build, {pem.name: "0" * 64})
        ok = verify_directory(build, verbose=True)
        assert ok is False
        assert any("hash mismatch" in r.message.lower() for r in caplog.records)

    def test_missing_checksum_entry_warns(self, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        build = tmp_path / "build"
        build.mkdir()
        pem = build / "bundle.pem"
        pem.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
        write_checksums(build, {})
        ok = verify_directory(build, verbose=False)
        assert ok is True  # no failure, just a warning
        assert any("No checksum entry" in r.message for r in caplog.records)

    @patch("bundlecraft.verifier.count_certs_in_store", return_value=1)
    def test_count_mismatch_warning(self, mock_count, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        build = tmp_path / "build"
        build.mkdir()
        # Two files with different counts injected
        a = build / "a.pem"
        a.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
        b = build / "b.pem"
        b.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
        write_checksums(
            build,
            {
                a.name: sha256_bytes(a.read_bytes()),
                b.name: sha256_bytes(b.read_bytes()),
            },
        )
        # First call returns 1, second call return 2
        mock_count.side_effect = [1, 2]
        ok = verify_directory(build, verbose=False, check_counts=True)
        assert ok is True
        assert any("count mismatch" in r.message for r in caplog.records)

    @patch("bundlecraft.verifier.count_certs_in_store", return_value=0)
    def test_all_zero_counts_warning(self, _mock, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        build = tmp_path / "build"
        build.mkdir()
        a = build / "a.pem"
        a.write_text("")
        write_checksums(build, {a.name: sha256_bytes(a.read_bytes())})
        ok = verify_directory(build, verbose=False, check_counts=True)
        assert ok is True
        assert any("appear empty" in r.message for r in caplog.records)


class TestVerifierCLI:
    def test_dry_run_file_human(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "one.pem"
        f.write_bytes(b"CERTDATA")
        result = runner.invoke(
            verifier_main,
            ["--target", str(f), "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Would verify single file" in result.output

    def test_json_file_success(self, tmp_path: Path):
        runner = CliRunner()
        f = tmp_path / "one.pem"
        f.write_bytes(b"CERTDATA")
        result = runner.invoke(
            verifier_main,
            ["--target", str(f), "--json"],
        )
        assert result.exit_code == 0
        # JSON emitted should parse
        data = json.loads(result.output)
        assert data.get("success") is True
        assert data.get("verified_files") == 1
        assert "file_sha256" in data

    def test_directory_dry_run_variants(self, tmp_path: Path):
        runner = CliRunner()
        d = tmp_path / "build"
        d.mkdir()
        # verify-manifest
        r1 = runner.invoke(verifier_main, ["--target", str(d), "--dry-run", "--verify-manifest"])
        assert r1.exit_code == 0
        assert "Would display manifest info" in r1.output
        # verify-all
        r2 = runner.invoke(verifier_main, ["--target", str(d), "--dry-run", "--verify-all"])
        assert r2.exit_code == 0
        assert "Would verify directory" in r2.output

    def test_directory_json_with_errors_and_warnings(self, tmp_path: Path):
        runner = CliRunner()
        d = tmp_path / "build"
        d.mkdir()
        # Prepare files and checksums to induce one warning and one error
        pem = d / "bundle.pem"
        pem.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
        # Missing checksums file triggers error path later
        result = runner.invoke(verifier_main, ["--target", str(d), "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data.get("success") is False
        assert any("Missing checksums" in e for e in data.get("errors", []))

    @patch("bundlecraft.helpers.signing.verify_signature", return_value=(True, "OK"))
    def test_signature_verification_valid(self, _mock_verify, tmp_path: Path, caplog):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        runner = CliRunner()
        d = tmp_path / "dir"
        d.mkdir()
        t = d / "file.pem"
        t.write_bytes(b"abc")
        asc = d / "file.pem.asc"
        asc.write_text("sig")
        # Add checksum for the pem so directory verify runs fully
        write_checksums(d, {t.name: sha256_bytes(t.read_bytes())})
        result = runner.invoke(verifier_main, ["--target", str(d), "--verify-signatures"])
        assert result.exit_code == 0
        assert any(f"{t.name}: OK" in r.message for r in caplog.records)

    @patch("bundlecraft.helpers.signing.verify_signature", return_value=(False, "BAD"))
    def test_signature_verification_invalid_sets_failure(
        self, _mock_verify, tmp_path: Path, caplog
    ):
        caplog.set_level(logging.INFO, logger="bundlecraft.verifier")
        runner = CliRunner()
        d = tmp_path / "dir"
        d.mkdir()
        t = d / "file.pem"
        t.write_bytes(b"abc")
        asc = d / "file.pem.asc"
        asc.write_text("sig")
        write_checksums(d, {t.name: sha256_bytes(t.read_bytes())})
        result = runner.invoke(verifier_main, ["--target", str(d), "--verify-signatures"])
        # main() exits with validation error
        assert result.exit_code != 0
        assert any(f"{t.name}: BAD" in r.message for r in caplog.records)
