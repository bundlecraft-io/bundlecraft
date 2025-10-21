#!/usr/bin/env python3
"""
Tests for atomic build context manager.

Verifies that builds are all-or-nothing:
- Successful builds atomically commit temp → final
- Failed builds cleanup temp, preserve final
- Interrupted builds cleanup temp directories
"""

import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from bundlecraft.helpers.atomic_build import AtomicBuildContext, atomic_directory_update


class TestAtomicBuildContext:
    """Test AtomicBuildContext for atomic build operations."""

    def test_successful_build_commits(self, tmp_path):
        """Test that successful build atomically commits temp → final."""
        final_path = tmp_path / "final"
        test_file_content = "build output content"

        with AtomicBuildContext(final_path, verbose=True) as temp_dir:
            # Build to temp directory
            test_file = temp_dir / "output.txt"
            test_file.write_text(test_file_content)
            assert test_file.exists()

        # After success, temp should be moved to final
        assert final_path.exists()
        assert (final_path / "output.txt").read_text() == test_file_content
        # Temp directory should not exist (moved, not copied)
        assert not temp_dir.exists()

    def test_failed_build_preserves_existing(self, tmp_path):
        """Test that failed build preserves existing final output."""
        final_path = tmp_path / "final"
        final_path.mkdir()
        existing_file = final_path / "existing.txt"
        existing_content = "existing output"
        existing_file.write_text(existing_content)

        with pytest.raises(ValueError):
            with AtomicBuildContext(final_path) as temp_dir:
                # Build to temp
                (temp_dir / "new.txt").write_text("new output")
                # Simulate build failure
                raise ValueError("Build failed")

        # Existing final output should be preserved
        assert final_path.exists()
        assert existing_file.exists()
        assert existing_file.read_text() == existing_content
        # New file should not be in final
        assert not (final_path / "new.txt").exists()

    def test_failed_build_cleans_temp(self, tmp_path):
        """Test that failed build cleans up temp directory."""
        final_path = tmp_path / "final"
        temp_dirs_before = set(Path(tempfile.gettempdir()).glob("bundlecraft-build-*"))

        try:
            with AtomicBuildContext(final_path) as temp_dir:
                temp_path = temp_dir  # Capture for verification
                (temp_dir / "output.txt").write_text("content")
                raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass

        # Temp directory should be cleaned up
        assert not temp_path.exists()
        # No new temp directories left behind
        temp_dirs_after = set(Path(tempfile.gettempdir()).glob("bundlecraft-build-*"))
        assert temp_dirs_after == temp_dirs_before

    def test_keep_temp_preserves_on_failure(self, tmp_path):
        """Test that keep_temp=True preserves temp on failure."""
        final_path = tmp_path / "final"

        try:
            with AtomicBuildContext(final_path, keep_temp=True) as temp_dir:
                temp_path = temp_dir
                (temp_dir / "debug.txt").write_text("debug info")
                raise RuntimeError("Debug this")
        except RuntimeError:
            pass

        # Temp should be preserved for debugging
        assert temp_path.exists()
        assert (temp_path / "debug.txt").exists()

        # Cleanup for test hygiene
        import shutil

        shutil.rmtree(temp_path)

    def test_dry_run_mode(self, tmp_path):
        """Test that dry_run mode doesn't move files."""
        final_path = tmp_path / "final"

        with AtomicBuildContext(final_path, dry_run=True, verbose=True) as temp_dir:
            (temp_dir / "output.txt").write_text("dry run content")
            assert temp_dir.exists()

        # In dry-run, final should not exist
        assert not final_path.exists()
        # Temp should still exist (not moved in dry-run)
        assert temp_dir.exists()

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    def test_replaces_existing_final(self, tmp_path):
        """Test that successful build replaces existing final output."""
        final_path = tmp_path / "final"
        final_path.mkdir()
        old_file = final_path / "old.txt"
        old_file.write_text("old content")

        with AtomicBuildContext(final_path) as temp_dir:
            (temp_dir / "new.txt").write_text("new content")

        # Old file should be gone, new file should exist
        assert not (final_path / "old.txt").exists()
        assert (final_path / "new.txt").exists()
        assert (final_path / "new.txt").read_text() == "new content"

    def test_multiple_files_atomic(self, tmp_path):
        """Test that all files are committed atomically."""
        final_path = tmp_path / "final"

        with AtomicBuildContext(final_path) as temp_dir:
            for i in range(5):
                (temp_dir / f"file{i}.txt").write_text(f"content {i}")

        # All files should be in final
        assert final_path.exists()
        for i in range(5):
            assert (final_path / f"file{i}.txt").read_text() == f"content {i}"

    def test_nested_directories(self, tmp_path):
        """Test atomic commit with nested directory structure."""
        final_path = tmp_path / "final"

        with AtomicBuildContext(final_path) as temp_dir:
            subdir = temp_dir / "sub" / "nested"
            subdir.mkdir(parents=True)
            (subdir / "deep.txt").write_text("deep content")

        # Nested structure should be preserved in final
        assert (final_path / "sub" / "nested" / "deep.txt").exists()
        assert (final_path / "sub" / "nested" / "deep.txt").read_text() == "deep content"


class TestAtomicDirectoryUpdate:
    """Test atomic_directory_update utility function."""

    def test_atomic_directory_update_success(self, tmp_path):
        """Test atomic directory update replaces destination."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"

        # Setup source
        source.mkdir()
        (source / "new.txt").write_text("new content")

        # Setup existing dest
        dest.mkdir()
        (dest / "old.txt").write_text("old content")

        # Atomic update
        atomic_directory_update(source, dest, verbose=True)

        # Dest should have new content
        assert (dest / "new.txt").exists()
        assert not (dest / "old.txt").exists()
        # Source should be moved (not exist anymore)
        assert not source.exists()

    def test_atomic_directory_update_no_existing(self, tmp_path):
        """Test atomic directory update when dest doesn't exist."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"

        source.mkdir()
        (source / "file.txt").write_text("content")

        atomic_directory_update(source, dest)

        assert dest.exists()
        assert (dest / "file.txt").read_text() == "content"
        assert not source.exists()

    def test_atomic_directory_update_error_rollback(self, tmp_path):
        """Test atomic directory update rolls back on error."""
        source = tmp_path / "nonexistent"
        dest = tmp_path / "dest"

        dest.mkdir()
        (dest / "preserve.txt").write_text("preserve this")

        with pytest.raises(ValueError):
            atomic_directory_update(source, dest)

        # Dest should be preserved
        assert dest.exists()
        assert (dest / "preserve.txt").read_text() == "preserve this"


class TestSignalHandling:
    """Test signal handling for graceful cleanup."""

    def test_sigint_cleanup(self, tmp_path):
        """Test that SIGINT cleans up temp directories."""
        # Create a subprocess that will be interrupted
        test_script = tmp_path / "test_interrupt.py"
        test_script.write_text(
            f"""
import sys
import time
from pathlib import Path
sys.path.insert(0, {str(Path(__file__).parent.parent)!r})

from bundlecraft.helpers.atomic_build import AtomicBuildContext

final_path = Path({str(tmp_path / "final")!r})
with AtomicBuildContext(final_path) as temp_dir:
    marker = temp_dir / "marker.txt"
    marker.write_text("temp")
    print(f"TEMP_DIR:{{temp_dir}}")
    sys.stdout.flush()
    time.sleep(10)  # Wait for interrupt
"""
        )

        # Run subprocess and interrupt it
        proc = subprocess.Popen(
            [sys.executable, str(test_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for temp dir to be created
        temp_dir = None
        try:
            for line in proc.stdout:
                if line.startswith("TEMP_DIR:"):
                    temp_dir = Path(line.strip().split(":", 1)[1])
                    break

            if temp_dir:
                # Verify temp exists
                time.sleep(0.5)
                assert temp_dir.exists()

                # Send SIGINT
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=5)

                # Temp should be cleaned up
                time.sleep(0.5)
                assert not temp_dir.exists(), "Temp directory was not cleaned up after SIGINT"
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


def test_concurrent_builds_different_targets(tmp_path):
    """Test that concurrent builds to different targets don't interfere."""
    target1 = tmp_path / "target1"
    target2 = tmp_path / "target2"

    # Simulate concurrent builds
    with AtomicBuildContext(target1) as temp1:
        (temp1 / "file1.txt").write_text("content1")
        with AtomicBuildContext(target2) as temp2:
            (temp2 / "file2.txt").write_text("content2")

    # Both targets should have their files
    assert (target1 / "file1.txt").read_text() == "content1"
    assert (target2 / "file2.txt").read_text() == "content2"
