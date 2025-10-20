"""Tests for intermediate CA filtering functionality."""

from bundlecraft.builder import is_intermediate_ca


class TestIsIntermediateCA:
    """Test suite for intermediate CA detection."""

    def test_root_ca_is_not_intermediate(self):
        """Test that a self-signed root CA is not identified as intermediate."""
        # Actual root CA from sources/internal/rootCA.pem (subject == issuer)
        root_ca_pem = """-----BEGIN CERTIFICATE-----
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
        assert not is_intermediate_ca(root_ca_pem)

    def test_intermediate_ca_is_detected(self):
        """Test that an intermediate CA (issuer != subject) is correctly identified."""
        # Actual intermediate CA from sources/internal/issuingCA1.pem (subject != issuer)
        intermediate_ca_pem = """-----BEGIN CERTIFICATE-----
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
        assert is_intermediate_ca(intermediate_ca_pem)

    def test_invalid_pem_returns_false(self):
        """Test that an invalid PEM block returns False (safe default)."""
        invalid_pem = "This is not a valid PEM certificate"
        assert not is_intermediate_ca(invalid_pem)

    def test_empty_pem_returns_false(self):
        """Test that an empty PEM block returns False."""
        assert not is_intermediate_ca("")
