"""Tests for BundleCraft helper modules."""

import pytest

from bundlecraft.helpers import utils


@pytest.mark.helpers
class TestUtils:
    """Test suite for utils helper module."""

    def test_load_yaml_existing_file(self, test_data_dir):
        """Test loading an existing YAML file."""
        yaml_file = test_data_dir / "configs" / "bundles" / "test-bundle.yaml"
        if yaml_file.exists():
            result = utils.load_yaml(yaml_file)
            assert result is not None
            assert isinstance(result, dict)

    def test_load_yaml_missing_file_not_required(self, temp_dir):
        """Test loading missing YAML file when not required."""
        nonexistent = temp_dir / "nonexistent.yaml"
        result = utils.load_yaml(nonexistent, required=False)
        assert result is None

    def test_load_yaml_missing_file_required(self, temp_dir):
        """Test loading missing YAML file when required raises error."""
        nonexistent = temp_dir / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            utils.load_yaml(nonexistent, required=True)

    def test_ensure_dir(self, temp_dir):
        """Test directory creation."""
        new_dir = temp_dir / "test" / "nested" / "dir"
        utils.ensure_dir(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_sha256_file(self, sample_cert_path):
        """Test SHA256 hash calculation."""
        hash_value = utils.sha256_file(sample_cert_path)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 hex digest length
        # Hash should be consistent
        hash_value2 = utils.sha256_file(sample_cert_path)
        assert hash_value == hash_value2

    def test_list_files(self, test_data_dir):
        """Test listing files with specific suffixes."""
        certs_dir = test_data_dir / "certs"
        if certs_dir.exists():
            pem_files = utils.list_files(certs_dir, suffixes=(".pem",))
            assert isinstance(pem_files, list)
