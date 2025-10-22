"""Tests for output metadata templating functionality."""

import datetime as dt

from bundlecraft.helpers.template_utils import (
    expand_metadata_dict,
    expand_output_metadata,
    expand_template_variables,
    get_git_commit,
)


class TestGetGitCommit:
    """Test git commit hash retrieval."""

    def test_get_git_commit_returns_string(self):
        """Test that get_git_commit returns a string."""
        result = get_git_commit()
        assert isinstance(result, str)
        # Should be either a 7-char hash or 'unknown'
        assert len(result) == 7 or result == "unknown"


class TestExpandTemplateVariables:
    """Test template variable expansion."""

    def test_expand_bundle_variable(self):
        """Test expansion of {{bundle}} variable."""
        result = expand_template_variables("prefix-{{bundle}}-suffix", bundle="test-bundle")
        assert result == "prefix-test-bundle-suffix"

    def test_expand_env_variable(self):
        """Test expansion of {{env}} variable."""
        result = expand_template_variables("{{env}}-bundle", env="production")
        assert result == "production-bundle"

    def test_expand_multiple_variables(self):
        """Test expansion of multiple variables."""
        result = expand_template_variables("{{bundle}}-{{env}}", bundle="internal", env="prod")
        assert result == "internal-prod"

    def test_expand_date_variable(self):
        """Test expansion of {{date}} variable."""
        result = expand_template_variables("build-{{date}}")
        # Should match YYYY-MM-DD format
        assert result.startswith("build-")
        date_part = result.replace("build-", "")
        # Validate date format
        dt.datetime.strptime(date_part, "%Y-%m-%d")

    def test_expand_timestamp_variable(self):
        """Test expansion of {{timestamp}} variable."""
        result = expand_template_variables("{{timestamp}}")
        # Should be ISO 8601 format
        assert "T" in result
        assert result.endswith("Z")

    def test_expand_git_commit_variable(self):
        """Test expansion of {{git_commit}} variable."""
        result = expand_template_variables("commit-{{git_commit}}")
        assert result.startswith("commit-")
        commit_part = result.replace("commit-", "")
        assert len(commit_part) == 7 or commit_part == "unknown"

    def test_expand_with_custom_timestamp(self):
        """Test expansion with provided timestamp."""
        timestamp = "2025-10-21T12:00:00Z"
        result = expand_template_variables("{{date}}-{{timestamp}}", timestamp_utc=timestamp)
        assert result == "2025-10-21-2025-10-21T12:00:00Z"

    def test_expand_no_variables(self):
        """Test expansion with no template variables."""
        result = expand_template_variables("plain-text", bundle="test")
        assert result == "plain-text"

    def test_expand_empty_string(self):
        """Test expansion of empty string."""
        result = expand_template_variables("", bundle="test")
        assert result == ""

    def test_expand_unknown_variable(self):
        """Test that unknown variables are left unchanged."""
        result = expand_template_variables("{{unknown}}", bundle="test")
        assert result == "{{unknown}}"


class TestExpandMetadataDict:
    """Test metadata dictionary expansion."""

    def test_expand_simple_dict(self):
        """Test expansion of simple metadata dict."""
        metadata = {
            "build-id": "{{bundle}}-{{env}}",
            "environment": "{{env}}",
        }
        result = expand_metadata_dict(metadata, bundle="internal", env="prod")
        assert result == {
            "build-id": "internal-prod",
            "environment": "prod",
        }

    def test_expand_empty_dict(self):
        """Test expansion of empty dict."""
        result = expand_metadata_dict({})
        assert result == {}

    def test_expand_dict_with_no_variables(self):
        """Test expansion of dict with no template variables."""
        metadata = {
            "static-key": "static-value",
        }
        result = expand_metadata_dict(metadata)
        assert result == metadata


class TestExpandOutputMetadata:
    """Test output metadata expansion."""

    def test_expand_annotations_and_labels(self):
        """Test expansion of both annotations and labels."""
        output_metadata = {
            "annotations": {
                "build-timestamp": "{{timestamp}}",
                "bundle-version": "{{bundle}}-{{env}}-{{date}}",
            },
            "labels": {
                "environment": "{{env}}",
                "bundle-id": "{{bundle}}",
            },
        }
        timestamp = "2025-10-21T12:00:00Z"
        result = expand_output_metadata(
            output_metadata, bundle="internal", env="prod", timestamp_utc=timestamp
        )
        assert result is not None
        assert "annotations" in result
        assert "labels" in result
        assert result["annotations"]["build-timestamp"] == timestamp
        assert result["annotations"]["bundle-version"] == "internal-prod-2025-10-21"
        assert result["labels"]["environment"] == "prod"
        assert result["labels"]["bundle-id"] == "internal"

    def test_expand_annotations_only(self):
        """Test expansion with annotations only."""
        output_metadata = {
            "annotations": {
                "sync-wave": "1",
                "bundle": "{{bundle}}",
            }
        }
        result = expand_output_metadata(output_metadata, bundle="test")
        assert result is not None
        assert "annotations" in result
        assert "labels" not in result
        assert result["annotations"]["sync-wave"] == "1"
        assert result["annotations"]["bundle"] == "test"

    def test_expand_labels_only(self):
        """Test expansion with labels only."""
        output_metadata = {
            "labels": {
                "app": "bundlecraft",
                "env": "{{env}}",
            }
        }
        result = expand_output_metadata(output_metadata, env="staging")
        assert result is not None
        assert "labels" in result
        assert "annotations" not in result
        assert result["labels"]["env"] == "staging"

    def test_expand_none_metadata(self):
        """Test expansion with None input."""
        result = expand_output_metadata(None)
        assert result is None

    def test_expand_empty_metadata(self):
        """Test expansion with empty dict."""
        result = expand_output_metadata({})
        assert result is None

    def test_expand_empty_annotations_and_labels(self):
        """Test expansion with empty annotations and labels."""
        output_metadata = {
            "annotations": {},
            "labels": {},
        }
        result = expand_output_metadata(output_metadata)
        assert result is None


class TestTemplateExpansionIntegration:
    """Integration tests for template expansion."""

    def test_realistic_argocd_metadata(self):
        """Test realistic ArgoCD metadata expansion."""
        output_metadata = {
            "annotations": {
                "argocd.argoproj.io/sync-wave": "1",
                "build-timestamp": "{{timestamp}}",
                "bundle-version": "{{bundle}}-{{env}}-{{date}}",
                "git-commit": "{{git_commit}}",
            },
            "labels": {
                "environment": "{{env}}",
                "bundle-id": "{{bundle}}",
                "app.kubernetes.io/component": "trust-bundle",
                "app.kubernetes.io/managed-by": "bundlecraft",
            },
        }
        timestamp = "2025-10-21T05:00:00Z"
        result = expand_output_metadata(
            output_metadata, bundle="internal-prod", env="production", timestamp_utc=timestamp
        )

        assert result is not None
        assert result["annotations"]["argocd.argoproj.io/sync-wave"] == "1"
        assert result["annotations"]["build-timestamp"] == timestamp
        assert result["annotations"]["bundle-version"] == "internal-prod-production-2025-10-21"
        assert result["labels"]["environment"] == "production"
        assert result["labels"]["bundle-id"] == "internal-prod"
        assert result["labels"]["app.kubernetes.io/component"] == "trust-bundle"

    def test_realistic_flux_metadata(self):
        """Test realistic Flux metadata expansion."""
        output_metadata = {
            "annotations": {
                "kustomize.toolkit.fluxcd.io/prune": "true",
                "build-date": "{{date}}",
            },
            "labels": {
                "kustomize.toolkit.fluxcd.io/name": "trust-bundles",
                "environment": "{{env}}",
            },
        }
        result = expand_output_metadata(
            output_metadata, env="dev", timestamp_utc="2025-10-21T12:00:00Z"
        )

        assert result is not None
        assert result["labels"]["environment"] == "dev"
        assert result["annotations"]["build-date"] == "2025-10-21"


class TestOutputMetadataInBuild:
    """Integration tests for output metadata in actual builds."""

    def test_output_metadata_in_manifest(self, tmp_path):
        """Test that output metadata appears in manifest.json."""
        import json
        import shutil
        from pathlib import Path

        import yaml
        from click.testing import CliRunner

        from bundlecraft.builder import main as build_main

        # Setup test workspace
        temp = tmp_path
        (temp / "config" / "envs").mkdir(parents=True, exist_ok=True)
        (temp / "config" / "sources").mkdir(parents=True, exist_ok=True)
        (temp / "sources" / "internal").mkdir(parents=True, exist_ok=True)

        # Create env config with output_metadata
        craft_yaml = temp / "config" / "envs" / "test.yaml"
        craft_yaml.write_text(
            """
name: TestCraft
description: Test env
bundles:
  test-bundle:
    include_sources: [test-bundle]
output_formats: [pem]
output_metadata:
  annotations:
    build-timestamp: "{{timestamp}}"
    bundle-version: "{{bundle}}-{{env}}"
  labels:
    environment: "{{env}}"
    bundle-id: "{{bundle}}"
""".strip()
        )

        # Create bundle config
        bundle_yaml = temp / "config" / "sources" / "test-bundle.yaml"
        bundle_yaml.write_text(
            """
source_name: test-bundle
description: Test bundle
repo:
  - name: internal
    include: [cert_sources/internal/]
""".strip()
        )

        # Copy sample certificate (CI path) or generate one locally if unavailable
        sample_pem_src = Path(
            "/home/runner/work/bundlecraft/bundlecraft/tests/data/certs/sample.pem"
        )
        sample_dest = temp / "sources" / "internal" / "sample.pem"
        if sample_pem_src.exists():
            shutil.copyfile(sample_pem_src, sample_dest)
        else:
            # Generate a minimal valid self-signed certificate for the test
            try:
                import datetime as _dt

                from cryptography import x509
                from cryptography.hazmat.backends import default_backend
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.x509.oid import NameOID

                key = rsa.generate_private_key(
                    public_exponent=65537, key_size=2048, backend=default_backend()
                )
                subject = issuer = x509.Name(
                    [x509.NameAttribute(NameOID.COMMON_NAME, "Test Root CA")]
                )
                cert = (
                    x509.CertificateBuilder()
                    .subject_name(subject)
                    .issuer_name(issuer)
                    .public_key(key.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(_dt.datetime.now(_dt.timezone.utc))
                    .not_valid_after(_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=365))
                    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                    .sign(key, hashes.SHA256(), default_backend())
                )
                sample_dest.write_text(
                    cert.public_bytes(serialization.Encoding.PEM).decode("utf-8"),
                    encoding="utf-8",
                )
            except Exception as _e:
                # As a last resort, write a placeholder that will still be parsed in earlier steps
                sample_dest.write_text(
                    """-----BEGIN CERTIFICATE-----\nMIIBszCCAVugAwIBAgIUXo0EtesttesttesttesttesttestMAoGCCqGSM49BAMC\nMDQxMjAwBgNVBAMMKVRlc3QgUm9vdCBDQSAoR2VuZXJhdGVkIGJ5IHRlc3QpMB4X\nDTI1MTAyMTAwMDAwMFoXDTI2MTAyMTAwMDAwMFowNDEyMDBgA1UEAwwlVGVzdCBS\nb290IENBIChHZW5lcmF0ZWQgYnkgdGVzdCkwWTATBgcqhkjOPQIBBggqhkjOPQMB\nwAIBAAIBAQD7z6n9m+Zc3Sfr3i3e7QIDAQABMAoGCCqGSM49BAMCA0kAMEYCIQCH\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIhAP//////////\n//////////8AAAAAAAAAAAAAAAAAAAAA\n-----END CERTIFICATE-----\n""",
                    encoding="utf-8",
                )

        # Monkeypatch
        import bundlecraft.builder as builder_mod

        builder_mod.ROOT = temp
        builder_mod.CONFIG_DIR = temp / "config"
        builder_mod.SOURCES_DIR = temp / "sources"
        builder_mod.STAGED_DIR = temp / "sources" / "staged"
        builder_mod.DIST_DIR = temp / "dist"

        # Run build
        runner = CliRunner()
        result = runner.invoke(build_main, ["--env", "test", "--output-root", str(temp / "dist")])

        # Check that build succeeded
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Check manifest.json exists
        manifest_path = temp / "dist" / "TestCraft" / "test-bundle" / "manifest.json"
        assert manifest_path.exists(), "manifest.json not created"

        # Load and validate manifest
        manifest = json.loads(manifest_path.read_text())
        assert "output_metadata" in manifest, "output_metadata not in manifest"

        # Check annotations
        assert "annotations" in manifest["output_metadata"]
        annotations = manifest["output_metadata"]["annotations"]
        assert "build-timestamp" in annotations
        assert "bundle-version" in annotations
        assert annotations["bundle-version"] == "test-bundle-test"

        # Check labels
        assert "labels" in manifest["output_metadata"]
        labels = manifest["output_metadata"]["labels"]
        assert labels["environment"] == "test"
        assert labels["bundle-id"] == "test-bundle"

        # Check that metadata.yaml sidecar exists
        metadata_yaml_path = temp / "dist" / "TestCraft" / "test-bundle" / "metadata.yaml"
        assert metadata_yaml_path.exists(), "metadata.yaml sidecar not created"

        # Validate YAML sidecar content
        metadata_yaml = yaml.safe_load(metadata_yaml_path.read_text())
        assert "annotations" in metadata_yaml
        assert "labels" in metadata_yaml
        assert metadata_yaml["labels"]["environment"] == "test"
