#!/usr/bin/env python3
"""
Atomic build context manager for reliable, all-or-nothing builds.

Provides atomicity guarantees:
- Build to temporary directory
- Atomic move/rename on success
- Automatic cleanup on failure
- Signal handling for graceful interruption cleanup
"""

from __future__ import annotations

import atexit
import signal
import sys
import tempfile
import uuid
from pathlib import Path

import click


class AtomicBuildContext:
    """Context manager for atomic build operations.

    Ensures builds are all-or-nothing:
    - Creates temporary build directory
    - On success: atomically moves temp → final location
    - On failure: cleans up temp, preserves existing final location
    - On interrupt: cleans up temp, exits gracefully

    Usage:
        with AtomicBuildContext(final_path, keep_temp=False) as temp_dir:
            # Build to temp_dir
            build_artifacts(temp_dir)
            # On exit: temp_dir atomically moved to final_path
    """

    _active_contexts: list[AtomicBuildContext] = []
    _signal_handlers_installed = False

    def __init__(
        self,
        final_path: Path,
        keep_temp: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize atomic build context.

        Args:
            final_path: Final destination for build output
            keep_temp: If True, preserve temp directory on failure (for debugging)
            verbose: Enable verbose logging
            dry_run: If True, don't actually move files (simulation mode)
        """
        self.final_path = final_path.resolve()
        self.keep_temp = keep_temp
        self.verbose = verbose
        self.dry_run = dry_run
        self.temp_dir: Path | None = None
        self.success = False
        self._backup_path: Path | None = None

    def __enter__(self) -> Path:
        """Enter context: create temp directory and register signal handlers."""
        # Create unique temporary directory
        temp_prefix = f"bundlecraft-build-{uuid.uuid4().hex[:8]}-"
        self.temp_dir = Path(tempfile.mkdtemp(prefix=temp_prefix))

        if self.verbose:
            click.echo(f"[atomic] Created temp build directory: {self.temp_dir}", err=True)

        # Register this context for signal handling
        AtomicBuildContext._active_contexts.append(self)

        # Install signal handlers (once)
        if not AtomicBuildContext._signal_handlers_installed:
            self._install_signal_handlers()
            AtomicBuildContext._signal_handlers_installed = True

        return self.temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context: commit on success, cleanup on failure."""
        try:
            if exc_type is None:
                # Success: atomic commit
                if self.dry_run:
                    if self.verbose:
                        click.echo(
                            f"[atomic] [dry-run] Would move {self.temp_dir} → {self.final_path}",
                            err=True,
                        )
                    self.success = True
                else:
                    self._atomic_commit()
                    self.success = True
            else:
                # Failure: cleanup temp, preserve final
                if self.verbose:
                    click.echo(
                        f"[atomic] Build failed, cleaning up temp directory: {self.temp_dir}",
                        err=True,
                    )
                if not self.keep_temp and not self.dry_run:
                    self._cleanup_temp()
                elif self.keep_temp:
                    click.secho(
                        f"[atomic] Preserved temp directory for debugging: {self.temp_dir}",
                        fg="yellow",
                        err=True,
                    )
        finally:
            # Remove from active contexts
            if self in AtomicBuildContext._active_contexts:
                AtomicBuildContext._active_contexts.remove(self)

        # Don't suppress exceptions
        return False

    def _atomic_commit(self) -> None:
        """Atomically move temp directory to final location.

        Strategy:
        1. If final_path exists, move it to backup location
        2. Atomically rename temp → final (os.replace is atomic on POSIX)
        3. Remove backup on success
        4. On error, restore from backup
        """
        import shutil

        if self.verbose:
            click.echo(f"[atomic] Committing build: {self.temp_dir} → {self.final_path}", err=True)

        # Ensure parent directory exists
        self.final_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Backup existing final_path if it exists
            if self.final_path.exists():
                backup_suffix = f".backup-{uuid.uuid4().hex[:8]}"
                self._backup_path = self.final_path.with_name(self.final_path.name + backup_suffix)
                if self.verbose:
                    click.echo(
                        f"[atomic] Backing up existing: {self.final_path} → {self._backup_path}",
                        err=True,
                    )
                # Use shutil.move for cross-filesystem support
                shutil.move(str(self.final_path), str(self._backup_path))

            # Step 2: Atomic move temp → final
            # os.replace is atomic on POSIX (same filesystem)
            # For cross-filesystem, this falls back to copy+delete
            import os

            try:
                os.replace(str(self.temp_dir), str(self.final_path))
                if self.verbose:
                    click.echo(
                        f"[atomic] ✓ Atomically moved temp → final: {self.final_path}",
                        err=True,
                    )
            except OSError:
                # Fallback for cross-filesystem moves
                if self.verbose:
                    click.echo(
                        "[atomic] Cross-filesystem detected, using copy+verify fallback",
                        err=True,
                    )
                shutil.copytree(str(self.temp_dir), str(self.final_path), dirs_exist_ok=True)
                self._cleanup_temp()

            # Step 3: Remove backup on success
            if self._backup_path and self._backup_path.exists():
                if self.verbose:
                    click.echo(f"[atomic] Removing backup: {self._backup_path}", err=True)
                shutil.rmtree(self._backup_path)
                self._backup_path = None

        except Exception as e:
            # Rollback: restore from backup if available
            if self._backup_path and self._backup_path.exists():
                click.secho(
                    f"[atomic] ERROR during commit, restoring from backup: {e}",
                    fg="red",
                    err=True,
                )
                if self.final_path.exists():
                    shutil.rmtree(self.final_path)
                shutil.move(str(self._backup_path), str(self.final_path))
                self._backup_path = None
            raise

    def _cleanup_temp(self) -> None:
        """Remove temporary build directory."""
        import shutil

        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                if self.verbose:
                    click.echo(f"[atomic] Cleaned up temp directory: {self.temp_dir}", err=True)
            except Exception as e:
                click.secho(
                    f"[atomic] Warning: Failed to cleanup temp directory {self.temp_dir}: {e}",
                    fg="yellow",
                    err=True,
                )

    @classmethod
    def _install_signal_handlers(cls) -> None:
        """Install signal handlers for graceful cleanup on interruption."""

        def signal_handler(signum, frame):
            signame = signal.Signals(signum).name
            click.secho(
                f"\n[atomic] Received {signame}, cleaning up...",
                fg="yellow",
                err=True,
            )

            # Cleanup all active contexts
            for ctx in list(cls._active_contexts):
                if not ctx.keep_temp:
                    ctx._cleanup_temp()

            # Exit with standard interrupted exit code
            sys.exit(128 + signum)

        # Register handlers for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Register atexit handler for emergency cleanup
        atexit.register(cls._emergency_cleanup)

    @classmethod
    def _emergency_cleanup(cls) -> None:
        """Emergency cleanup of all active contexts on abnormal exit."""
        if cls._active_contexts:
            for ctx in list(cls._active_contexts):
                if not ctx.keep_temp:
                    ctx._cleanup_temp()


def atomic_directory_update(source: Path, dest: Path, verbose: bool = False) -> None:
    """Atomically update a directory by replacing it with new content.

    This is a utility function for atomic updates outside of full build context.
    Useful for updating cache directories atomically.

    Args:
        source: Source directory with new content
        dest: Destination directory to update
        verbose: Enable verbose logging
    """
    import os
    import shutil

    if not source.exists():
        raise ValueError(f"Source directory does not exist: {source}")

    # Create temp location for atomic swap
    temp_suffix = f".tmp-{uuid.uuid4().hex[:8]}"
    temp_dest = dest.with_name(dest.name + temp_suffix)

    try:
        # Move existing dest to temp (if exists)
        if dest.exists():
            os.replace(str(dest), str(temp_dest))

        # Move source to dest (atomic on POSIX)
        os.replace(str(source), str(dest))

        # Remove old version
        if temp_dest.exists():
            shutil.rmtree(temp_dest)

        if verbose:
            click.echo(f"[atomic] ✓ Atomically updated: {dest}", err=True)

    except Exception:
        # Rollback on error
        if temp_dest.exists() and not dest.exists():
            os.replace(str(temp_dest), str(dest))
        raise
