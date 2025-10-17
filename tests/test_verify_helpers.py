#!/usr/bin/env python3
"""
test_verify_helpers.py
Unit tests for verify_utils.py helper functions.
"""


from bundlecraft.helpers.verify_utils import (
    _check_output_files,
    _split_pem_blocks,
)


class TestSplitPemBlocks:
    """Test PEM block splitting functionality."""

    def test_split_single_block(self, sample_cert_path):
        """Test splitting a single PEM certificate."""
        text = sample_cert_path.read_text()
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 1
        assert "-----BEGIN CERTIFICATE-----" in blocks[0]
        assert "-----END CERTIFICATE-----" in blocks[0]

    def test_split_multiple_blocks(self, multi_cert_bundle):
        """Test splitting multiple PEM certificates."""
        text = multi_cert_bundle.read_text()
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 2
        for block in blocks:
            assert "-----BEGIN CERTIFICATE-----" in block
            assert "-----END CERTIFICATE-----" in block

    def test_split_empty_string(self):
        """Test splitting an empty string."""
        blocks = _split_pem_blocks("")
        assert len(blocks) == 0

    def test_split_no_certificates(self):
        """Test splitting text with no certificates."""
        text = "This is just random text\nNo certificates here"
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 0

    def test_split_incomplete_block(self):
        """Test splitting incomplete PEM block (no END marker)."""
        text = "-----BEGIN CERTIFICATE-----\nMIIDXTCC\nNo end marker"
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 0

    def test_split_blocks_end_with_newline(self, sample_cert_path):
        """Test that split blocks end with newline."""
        text = sample_cert_path.read_text()
        blocks = _split_pem_blocks(text)
        for block in blocks:
            assert block.endswith("\n")

    def test_split_with_extra_content(self):
        """Test splitting PEM with extra content between certificates."""
        text = """Some header text
-----BEGIN CERTIFICATE-----
MIID
-----END CERTIFICATE-----
Some middle text
-----BEGIN CERTIFICATE-----
ABCD
-----END CERTIFICATE-----
Footer text"""
        blocks = _split_pem_blocks(text)
        assert len(blocks) == 2

    def test_split_multiple_begin_markers(self):
        """Test handling multiple BEGIN markers without END."""
        text = """-----BEGIN CERTIFICATE-----
-----BEGIN CERTIFICATE-----
Data
-----END CERTIFICATE-----"""
        blocks = _split_pem_blocks(text)
        # Should only capture the last valid block
        assert len(blocks) == 1


class TestCheckOutputFiles:
    """Test output file validation."""

    def test_check_valid_p7b_file(self, tmp_path):
        """Test checking a valid P7B file."""
        p7b_file = tmp_path / "test.p7b"
        p7b_file.write_bytes(b"dummy p7b content")

        result = _check_output_files(tmp_path)
        assert result is True

    def test_check_valid_p12_file(self, tmp_path):
        """Test checking a valid P12 file."""
        p12_file = tmp_path / "test.p12"
        p12_file.write_bytes(b"dummy p12 content")

        result = _check_output_files(tmp_path)
        assert result is True

    def test_check_empty_p7b_file(self, tmp_path, capsys):
        """Test checking an empty P7B file."""
        p7b_file = tmp_path / "test.p7b"
        p7b_file.write_bytes(b"")

        result = _check_output_files(tmp_path)
        assert result is False

        captured = capsys.readouterr()
        assert "Empty or missing" in captured.out

    def test_check_empty_p12_file(self, tmp_path, capsys):
        """Test checking an empty P12 file."""
        p12_file = tmp_path / "test.p12"
        p12_file.write_bytes(b"")

        result = _check_output_files(tmp_path)
        assert result is False

        captured = capsys.readouterr()
        assert "Empty or missing" in captured.out

    def test_check_no_output_files(self, tmp_path):
        """Test checking directory with no output files."""
        result = _check_output_files(tmp_path)
        # Should return True when no files to check
        assert result is True

    def test_check_mixed_files(self, tmp_path, capsys):
        """Test checking with valid and invalid files."""
        (tmp_path / "valid.p7b").write_bytes(b"content")
        (tmp_path / "empty.p12").write_bytes(b"")

        result = _check_output_files(tmp_path)
        assert result is False

    def test_check_ignores_other_extensions(self, tmp_path):
        """Test that other file extensions are ignored."""
        (tmp_path / "test.pem").write_bytes(b"")
        (tmp_path / "test.jks").write_bytes(b"")

        result = _check_output_files(tmp_path)
        # Only checks p7b and p12
        assert result is True
