"""
Common test fixtures and configuration for BundleCraft tests.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory containing sample certificates and configs."""
    return Path(__file__).parent / "data"


# Ensure the repository root is importable for 'bundlecraft' without requiring installation
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test files that is cleaned up after each test."""
    with tempfile.TemporaryDirectory() as td:
        temp_path = Path(td)
        yield temp_path


@pytest.fixture(scope="function")
def temp_workspace(temp_dir, test_data_dir):
    """
    Create a temporary workspace with sample certificates and configs.
    This provides an isolated environment for each test.
    """
    # Create standard directory structure
    dirs = ["sources/internal", "config/bundles", "config/envs", "build"]
    for d in dirs:
        (temp_dir / d).mkdir(parents=True)

    # Copy sample test data if it exists
    if test_data_dir.exists():
        if (test_data_dir / "certs").exists():
            shutil.copytree(test_data_dir / "certs", temp_dir / "sources", dirs_exist_ok=True)
        if (test_data_dir / "configs").exists():
            shutil.copytree(test_data_dir / "configs", temp_dir / "config", dirs_exist_ok=True)

    yield temp_dir


@pytest.fixture(scope="function")
def sample_cert_path(test_data_dir) -> Path:
    """Return path to a sample test certificate."""
    return test_data_dir / "certs" / "sample.pem"


@pytest.fixture(scope="function")
def intermediate_cert_path(test_data_dir) -> Path:
    """Return path to an intermediate test certificate."""
    return test_data_dir / "certs" / "intermediate.pem"


@pytest.fixture(scope="function")
def multi_cert_bundle(tmp_path, sample_cert_path, intermediate_cert_path) -> Path:
    """Create a bundle with multiple certificates for testing."""
    bundle_path = tmp_path / "multi-cert-bundle.pem"
    with open(bundle_path, "w") as out:
        with open(sample_cert_path) as f1:
            out.write(f1.read())
        out.write("\n")
        with open(intermediate_cert_path) as f2:
            out.write(f2.read())
    return bundle_path


@pytest.fixture(scope="function")
def sample_bundle_config(test_data_dir) -> Path:
    """Return path to a sample bundle configuration."""
    return test_data_dir / "configs" / "bundles" / "test-bundle.yaml"


@pytest.fixture(scope="function")
def sample_env_config(test_data_dir) -> Path:
    """Return path to a sample environment configuration."""
    return test_data_dir / "configs" / "envs" / "test-env.yaml"


@pytest.fixture(autouse=True)
def test_env():
    """Set test-specific environment variables."""
    # Store original values
    old_values = {}
    test_vars = {
        "TRUST_JKS_PASSWORD": "test-password",
        "TRUST_P12_PASSWORD": "test-password",
    }

    # Set test values
    for key, value in test_vars.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, value in old_values.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value
