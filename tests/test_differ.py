"""Tests for BundleCraft diff module."""

import json

import pytest
from click.testing import CliRunner

from bundlecraft.differ import compare_bundles, format_human_readable, format_json, main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_cert_1():
    """Sample certificate 1 (root CA)."""
    return """-----BEGIN CERTIFICATE-----
MIICwzCCAaugAwIBAgIEL0mJWDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAly
b290LXByb2QwHhcNMjUxMDA1MTk1OTMwWhcNMjYxMDA1MTk1OTMwWjAUMRIwEAYD
VQQDDAlyb290LXByb2QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC8
MPq8zC4ApNWad8Y5qf94/e08umiQarRH4gRXAcA3WlkdoVyCZWwbkzNQnP1GjyZ0
IiFRxTeWyYiJb8033ehRHzxJQ6qKtSAHtapnlI8fjztwGOjNxKrqo7EHOMaWJ0b3
dYFfdITOpxtxxH3FpnSFzK/b5pC4883bRRwVSGNNamYSKBuMixVgNnOonGotEa+x
aTJ0vjh3XKW2an0BsEmroRwMgKFGwZVGzXQ7IWMhLgjayTIMtjwzB9AYn6C0BzSW
zWE0Ymq6GU/ZEXcLyoSA9zTEkA79EyCg92O4Zb2Lct0eA0yF1QLtHneH3qLV1LU7
3B0vctVmY9ZlBGeRhRljAgMBAAGjHTAbMAwGA1UdEwQFMAMBAf8wCwYDVR0PBAQD
AgEGMA0GCSqGSIb3DQEBCwUAA4IBAQAjwd2vEqMZKeL4QwZ5xK0givoBiPE9zBC4
mZ/KLdK1vKqCv4uUDRKE+3Vcxd5brUOFkrEkvmLpE7DQyYiNh0NCC2CZc1zT57uK
iApn5KFF4DNwl+x1F+JUlursokjF1fmi2ie/1lbLzzQLzfg3bckEPInGT+cumJ5n
B8uFnc/7fwd1BiJ2fcSCT2xRvXfvRAf4HNtq/xBYiM8BBUc3PRPpxOu+5YOlLtJZ
D4CmYQf3GhxuKHXEwI011lC9ZyBgpZYtfiIbB1wRIbdOa/FakpRKg63f+NrycXuY
rppPl5yxFU82P2JIGr53Ob6LWyyCWiOETuyKAVIEbaJASbtogKjh
-----END CERTIFICATE-----
"""


@pytest.fixture
def sample_cert_2():
    """Sample certificate 2 (issuing CA)."""
    return """-----BEGIN CERTIFICATE-----
MIICxDCCAaygAwIBAgIFASng6W0wDQYJKoZIhvcNAQELBQAwFDESMBAGA1UEAwwJ
cm9vdC1wcm9kMB4XDTI1MTAwNTE5NTkzMFoXDTI2MTAwNTE5NTkzMFowFDESMBAG
A1UEAwwJc3ViMS1wcm9kMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA
wa2aM4BHxZCLdPsqptFdVzBcFQMjQtg98MQhehi3uKGaVHK/x7iWp3xalpriLmUz
eN3DTnf0uRKzwOAlIwhjmGUzIZjQu9FAri60kjktG9ZLV2t+UEosl95qisXZJPdu
0/krNgbqv/eFUKvR8LEP0tMQGk2TfJ4eHQfPLW8VhoINCSjn4FqaO6GthLSUX38L
kP3fHKvT3hGFaAyXe65Qh3eZs+ypxsLoL5o8p5Onm58/03iXxVUMiZ1aK8C18r2T
UlhsrQ4W0K0nlSuJpX+BUcCxL+5SRp9ZsTfLfo0ruwHb3Mwi2W7XTvnHSVB3JuNN
ZM5ri6u99jo5H23T8umixQIDAQABox0wGzAMBgNVHRMEBTADAQH/MAsGA1UdDwQE
AwIBBjANBgkqhkiG9w0BAQsFAAOCAQEAeqtCt6jqOTJAXUrf/DnSnAqq/x4Nz/TZ
4gKp/MTXMkFjrDtcakha5tlmtVYStGs1/yqT7/0pCZSALBQAFAdHe416Ial6mZ/A
5229W19jNcrTTe5kg9boq2wXriRL3bX9nTThbYDRwwXIPQXvF+MEMyFQX3ZzEkph
Elw9eDUMAMaj0gflYeCgLZ1coyHUke9jcOqHbeVsxfeIcPbOpMTpFw4dTGqRl++f
CEoHWoAOkebx7p/h+ZdbOSQ6DVvC22+5T6mDEo0mUYn4SKbgQyR/WG2W0mMcMmbX
rCHd9f8bgTKnbYVEXAskabsPwiWi749vkfUGrgZts3NzYOEeyS/TUA==
-----END CERTIFICATE-----
"""


@pytest.fixture
def bundle_dir_1(tmp_path, sample_cert_1):
    """Create a temporary bundle directory with cert 1."""
    bundle_dir = tmp_path / "bundle1"
    bundle_dir.mkdir()

    # Create PEM file
    pem_file = bundle_dir / "bundlecraft-ca-trust.pem"
    pem_file.write_text(sample_cert_1, encoding="utf-8")

    # Create manifest
    manifest = {
        "craft": "Test",
        "target": "test-bundle",
        "timestamp_utc": "2025-01-01T00:00:00Z",
        "certificate_count": 1,
        "output_formats": ["pem"],
    }
    manifest_file = bundle_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return bundle_dir


@pytest.fixture
def bundle_dir_2(tmp_path, sample_cert_2):
    """Create a temporary bundle directory with cert 2."""
    bundle_dir = tmp_path / "bundle2"
    bundle_dir.mkdir()

    # Create PEM file
    pem_file = bundle_dir / "bundlecraft-ca-trust.pem"
    pem_file.write_text(sample_cert_2, encoding="utf-8")

    # Create manifest
    manifest = {
        "craft": "Test",
        "target": "test-bundle",
        "timestamp_utc": "2025-01-01T12:00:00Z",
        "certificate_count": 1,
        "output_formats": ["pem"],
    }
    manifest_file = bundle_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return bundle_dir


@pytest.fixture
def bundle_dir_both(tmp_path, sample_cert_1, sample_cert_2):
    """Create a temporary bundle directory with both certs."""
    bundle_dir = tmp_path / "bundle_both"
    bundle_dir.mkdir()

    # Create PEM file with both certs
    pem_file = bundle_dir / "bundlecraft-ca-trust.pem"
    pem_file.write_text(sample_cert_1 + "\n" + sample_cert_2, encoding="utf-8")

    # Create manifest
    manifest = {
        "craft": "Test",
        "target": "test-bundle",
        "timestamp_utc": "2025-01-01T12:00:00Z",
        "certificate_count": 2,
        "output_formats": ["pem"],
    }
    manifest_file = bundle_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return bundle_dir


class TestCompareBundles:
    """Test suite for compare_bundles function."""

    def test_compare_identical_bundles(self, bundle_dir_1):
        """Test comparing identical bundles returns no changes."""
        result = compare_bundles(bundle_dir_1, bundle_dir_1)

        assert result["diff"]["summary"]["added_count"] == 0
        assert result["diff"]["summary"]["removed_count"] == 0
        assert result["diff"]["summary"]["unchanged_count"] == 1
        assert result["diff"]["summary"]["total_changes"] == 0

    def test_compare_different_bundles(self, bundle_dir_1, bundle_dir_2):
        """Test comparing different bundles detects changes."""
        result = compare_bundles(bundle_dir_1, bundle_dir_2)

        assert result["diff"]["summary"]["added_count"] == 1
        assert result["diff"]["summary"]["removed_count"] == 1
        assert result["diff"]["summary"]["unchanged_count"] == 0
        assert result["diff"]["summary"]["total_changes"] == 2

        # Check added cert details
        added = result["diff"]["added"][0]
        assert "fingerprint" in added
        assert "subject" in added
        assert added["subject"] == "CN=sub1-prod"

        # Check removed cert details
        removed = result["diff"]["removed"][0]
        assert "fingerprint" in removed
        assert "subject" in removed
        assert removed["subject"] == "CN=root-prod"

    def test_compare_subset_bundles(self, bundle_dir_1, bundle_dir_both):
        """Test comparing bundles where one is a subset of the other."""
        result = compare_bundles(bundle_dir_1, bundle_dir_both)

        assert result["diff"]["summary"]["added_count"] == 1
        assert result["diff"]["summary"]["removed_count"] == 0
        assert result["diff"]["summary"]["unchanged_count"] == 1
        assert result["diff"]["summary"]["total_changes"] == 1

    def test_manifest_metadata_included(self, bundle_dir_1, bundle_dir_2):
        """Test that manifest metadata is included in results."""
        result = compare_bundles(bundle_dir_1, bundle_dir_2)

        assert result["from"]["manifest"] is not None
        assert result["from"]["manifest"]["craft"] == "Test"
        assert result["to"]["manifest"] is not None
        assert result["to"]["manifest"]["craft"] == "Test"


class TestFormatting:
    """Test suite for formatting functions."""

    def test_format_human_readable(self, bundle_dir_1, bundle_dir_2):
        """Test human-readable formatting."""
        result = compare_bundles(bundle_dir_1, bundle_dir_2)
        formatted = format_human_readable(result)

        assert "BUNDLE DIFF REPORT" in formatted
        assert "SUMMARY" in formatted
        assert "Added:     1" in formatted
        assert "Removed:   1" in formatted
        assert "ADDED CERTIFICATES" in formatted
        assert "REMOVED CERTIFICATES" in formatted
        assert "CN=sub1-prod" in formatted
        assert "CN=root-prod" in formatted

    def test_format_human_readable_no_changes(self, bundle_dir_1):
        """Test human-readable formatting with no changes."""
        result = compare_bundles(bundle_dir_1, bundle_dir_1)
        formatted = format_human_readable(result)

        assert "NO CHANGES DETECTED" in formatted
        assert "Total Changes: 0" in formatted

    def test_format_json(self, bundle_dir_1, bundle_dir_2):
        """Test JSON formatting."""
        result = compare_bundles(bundle_dir_1, bundle_dir_2)
        formatted = format_json(result)

        # Verify it's valid JSON
        parsed = json.loads(formatted)
        assert "diff" in parsed
        assert "from" in parsed
        assert "to" in parsed
        assert parsed["diff"]["summary"]["total_changes"] == 2


class TestCLI:
    """Test suite for CLI interface."""

    def test_diff_command_help(self, cli_runner):
        """Test that diff --help works."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Compare two bundle builds" in result.output

    def test_diff_command_human_output(self, cli_runner, bundle_dir_1, bundle_dir_2):
        """Test diff command with human-readable output."""
        result = cli_runner.invoke(main, ["--from", str(bundle_dir_1), "--to", str(bundle_dir_2)])
        assert result.exit_code == 0
        assert "BUNDLE DIFF REPORT" in result.output
        assert "Added:     1" in result.output
        assert "Removed:   1" in result.output

    def test_diff_command_json_output(self, cli_runner, bundle_dir_1, bundle_dir_2):
        """Test diff command with JSON output."""
        result = cli_runner.invoke(
            main,
            ["--from", str(bundle_dir_1), "--to", str(bundle_dir_2), "--output-format", "json"],
        )
        assert result.exit_code == 0

        # Verify output is valid JSON
        parsed = json.loads(result.output)
        assert "diff" in parsed
        assert parsed["diff"]["summary"]["total_changes"] == 2

    def test_diff_command_output_file(self, cli_runner, bundle_dir_1, bundle_dir_2, tmp_path):
        """Test diff command with file output."""
        output_file = tmp_path / "diff-report.txt"
        result = cli_runner.invoke(
            main,
            ["--from", str(bundle_dir_1), "--to", str(bundle_dir_2), "--output", str(output_file)],
        )
        assert result.exit_code == 0
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "BUNDLE DIFF REPORT" in content

    def test_diff_command_no_changes(self, cli_runner, bundle_dir_1):
        """Test diff command with identical bundles."""
        result = cli_runner.invoke(main, ["--from", str(bundle_dir_1), "--to", str(bundle_dir_1)])
        assert result.exit_code == 0
        assert "NO CHANGES DETECTED" in result.output

    def test_diff_command_missing_from(self, cli_runner, bundle_dir_1):
        """Test diff command with missing --from option."""
        result = cli_runner.invoke(main, ["--to", str(bundle_dir_1)])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_diff_command_missing_to(self, cli_runner, bundle_dir_1):
        """Test diff command with missing --to option."""
        result = cli_runner.invoke(main, ["--from", str(bundle_dir_1)])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()
