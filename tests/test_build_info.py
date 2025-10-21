"""Tests for build_info module."""

import json
import subprocess

from bundlecraft import __version__
from bundlecraft.helpers.build_info import (
    generate_build_info,
    get_bundlecraft_version,
    get_git_info,
    get_source_versions,
)


class TestGetBundlecraftVersion:
    """Tests for get_bundlecraft_version function."""

    def test_returns_version_string(self):
        """Verify that get_bundlecraft_version returns the package version."""
        version = get_bundlecraft_version()
        assert version == __version__
        assert isinstance(version, str)
        assert len(version) > 0


class TestGetGitInfo:
    """Tests for get_git_info function."""

    def test_returns_none_for_non_git_directory(self, tmp_path):
        """Verify that get_git_info returns None for non-git directories."""
        result = get_git_info(tmp_path)
        assert result is None

    def test_returns_git_info_for_git_repository(self, tmp_path):
        """Verify that get_git_info returns correct info for git repositories."""
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create a file and commit
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        result = get_git_info(tmp_path)
        assert result is not None
        assert "commit" in result
        assert "branch" in result
        assert "dirty" in result
        assert isinstance(result["commit"], str)
        assert len(result["commit"]) == 40  # SHA-1 hash
        assert result["branch"] in ["main", "master"]  # depends on git config
        assert result["dirty"] is False

    def test_detects_dirty_state(self, tmp_path):
        """Verify that get_git_info detects uncommitted changes."""
        # Initialize a git repo and make a commit
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Add uncommitted changes
        (tmp_path / "dirty.txt").write_text("uncommitted")

        result = get_git_info(tmp_path)
        assert result is not None
        assert result["dirty"] is True


class TestGetSourceVersions:
    """Tests for get_source_versions function."""

    def test_returns_empty_dict_for_no_staging_dirs(self):
        """Verify that get_source_versions returns empty dict when no staging dirs exist."""
        result = get_source_versions([])
        assert result == {}

    def test_returns_empty_dict_for_nonexistent_dirs(self, tmp_path):
        """Verify that get_source_versions returns empty dict for nonexistent directories."""
        nonexistent = tmp_path / "nonexistent"
        result = get_source_versions([nonexistent])
        assert result == {}

    def test_extracts_version_from_provenance(self, tmp_path):
        """Verify that get_source_versions extracts version from provenance.fetch.json."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()

        provenance = {
            "generated_at": "2025-10-21T05:00:00Z",
            "items": [
                {
                    "name": "mozilla_roots",
                    "origin": {"type": "url", "url": "https://example.com/2025-10-01/bundle.pem"},
                    "staged_path": "staging/mozilla_roots.pem",
                    "sha256": "abc123",
                }
            ],
        }
        (staging_dir / "provenance.fetch.json").write_text(json.dumps(provenance))

        result = get_source_versions([staging_dir])
        assert "mozilla_roots" in result
        assert result["mozilla_roots"] == "2025-10-01"

    def test_extracts_explicit_version_from_origin(self, tmp_path):
        """Verify that explicit version in origin is used."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()

        provenance = {
            "generated_at": "2025-10-21T05:00:00Z",
            "items": [
                {
                    "name": "internal",
                    "origin": {"type": "vault", "version": "v2.3.0"},
                    "staged_path": "staging/internal.pem",
                    "sha256": "def456",
                }
            ],
        }
        (staging_dir / "provenance.fetch.json").write_text(json.dumps(provenance))

        result = get_source_versions([staging_dir])
        assert "internal" in result
        assert result["internal"] == "v2.3.0"

    def test_extracts_version_from_metadata(self, tmp_path):
        """Verify that version from metadata is extracted."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()

        provenance = {
            "generated_at": "2025-10-21T05:00:00Z",
            "items": [
                {
                    "name": "custom",
                    "origin": {"type": "api", "metadata": {"version": "1.2.3"}},
                    "staged_path": "staging/custom.pem",
                    "sha256": "ghi789",
                }
            ],
        }
        (staging_dir / "provenance.fetch.json").write_text(json.dumps(provenance))

        result = get_source_versions([staging_dir])
        assert "custom" in result
        assert result["custom"] == "1.2.3"

    def test_handles_malformed_provenance_gracefully(self, tmp_path):
        """Verify that malformed provenance.fetch.json is handled gracefully."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()

        # Write invalid JSON
        (staging_dir / "provenance.fetch.json").write_text("invalid json {")

        result = get_source_versions([staging_dir])
        assert result == {}


class TestGenerateBuildInfo:
    """Tests for generate_build_info function."""

    def test_includes_bundlecraft_version(self):
        """Verify that generate_build_info includes bundlecraft version."""
        result = generate_build_info()
        assert "bundlecraft_version" in result
        assert result["bundlecraft_version"] == __version__

    def test_includes_git_info_when_available(self, tmp_path):
        """Verify that generate_build_info includes git info when in a git repo."""
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        result = generate_build_info(repo_root=tmp_path)
        assert "git_commit" in result
        assert "git_branch" in result
        assert "git_dirty" in result
        assert isinstance(result["git_commit"], str)
        assert len(result["git_commit"]) == 40

    def test_omits_git_info_when_not_available(self, tmp_path):
        """Verify that generate_build_info omits git info when not in a git repo."""
        result = generate_build_info(repo_root=tmp_path)
        assert "bundlecraft_version" in result
        assert "git_commit" not in result
        assert "git_branch" not in result
        assert "git_dirty" not in result

    def test_includes_source_versions_when_available(self, tmp_path):
        """Verify that generate_build_info includes source versions when staging dirs provided."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()

        provenance = {
            "generated_at": "2025-10-21T05:00:00Z",
            "items": [
                {
                    "name": "mozilla",
                    "origin": {"version": "2025-10-01"},
                    "staged_path": "staging/mozilla.pem",
                    "sha256": "abc123",
                }
            ],
        }
        (staging_dir / "provenance.fetch.json").write_text(json.dumps(provenance))

        result = generate_build_info(staging_dirs=[staging_dir])
        assert "source_versions" in result
        assert "mozilla" in result["source_versions"]
        assert result["source_versions"]["mozilla"] == "2025-10-01"

    def test_omits_source_versions_when_empty(self, tmp_path):
        """Verify that generate_build_info omits source_versions when empty."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()

        result = generate_build_info(staging_dirs=[staging_dir])
        assert "bundlecraft_version" in result
        assert "source_versions" not in result
