"""Tests for inline PEM certificate support in builder."""

import pytest
from click.testing import CliRunner

from bundlecraft.builder import main as build_main
from bundlecraft.builder import read_pem_chunks


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_inline_cert():
    """Sample certificate for inline testing."""
    return """-----BEGIN CERTIFICATE-----
MIIDmzCCAoOgAwIBAgIUIXvUHAmF4K0Fg2S0kWfzYNIZLXEwDQYJKoZIhvcNAQEL
BQAwXTELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFRlc3QxDTALBgNVBAcMBFRlc3Qx
GTAXBgNVBAoMEEJ1bmRsZUNyYWZ0IFRlc3QxFTATBgNVBAMMDFRlc3QgUm9vdCBD
QTAeFw0yNTEwMTcxODI0MzBaFw0yNjEwMTcxODI0MzBaMF0xCzAJBgNVBAYTAlVT
MQ0wCwYDVQQIDARUZXN0MQ0wCwYDVQQHDARUZXN0MRkwFwYDVQQKDBBCdW5kbGVD
cmFmdCBUZXN0MRUwEwYDVQQDDAxUZXN0IFJvb3QgQ0EwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQDBJwk4HlYwoxhXUwHfTlmOnyZZwme7uyvgb0Ffi3OC
O81HAavF1FKSxeP6sKsr8QTwV1xt8zJ30r8NCokhpYyNe8GJ1L3UaOuCag886NJu
RXFq+M8RLmNEsu0RCQAo4AwC49aDGPgFCKueYh7rajWGqGK0jZxA85+sjIRZYysp
5XGfVswxSfn6FiSG+a3eYZXNSsLw7vk4L/pxrZgwONgXMcHbH3gZX5ODurFlEmQI
MLRVSl9s8aTcBs1krlbi8OvbidtwIpj8uYVmBZDKMDDnS3qigRGlgshGMQITaM8m
/YU1CmNNZ8PbALMng/VqOZNnFA8XvBAPCHqsFgjVuBPNAgMBAAGjUzBRMB0GA1Ud
DgQWBBQJro4uWYFPXa+0skMQLTlbsZiisDAfBgNVHSMEGDAWgBQJro4uWYFPXa+0
skMQLTlbsZiisDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAf
JDycncrQSna2OBb6livL1qwXmQga0r3aGiE5fGLLeWUIN+jIErWShb4t3/prmYSQ
7Mx49a2CyouEQcm8Lw4VnNidqRJlMeo0ijcruoEUKs/01GuQ3Ndq+KJCtsKihxpv
FyxIEcrfbHstk0k9lMyx2hR97rl4zVYEYR0YcQqEpzYzhNpld9vmYPh0U1gCYH+v
niC4khqnqQsFphoHUsliDbvlcBxNuItvB3GpvpKT8HEtgWEB297HFsPd0HRjMsmo
q+AH75HTFTByvofrYI754KgpmeLjs2I/Yg25eRIPX0JcStStQacbauzGIk4Ihlj/
d36NPeehaDRjISc6//Da
-----END CERTIFICATE-----"""


@pytest.mark.builder
class TestInlinePEM:
    """Test suite for inline PEM certificate support."""

    def test_read_pem_chunks_with_inline(self, sample_inline_cert):
        """Test read_pem_chunks function with inline PEM strings."""
        # Test with only inline PEM
        inline_pems = [sample_inline_cert]
        blocks = read_pem_chunks([], inline_pems)
        
        assert len(blocks) == 1
        assert "-----BEGIN CERTIFICATE-----" in blocks[0]
        assert "-----END CERTIFICATE-----" in blocks[0]

    def test_read_pem_chunks_with_multiple_inline(self, sample_inline_cert):
        """Test read_pem_chunks with multiple inline PEM strings."""
        inline_pems = [sample_inline_cert, sample_inline_cert]
        blocks = read_pem_chunks([], inline_pems)
        
        assert len(blocks) == 2
        for block in blocks:
            assert "-----BEGIN CERTIFICATE-----" in block
            assert "-----END CERTIFICATE-----" in block

    def test_inline_pem_integration(self, cli_runner):
        """Test building with inline PEM using real config files."""
        result = cli_runner.invoke(
            build_main,
            [
                "--env", "test",
                "--bundle", "test-inline",
                "--output-root", "/tmp/test-inline-output",
            ],
        )
        
        # Check that inline PEM is recognized
        assert "Including inline PEM certificate" in result.output or result.exit_code == 0

    def test_inline_pem_multi_integration(self, cli_runner):
        """Test building with multiple inline PEM certificates."""
        result = cli_runner.invoke(
            build_main,
            [
                "--env", "test",
                "--bundle", "test-inline-multi",
                "--output-root", "/tmp/test-inline-multi-output",
            ],
        )
        
        # Should process multiple inline entries
        assert "Including inline PEM certificate" in result.output or result.exit_code == 0
