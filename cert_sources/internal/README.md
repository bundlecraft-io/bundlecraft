# Test Certificates - For Development Only

This directory contains **test certificates** used for development and testing of BundleCraft.

## ⚠️ Security Warning

**DO NOT use these certificates in production environments.**

These certificates are:

- Generated for testing purposes only
- Publicly available in this repository
- Not trusted by any system or browser
- May be regenerated or modified at any time

## Purpose

These test certificates allow developers to:

- Test BundleCraft's build and conversion functionality
- Verify multi-format output generation
- Test certificate validation and expiry warnings
- Run integration tests without requiring production CAs

All test certificates are self-signed and created with OpenSSL for development purposes only.

## Generating Test Certificates

To generate new test certificates:

```bash
# From repository root
python scripts/generate_test_cas.py
```

## For Production Use

For production trust bundles:

1. **Remove these test certificates** from your config
2. **Use your organization's actual CA certificates**
3. **Never commit private keys** to version control
4. **Consider using the fetch layer** to retrieve certificates from secure sources

See the main [README.md](../../README.md) and [docs/](../../docs/) for production setup guidance.
