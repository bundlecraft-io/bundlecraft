#!/usr/bin/env python3
"""
test_builder_helpers.py
Unit tests for builder.py helper functions.

NOTE: After the orchestration refactor, many builder functions became private (_prefixed).
This test file tests the core PEM processing functions which are still useful for
validation even though they're now internal implementation details.
"""

from bundlecraft.builder import (
    _dedupe_pem_blocks as dedupe_pem_blocks,
)
from bundlecraft.builder import _read_pem_chunks as read_pem_chunks
from bundlecraft.builder import _write_canonical_pem as write_canonical_pem


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


class TestDedupePemBlocks:
    """Test PEM block deduplication."""

    def test_dedupe_identical_certs(self, tmp_path, sample_cert_path):
        """Test deduplication of identical certificates."""
        block = sample_cert_path.read_text()
        blocks = [block, block, block]
        deduped = dedupe_pem_blocks(blocks)
        assert len(deduped) == 1

    def test_dedupe_different_certs(self, tmp_path, sample_cert_path, intermediate_cert_path):
        """Test that different certificates are not deduped."""
        block1 = sample_cert_path.read_text()
        block2 = intermediate_cert_path.read_text()
        blocks = [block1, block2]
        deduped = dedupe_pem_blocks(blocks)
        assert len(deduped) == 2

    def test_dedupe_maintains_order(self, tmp_path, sample_cert_path, intermediate_cert_path):
        """Test that deduplication maintains order."""
        block1 = sample_cert_path.read_text()
        block2 = intermediate_cert_path.read_text()
        blocks = [block1, block2, block1]
        deduped = dedupe_pem_blocks(blocks)
        assert len(deduped) == 2
        # First occurrence of block1 should be at index 0
        assert deduped[0] == block1 if block1.endswith("\n") else block1 + "\n"
        assert deduped[1] == block2 if block2.endswith("\n") else block2 + "\n"

    def test_dedupe_adds_newlines(self, tmp_path):
        """Test that dedupe ensures blocks end with newline."""
        block = "-----BEGIN CERTIFICATE-----\nMIIDXTCC\n-----END CERTIFICATE-----"
        blocks = [block]
        deduped = dedupe_pem_blocks(blocks)
        assert deduped[0].endswith("\n")

    def test_dedupe_invalid_pem(self, tmp_path):
        """Test deduplication with invalid PEM blocks."""
        blocks = ["not a pem block"]
        deduped = dedupe_pem_blocks(blocks)
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


# NOTE: The following test classes (TestBuildChecksums, TestPackageTar) were removed
# because those functions are no longer part of the refactored builder.
# - build_checksums is now inline in the main() function
# - package_tar was removed entirely (packaging feature removed)
