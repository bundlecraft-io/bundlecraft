#!/usr/bin/env python3
"""
Tests for SBOM generation functionality in BundleCraft.
"""

import json

import pytest

from bundlecraft.helpers.sbom import (
    _extract_certificate_metadata,
    _get_tooling_metadata,
    generate_cyclonedx_sbom,
    generate_spdx_sbom,
)

# Sample PEM certificate for testing (valid X.509 certificate)
SAMPLE_PEM = """-----BEGIN CERTIFICATE-----
MIIDaTCCAlGgAwIBAgIUFX25F8LAQCsyvO7QhP2TPrBbU3UwDQYJKoZIhvcNAQEL
BQAwZDELMAkGA1UEBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExFjAUBgNVBAcM
DVNhbiBGcmFuY2lzY28xETAPBgNVBAoMCFRlc3QgT3JnMRUwEwYDVQQDDAxUZXN0
IFJvb3QgQ0EwHhcNMjUwMTAxMDAwMDAwWhcNMjgwMTAxMDAwMDAwWjBkMQswCQYD
VQQGEwJVUzETMBEGA1UECAwKQ2FsaWZvcm5pYTEWMBQGA1UEBwwNU2FuIEZyYW5j
aXNjbzERMA8GA1UECgwIVGVzdCBPcmcxFTATBgNVBAMMDFRlc3QgUm9vdCBDQTCC
ASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANfPWSDmn+pIfrIb+JCQKLK+
bRQu1giBs01xlG84ZrEoc6o1rwM7nUOx7d9Jc5vXRSTz1QV8Bv8I7v1eQNoKKL+0
AiZyaf7CQTtkyAYpTXelq/p9KlDb1jkl5atk4ntigZ/HOiRkmEqGyXGkxpqnJDbc
Mat16rIxHJOrVsO7MF+8n3P6OA63qlwpEh9qX15d9PxXCJuk/OKBtb5S2K3XlqHI
pEipiQfmsFRnTvTk8YMSI/6Obq34hLuOXD2PHRQhevqaOiTVfwRMpGt78f3Ppukg
gAuSi9dQ54X3Kt4uzCcmCahbnOTuF1NarTVBwYLgAjyV1hVQGeHzD2f1W//SNUsC
AwEAAaMTMBEwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAHSt5
x/ixVnEgNDImWZYg3rpNN2Tvd4SHNhWc1oJmHf7L2JScKZ4yC+hd6y9auu60HBSW
ZRfj+WD3cMCDm0ndgO/cbhQb2AfsMMFt5ozyKj60wMHKlJgBZ/dbGYRwk+Kr/K0m
LmtzZSij74wAkDnNvz9iYZRsQmB3ifYhWySXR4rBUnDi0W2KUlvv4w7N1fvZFpKM
olcU0okD//zkwxztkhK2s9P4KuglBY6con+SSfWto4aGJWowCGYJU5yXEFRVwXhQ
TRasv8J23Lr575NzvF+SN+RwT5pthcRHh2ZZGt6JJnYkwriAHMi7xttJCu9xeRUz
LojuJvxA9WuJ7fip6w==
-----END CERTIFICATE-----"""


@pytest.fixture
def temp_build_dir(tmp_path):
    """Create a temporary build directory for testing."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    return build_dir


@pytest.fixture
def sample_manifest():
    """Create a sample build manifest."""
    return {
        "env": "test-env",
        "target": "test-bundle",
        "timestamp_utc": "2025-01-15T12:00:00Z",
        "certificate_count": 1,
        "output_formats": ["pem", "p7b", "jks", "p12"],
    }


class TestExtractCertificateMetadata:
    def test_extract_valid_certificate(self):
        """Test extracting metadata from a valid certificate."""
        metadata = _extract_certificate_metadata(SAMPLE_PEM)

        assert "subject" in metadata
        assert "issuer" in metadata
        assert "serial" in metadata
        assert "not_before" in metadata
        assert "not_after" in metadata
        assert "fingerprint_sha256" in metadata
        assert "fingerprint_sha1" in metadata
        assert "error" not in metadata

        # Verify subject contains expected values
        assert "Test Root CA" in metadata["subject"]

    def test_extract_invalid_certificate(self):
        """Test extracting metadata from invalid PEM."""
        invalid_pem = "This is not a valid certificate"
        metadata = _extract_certificate_metadata(invalid_pem)

        assert metadata["subject"] == "(unparsable)"
        assert metadata["issuer"] == "(unparsable)"
        assert "error" in metadata

    def test_extract_empty_certificate(self):
        """Test extracting metadata from empty string."""
        metadata = _extract_certificate_metadata("")

        assert metadata["subject"] == "(unparsable)"
        assert "error" in metadata


class TestGetToolingMetadata:
    def test_get_tooling_metadata(self):
        """Test getting tooling metadata."""
        metadata = _get_tooling_metadata()

        assert "python_version" in metadata
        assert "python_implementation" in metadata
        assert "platform" in metadata
        assert "cryptography_version" in metadata
        assert "click_version" in metadata

        # Verify versions are present
        assert metadata["python_version"]
        assert metadata["cryptography_version"] != "unknown"


class TestGenerateCycloneDxSbom:
    def test_generate_basic_sbom(self, temp_build_dir, sample_manifest):
        """Test generating a basic CycloneDX SBOM."""
        pem_blocks = [SAMPLE_PEM]

        sbom_path = generate_cyclonedx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        assert sbom_path.exists()
        assert sbom_path.name == "sbom.json"

        # Parse and verify SBOM structure
        sbom_data = json.loads(sbom_path.read_text())

        assert "bomFormat" in sbom_data
        assert sbom_data["bomFormat"] == "CycloneDX"
        assert "specVersion" in sbom_data
        assert "metadata" in sbom_data
        assert "components" in sbom_data

        # Verify metadata component
        assert "component" in sbom_data["metadata"]
        component = sbom_data["metadata"]["component"]
        assert "bundlecraft-ca-trust" in component["name"]
        assert component["type"] == "data"

    def test_generate_sbom_with_multiple_certificates(self, temp_build_dir, sample_manifest):
        """Test generating SBOM with multiple certificates."""
        pem_blocks = [SAMPLE_PEM, SAMPLE_PEM, SAMPLE_PEM]

        sbom_path = generate_cyclonedx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        sbom_data = json.loads(sbom_path.read_text())

        # Should have at least 3 certificate components
        components = sbom_data.get("components", [])
        cert_components = [c for c in components if c["name"].startswith("certificate-")]
        assert len(cert_components) >= 3

    def test_generate_sbom_with_provenance(self, temp_build_dir, sample_manifest):
        """Test generating SBOM with fetch provenance information."""
        sample_manifest["fetched"] = [
            {
                "name": "mozilla_roots",
                "type": "url",
                "url": "https://curl.se/ca/cacert.pem",
                "sha256": "abc123def456",
            }
        ]
        pem_blocks = [SAMPLE_PEM]

        sbom_path = generate_cyclonedx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        sbom_data = json.loads(sbom_path.read_text())

        # Verify provenance component is included
        components = sbom_data.get("components", [])
        provenance_components = [c for c in components if c["name"].startswith("provenance-")]
        assert len(provenance_components) > 0

        # Verify external reference
        prov_comp = provenance_components[0]
        assert "externalReferences" in prov_comp

    def test_generate_sbom_custom_output_path(self, temp_build_dir, sample_manifest):
        """Test generating SBOM with custom output path."""
        custom_path = temp_build_dir / "custom-sbom.json"
        pem_blocks = [SAMPLE_PEM]

        sbom_path = generate_cyclonedx_sbom(
            temp_build_dir, sample_manifest, pem_blocks, output_path=custom_path
        )

        assert sbom_path == custom_path
        assert sbom_path.exists()

    def test_generate_sbom_empty_certificates(self, temp_build_dir, sample_manifest):
        """Test generating SBOM with no certificates."""
        pem_blocks = []

        sbom_path = generate_cyclonedx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        assert sbom_path.exists()
        sbom_data = json.loads(sbom_path.read_text())

        # SBOM should still be valid even with no certificates
        assert "bomFormat" in sbom_data
        assert sbom_data["bomFormat"] == "CycloneDX"


class TestGenerateSpdxSbom:
    def test_spdx_not_implemented(self, temp_build_dir, sample_manifest):
        """Test that SPDX format raises NotImplementedError."""
        pem_blocks = [SAMPLE_PEM]

        with pytest.raises(NotImplementedError) as exc_info:
            generate_spdx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        assert "SPDX format support is planned for Phase 2" in str(exc_info.value)
        assert "CycloneDX" in str(exc_info.value)


class TestSbomIntegration:
    def test_sbom_includes_tooling_metadata(self, temp_build_dir, sample_manifest):
        """Test that SBOM includes tooling metadata as properties."""
        pem_blocks = [SAMPLE_PEM]

        sbom_path = generate_cyclonedx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        sbom_data = json.loads(sbom_path.read_text())

        # Check for tooling properties in main component
        component = sbom_data["metadata"]["component"]
        if "properties" in component:
            properties = component["properties"]
            tool_properties = [p for p in properties if p["name"].startswith("tool.")]
            assert len(tool_properties) > 0

    def test_sbom_includes_build_metadata(self, temp_build_dir, sample_manifest):
        """Test that SBOM includes build metadata as properties."""
        pem_blocks = [SAMPLE_PEM]

        sbom_path = generate_cyclonedx_sbom(temp_build_dir, sample_manifest, pem_blocks)

        sbom_data = json.loads(sbom_path.read_text())

        # Check for build properties in main component
        component = sbom_data["metadata"]["component"]
        if "properties" in component:
            properties = component["properties"]
            build_properties = [p for p in properties if p["name"].startswith("build.")]
            assert len(build_properties) > 0

            # Verify specific build properties
            prop_names = [p["name"] for p in build_properties]
            assert "build.env" in prop_names
            assert "build.target" in prop_names
            assert "build.certificate_count" in prop_names
