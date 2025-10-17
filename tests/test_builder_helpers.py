#!/usr/bin/env python3
"""
test_builder_helpers.py
Unit tests for builder.py helper functions.
"""

import tarfile

from bundlecraft.builder import (
    build_checksums,
    dedupe_ordered,
    package_tar,
    read_pem_chunks,
    write_canonical_pem,
)


class TestReadPemChunks:
    """Test PEM block reading and parsing."""

    def test_read_single_cert(self, tmp_path, sample_cert_path):
        """Test reading a single certificate."""
        blocks = read_pem_chunks([sample_cert_path])
        assert len(blocks) == 1
        assert "-----BEGIN CERTIFICATE-----" in blocks[0]
        assert "-----END CERTIFICATE-----" in blocks[0]

    def test_read_multiple_certs(self, tmp_path, multi_cert_bundle):
        """Test reading multiple certificates from a bundle."""
        blocks = read_pem_chunks([multi_cert_bundle])
        assert len(blocks) == 2
        for block in blocks:
            assert "-----BEGIN CERTIFICATE-----" in block
            assert "-----END CERTIFICATE-----" in block

    def test_read_from_multiple_files(self, tmp_path, sample_cert_path, intermediate_cert_path):
        """Test reading from multiple PEM files."""
        blocks = read_pem_chunks([sample_cert_path, intermediate_cert_path])
        assert len(blocks) == 2

    def test_read_malformed_pem(self, tmp_path):
        """Test reading a malformed PEM file."""
        malformed = tmp_path / "malformed.pem"
        malformed.write_text("This is not a PEM file\n-----BEGIN CERTIFICATE-----\nIncomplete")
        blocks = read_pem_chunks([malformed])
        # Should not include incomplete blocks
        assert len(blocks) == 0

    def test_read_empty_file(self, tmp_path):
        """Test reading an empty file."""
        empty = tmp_path / "empty.pem"
        empty.write_text("")
        blocks = read_pem_chunks([empty])
        assert len(blocks) == 0

    def test_read_with_extra_whitespace(self, tmp_path):
        """Test reading PEM with extra whitespace."""
        pem_with_spaces = tmp_path / "spaced.pem"
        pem_with_spaces.write_text(
            """

-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL0UG+mRkSvMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMjUwMTE1MTIzNDU2WhcNMjYwMTE1MTIzNDU2WjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEA3I8=
-----END CERTIFICATE-----

        """
        )
        blocks = read_pem_chunks([pem_with_spaces])
        assert len(blocks) == 1


class TestDedupeOrdered:
    """Test PEM block deduplication."""

    def test_dedupe_identical_certs(self, tmp_path, sample_cert_path):
        """Test deduplication of identical certificates."""
        block = sample_cert_path.read_text()
        blocks = [block, block, block]
        deduped = dedupe_ordered(blocks)
        assert len(deduped) == 1

    def test_dedupe_different_certs(self, tmp_path, sample_cert_path, intermediate_cert_path):
        """Test that different certificates are not deduped."""
        block1 = sample_cert_path.read_text()
        block2 = intermediate_cert_path.read_text()
        blocks = [block1, block2]
        deduped = dedupe_ordered(blocks)
        assert len(deduped) == 2

    def test_dedupe_maintains_order(self, tmp_path, sample_cert_path, intermediate_cert_path):
        """Test that deduplication maintains order."""
        block1 = sample_cert_path.read_text()
        block2 = intermediate_cert_path.read_text()
        blocks = [block1, block2, block1]
        deduped = dedupe_ordered(blocks)
        assert len(deduped) == 2
        # First occurrence of block1 should be at index 0
        assert deduped[0] == block1 if block1.endswith("\n") else block1 + "\n"
        assert deduped[1] == block2 if block2.endswith("\n") else block2 + "\n"

    def test_dedupe_adds_newlines(self, tmp_path):
        """Test that dedupe ensures blocks end with newline."""
        block = "-----BEGIN CERTIFICATE-----\nMIIDXTCC\n-----END CERTIFICATE-----"
        blocks = [block]
        deduped = dedupe_ordered(blocks)
        assert deduped[0].endswith("\n")

    def test_dedupe_invalid_pem(self, tmp_path):
        """Test deduplication with invalid PEM blocks."""
        blocks = ["not a pem block"]
        deduped = dedupe_ordered(blocks)
        # Invalid blocks should be skipped (no BEGIN/END markers)
        assert len(deduped) == 0


class TestWriteCanonicalPem:
    """Test canonical PEM writing with subject comments."""

    def test_write_pem_without_comments(self, tmp_path, sample_cert_path):
        """Test writing PEM without subject comments."""
        blocks = read_pem_chunks([sample_cert_path])
        output = tmp_path / "output.pem"
        write_canonical_pem(output, blocks, include_subject_comments=False)

        assert output.exists()
        content = output.read_text()
        assert "# Subject:" not in content
        assert "-----BEGIN CERTIFICATE-----" in content

    def test_write_pem_with_comments(self, tmp_path, sample_cert_path):
        """Test writing PEM with subject comments."""
        blocks = read_pem_chunks([sample_cert_path])
        output = tmp_path / "output.pem"
        write_canonical_pem(output, blocks, include_subject_comments=True)

        assert output.exists()
        content = output.read_text()
        assert "# Subject:" in content
        assert "-----BEGIN CERTIFICATE-----" in content

    def test_write_creates_directory(self, tmp_path):
        """Test that write_canonical_pem creates parent directories."""
        blocks = ["-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"]
        output = tmp_path / "subdir" / "deep" / "output.pem"
        write_canonical_pem(output, blocks, include_subject_comments=False)

        assert output.exists()

    def test_write_multiple_certs_with_comments(self, tmp_path, multi_cert_bundle):
        """Test writing multiple certificates with subject comments."""
        blocks = read_pem_chunks([multi_cert_bundle])
        output = tmp_path / "output.pem"
        write_canonical_pem(output, blocks, include_subject_comments=True)

        content = output.read_text()
        # Should have 2 subject comments for 2 certs
        assert content.count("# Subject:") == 2

    def test_write_unparsable_cert(self, tmp_path):
        """Test writing unparsable certificate with subject comments."""
        blocks = ["-----BEGIN CERTIFICATE-----\ninvalid_data_here\n-----END CERTIFICATE-----"]
        output = tmp_path / "output.pem"
        write_canonical_pem(output, blocks, include_subject_comments=True)

        content = output.read_text()
        assert "# Subject: (unparsable)" in content


class TestBuildChecksums:
    """Test checksum file generation."""

    def test_build_checksums_single_file(self, tmp_path):
        """Test building checksums for a single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        checksum_file = build_checksums(tmp_path)

        assert checksum_file.exists()
        assert checksum_file.name == "checksums.sha256"
        content = checksum_file.read_text()
        assert "test.txt" in content
        assert len(content.split("\n")[0].split()[0]) == 64  # SHA256 length

    def test_build_checksums_multiple_files(self, tmp_path):
        """Test building checksums for multiple files."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "file3.txt").write_text("content3")

        checksum_file = build_checksums(tmp_path)

        content = checksum_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert "file1.txt" in content
        assert "file2.txt" in content
        assert "file3.txt" in content

    def test_build_checksums_sorted_output(self, tmp_path):
        """Test that checksums are sorted alphabetically."""
        (tmp_path / "z_file.txt").write_text("z")
        (tmp_path / "a_file.txt").write_text("a")
        (tmp_path / "m_file.txt").write_text("m")

        checksum_file = build_checksums(tmp_path)

        content = checksum_file.read_text()
        lines = content.strip().split("\n")
        assert "a_file.txt" in lines[0]
        assert "m_file.txt" in lines[1]
        assert "z_file.txt" in lines[2]

    def test_build_checksums_empty_directory(self, tmp_path):
        """Test building checksums for an empty directory."""
        checksum_file = build_checksums(tmp_path)

        content = checksum_file.read_text()
        assert content == ""

    def test_build_checksums_ignores_subdirs(self, tmp_path):
        """Test that subdirectories are ignored."""
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.txt").write_text("nested")

        checksum_file = build_checksums(tmp_path)

        content = checksum_file.read_text()
        assert "file.txt" in content
        assert "nested.txt" not in content


class TestPackageTar:
    """Test tar.gz package creation."""

    def test_package_single_file(self, tmp_path):
        """Test packaging a single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        tar_path = package_tar(tmp_path)

        assert tar_path.exists()
        assert tar_path.name == "package.tar.gz"

        # Verify tar contents
        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getnames()
            assert "test.txt" in members

    def test_package_multiple_files(self, tmp_path):
        """Test packaging multiple files."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        tar_path = package_tar(tmp_path)

        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getnames()
            assert len(members) == 2
            assert "file1.txt" in members
            assert "file2.txt" in members

    def test_package_excludes_itself(self, tmp_path):
        """Test that the tar file doesn't include itself."""
        (tmp_path / "file.txt").write_text("content")

        tar_path = package_tar(tmp_path)

        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getnames()
            assert "package.tar.gz" not in members

    def test_package_sorted_files(self, tmp_path):
        """Test that files are added in sorted order."""
        (tmp_path / "z_file.txt").write_text("z")
        (tmp_path / "a_file.txt").write_text("a")

        tar_path = package_tar(tmp_path)

        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getnames()
            assert members == sorted(members)

    def test_package_empty_directory(self, tmp_path):
        """Test packaging an empty directory."""
        tar_path = package_tar(tmp_path)

        assert tar_path.exists()
        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getnames()
            assert len(members) == 0
