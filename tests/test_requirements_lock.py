"""Tests for requirements lock file validation."""

import re
from pathlib import Path


def test_requirements_lock_file_exists():
    """Test that the requirements lock file exists."""
    repo_root = Path(__file__).parent.parent
    lock_file = repo_root / "requirements-lock.txt"
    assert lock_file.exists(), "requirements-lock.txt file should exist"


def test_requirements_lock_file_format():
    """Test that the requirements lock file has the correct format."""
    repo_root = Path(__file__).parent.parent
    lock_file = repo_root / "requirements-lock.txt"
    
    with open(lock_file, "r") as f:
        content = f.read()
    
    # Should have header comments
    assert "# This file is auto-generated" in content, "Lock file should have header"
    assert "# Purpose:" in content, "Lock file should explain its purpose"
    assert "# Update Instructions:" in content, "Lock file should have update instructions"
    
    # Should reference CONTRIBUTING.md
    assert "CONTRIBUTING.md" in content, "Lock file should reference CONTRIBUTING.md"


def test_requirements_lock_file_has_core_dependencies():
    """Test that the lock file includes all core dependencies from pyproject.toml."""
    repo_root = Path(__file__).parent.parent
    lock_file = repo_root / "requirements-lock.txt"
    
    # Core dependencies that should be in the lock file
    core_dependencies = [
        "click",
        "cryptography",
        "pyOpenSSL",
        "PyYAML",
        "pydantic",
        "python-gnupg",
        "cyclonedx-bom",
        "pyjks",
    ]
    
    with open(lock_file, "r") as f:
        content = f.read()
    
    for dep in core_dependencies:
        # Check for package name with version pinning (e.g., "click==8.1.7")
        pattern = rf"{dep}=="
        assert re.search(pattern, content, re.IGNORECASE), (
            f"Lock file should include {dep} with exact version"
        )


def test_requirements_lock_file_has_exact_versions():
    """Test that all dependencies in lock file use exact version pinning."""
    repo_root = Path(__file__).parent.parent
    lock_file = repo_root / "requirements-lock.txt"
    
    with open(lock_file, "r") as f:
        lines = f.readlines()
    
    # Pattern for exact version pinning (package==version)
    # Handles package names with hyphens, underscores, dots, and multiple version segments
    # Version can be single segment (e.g., "1") or multiple segments (e.g., "1.2.3")
    # Hyphen at the end to avoid being interpreted as a range
    exact_version_pattern = re.compile(r"^[a-zA-Z0-9_.-]+==\d+(\.\d+)*")
    
    dependency_found = False
    for line in lines:
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        
        dependency_found = True
        
        # Check that line uses exact version pinning
        assert exact_version_pattern.match(line), (
            f"Line '{line}' should use exact version pinning (==)"
        )
        
        # Should not use range operators
        assert ">=" not in line, f"Line '{line}' should not use >= operator"
        assert "<=" not in line, f"Line '{line}' should not use <= operator"
        assert "~=" not in line, f"Line '{line}' should not use ~= operator"
        assert "!=" not in line, f"Line '{line}' should not use != operator"
    
    assert dependency_found, "Lock file should contain at least one dependency"


def test_requirements_lock_file_no_editable_installs():
    """Test that lock file doesn't contain editable installs."""
    repo_root = Path(__file__).parent.parent
    lock_file = repo_root / "requirements-lock.txt"
    
    with open(lock_file, "r") as f:
        content = f.read()
    
    # Should not have -e flag (editable installs)
    assert "-e " not in content, "Lock file should not contain editable installs"
    assert "file://" not in content, "Lock file should not contain file:// URLs"
