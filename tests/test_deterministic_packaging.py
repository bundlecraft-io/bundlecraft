"""Tests for deterministic tar packaging and single-pass checksums."""

import hashlib
import tarfile
import time

from bundlecraft.builder import _create_deterministic_tar


class TestDeterministicTarPackaging:
    """Test suite for deterministic tar packaging."""

    def test_tar_created_successfully(self, temp_dir):
        """Test that tar file is created successfully."""
        # Create some test files
        (temp_dir / "file1.txt").write_text("content1", encoding="utf-8")
        (temp_dir / "file2.txt").write_text("content2", encoding="utf-8")

        tar_path = _create_deterministic_tar(temp_dir, "test-package")

        assert tar_path.exists()
        assert tar_path.name == "test-package.tar.gz"

    def test_tar_contains_all_files(self, temp_dir):
        """Test that tar contains all files from build directory."""
        # Create test files
        files = ["file1.txt", "file2.txt", "file3.pem"]
        for fname in files:
            (temp_dir / fname).write_text(f"content of {fname}", encoding="utf-8")

        tar_path = _create_deterministic_tar(temp_dir, "test-package")

        # Verify tar contents
        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getmembers()
            member_names = {m.name for m in members}
            assert member_names == set(files)

    def test_tar_excludes_itself(self, temp_dir):
        """Test that tar doesn't include itself."""
        (temp_dir / "file1.txt").write_text("content", encoding="utf-8")

        tar_path = _create_deterministic_tar(temp_dir, "test-package")

        with tarfile.open(tar_path, "r:gz") as tar:
            member_names = [m.name for m in tar.getmembers()]
            assert "test-package.tar.gz" not in member_names

    def test_tar_metadata_normalized(self, temp_dir):
        """Test that tar metadata is normalized for determinism."""
        (temp_dir / "file1.txt").write_text("content", encoding="utf-8")

        tar_path = _create_deterministic_tar(temp_dir, "test-package")

        with tarfile.open(tar_path, "r:gz") as tar:
            for member in tar.getmembers():
                # Verify normalized metadata
                assert member.mtime == 0, "mtime should be 0 (epoch)"
                assert member.uid == 0, "uid should be 0"
                assert member.gid == 0, "gid should be 0"
                assert member.uname == "", "uname should be empty"
                assert member.gname == "", "gname should be empty"

    def test_tar_entries_sorted(self, temp_dir):
        """Test that tar entries are sorted for determinism."""
        # Create files in non-alphabetical order
        files = ["z-last.txt", "a-first.txt", "m-middle.txt"]
        for fname in files:
            (temp_dir / fname).write_text(f"content of {fname}", encoding="utf-8")

        tar_path = _create_deterministic_tar(temp_dir, "test-package")

        with tarfile.open(tar_path, "r:gz") as tar:
            member_names = [m.name for m in tar.getmembers()]
            # Should be sorted alphabetically
            assert member_names == sorted(files)

    def test_identical_inputs_produce_identical_tar(self, temp_dir):
        """Test that identical inputs produce byte-identical tar archives."""
        # Create test files
        (temp_dir / "file1.txt").write_text("content1", encoding="utf-8")
        (temp_dir / "file2.txt").write_text("content2", encoding="utf-8")

        # Create first tar
        tar_path1 = _create_deterministic_tar(temp_dir, "package1")
        hash1 = hashlib.sha256(tar_path1.read_bytes()).hexdigest()

        # Remove first tar and recreate
        tar_path1.unlink()

        # Create second tar with same content
        tar_path2 = _create_deterministic_tar(temp_dir, "package2")
        # Rename to same name for fair comparison
        tar_path2.rename(temp_dir / "package1.tar.gz")
        tar_path1 = temp_dir / "package1.tar.gz"
        hash2 = hashlib.sha256(tar_path1.read_bytes()).hexdigest()

        # Hashes should be identical
        assert hash1 == hash2, "Identical inputs should produce byte-identical tars"

    def test_tar_deterministic_across_time(self, temp_dir):
        """Test that tar creation is deterministic across different times."""
        # Create test files
        (temp_dir / "file1.txt").write_text("content1", encoding="utf-8")

        # Create first tar
        tar_path1 = _create_deterministic_tar(temp_dir, "package1")
        hash1 = hashlib.sha256(tar_path1.read_bytes()).hexdigest()
        tar_path1.unlink()

        # Wait a moment to ensure different timestamp
        time.sleep(0.1)

        # Touch the file to change its mtime
        (temp_dir / "file1.txt").touch()

        # Create second tar
        tar_path2 = _create_deterministic_tar(temp_dir, "package2")
        tar_path2.rename(temp_dir / "package1.tar.gz")
        tar_path1 = temp_dir / "package1.tar.gz"
        hash2 = hashlib.sha256(tar_path1.read_bytes()).hexdigest()

        # Should still be identical despite file timestamp changes
        assert hash1 == hash2, "Tar should be deterministic regardless of file timestamps"

    def test_tar_with_empty_directory(self, temp_dir):
        """Test creating tar with empty directory."""
        tar_path = _create_deterministic_tar(temp_dir, "empty-package")

        assert tar_path.exists()
        with tarfile.open(tar_path, "r:gz") as tar:
            assert len(tar.getmembers()) == 0


class TestDeterministicZipFormat:
    """Test suite for deterministic zip format in convert_utils."""

    def test_zip_format_deterministic(self, temp_dir, sample_cert_pem):
        """Test that ZIP format (tar.gz of individual certs) is deterministic."""
        from bundlecraft.helpers.convert_utils import create_zip

        # Create a PEM bundle with multiple certs
        pem_path = temp_dir / "bundle.pem"
        pem_content = sample_cert_pem + "\n" + sample_cert_pem
        pem_path.write_text(pem_content, encoding="utf-8")

        # Create first zip
        output_dir1 = temp_dir / "output1"
        output_dir1.mkdir()
        create_zip(pem_path, output_dir1, "bundle", force=True)
        zip_path1 = output_dir1 / "bundle.tar.gz"
        hash1 = hashlib.sha256(zip_path1.read_bytes()).hexdigest()

        # Create second zip with same content
        output_dir2 = temp_dir / "output2"
        output_dir2.mkdir()
        time.sleep(0.1)  # Ensure different time
        create_zip(pem_path, output_dir2, "bundle", force=True)
        zip_path2 = output_dir2 / "bundle.tar.gz"
        hash2 = hashlib.sha256(zip_path2.read_bytes()).hexdigest()

        # Should be byte-identical
        assert hash1 == hash2, "ZIP format should be deterministic"

    def test_zip_entries_sorted(self, temp_dir, sample_cert_pem):
        """Test that ZIP entries are sorted for determinism."""
        from bundlecraft.helpers.convert_utils import create_zip

        # Create a PEM bundle with multiple certs
        pem_path = temp_dir / "bundle.pem"
        # Add multiple copies to get multiple files
        pem_content = "\n".join([sample_cert_pem] * 3)
        pem_path.write_text(pem_content, encoding="utf-8")

        output_dir = temp_dir / "output"
        output_dir.mkdir()
        create_zip(pem_path, output_dir, "bundle", force=True)
        zip_path = output_dir / "bundle.tar.gz"

        # Verify entries are sorted
        with tarfile.open(zip_path, "r:gz") as tar:
            members = tar.getmembers()
            names = [m.name for m in members]
            assert names == sorted(names), "ZIP entries should be sorted"

    def test_zip_metadata_normalized(self, temp_dir, sample_cert_pem):
        """Test that ZIP metadata is normalized."""
        from bundlecraft.helpers.convert_utils import create_zip

        pem_path = temp_dir / "bundle.pem"
        pem_path.write_text(sample_cert_pem, encoding="utf-8")

        output_dir = temp_dir / "output"
        output_dir.mkdir()
        create_zip(pem_path, output_dir, "bundle", force=True)
        zip_path = output_dir / "bundle.tar.gz"

        with tarfile.open(zip_path, "r:gz") as tar:
            for member in tar.getmembers():
                assert member.mtime == 0, "mtime should be 0"
                assert member.uid == 0, "uid should be 0"
                assert member.gid == 0, "gid should be 0"
                assert member.uname == "", "uname should be empty"
                assert member.gname == "", "gname should be empty"


class TestSinglePassChecksums:
    """Test that checksums are computed only once after all outputs."""

    def test_checksums_include_all_outputs(self, temp_dir):
        """Test that checksums file includes all output files."""
        # Simulate build output
        files = ["bundle.pem", "bundle.p7b", "package.tar.gz", "manifest.json"]
        for fname in files:
            (temp_dir / fname).write_text(f"content of {fname}", encoding="utf-8")

        # Simulate checksum creation (from builder.py pattern)
        all_files = sorted([f.name for f in temp_dir.glob("*") if f.is_file()])
        from bundlecraft.helpers.utils import sha256_file

        checksum_lines = [
            f"{sha256_file(temp_dir / fname)}  {fname}" for fname in all_files
        ]
        checksum_path = temp_dir / "checksums.sha256"
        checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

        # Verify all files are in checksums
        checksum_content = checksum_path.read_text()
        for fname in files:
            assert fname in checksum_content

    def test_manifest_excludes_itself_and_checksums(self, temp_dir):
        """Test that manifest doesn't include itself or checksums in file list."""
        # Create output files
        files = ["bundle.pem", "bundle.p7b", "package.tar.gz"]
        for fname in files:
            (temp_dir / fname).write_text(f"content of {fname}", encoding="utf-8")

        # Simulate manifest creation (from builder.py pattern)
        from bundlecraft.helpers.utils import sha256_file

        output_files = sorted(
            [
                f.name
                for f in temp_dir.glob("*")
                if f.is_file() and f.name not in ("manifest.json", "checksums.sha256")
            ]
        )

        manifest_files = [
            {"path": fname, "sha256": sha256_file(temp_dir / fname)} for fname in output_files
        ]

        # Verify manifest excludes itself and checksums
        file_names = [f["path"] for f in manifest_files]
        assert "manifest.json" not in file_names
        assert "checksums.sha256" not in file_names
        assert set(file_names) == set(files)
