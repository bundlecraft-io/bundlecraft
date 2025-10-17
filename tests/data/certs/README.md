# Test Certificates

This directory contains **public certificates only** for testing purposes.

## ⚠️ Security Note

**No private keys are stored here.** All certificates are self-signed public test certificates with no corresponding private keys in this repository. Private keys generated during certificate creation are immediately deleted and never committed.

## Certificate Inventory

| File | Purpose | Details |
|------|---------|---------|
| `sample.pem` | Primary test certificate | Self-signed Root CA for general testing |
| `intermediate.pem` | Secondary test certificate | Self-signed Intermediate CA for multi-cert testing |
| `valid-root.pem` | Backup root certificate | Identical to sample.pem, kept as reference |

## Certificate Details

**Subject:** `C=US, ST=Test, L=Test, O=BundleCraft Test, CN=Test Root CA`
**Validity:** 365 days from generation (auto-generated)
**Algorithm:** RSA 2048-bit, SHA256 with RSA Encryption
**Usage:** Testing only - NOT for production use

## Regenerating Test Certificates

If you need to regenerate these test certificates:

```bash
cd tests/data/certs

# Generate new root CA (certificate only, no private key saved)
openssl req -x509 -newkey rsa:2048 \
  -keyout /tmp/temp-key.pem \
  -out sample.pem \
  -days 365 -nodes \
  -subj "/C=US/ST=Test/L=Test/O=BundleCraft Test/CN=Test Root CA"

# Generate intermediate CA
openssl req -x509 -newkey rsa:2048 \
  -keyout /tmp/temp-key.pem \
  -out intermediate.pem \
  -days 365 -nodes \
  -subj "/C=US/ST=Test/L=Test/O=BundleCraft Test/CN=Test Intermediate CA"

# Clean up any temporary keys
rm -f /tmp/temp-key.pem

# Backup root
cp sample.pem valid-root.pem
```

**Important:** Never commit `*-key.pem`, `*_key.pem`, or `key.pem` files. These patterns are blocked by `.gitignore`.

## Verification

Verify certificates are valid and parseable:

```bash
# Check certificate details
openssl x509 -in sample.pem -text -noout | head -20

# Verify it's a certificate (not a key)
openssl x509 -in sample.pem -noout -subject
# Should output: subject=C = US, ST = Test, L = Test, O = BundleCraft Test, CN = Test Root CA
```

## Usage in Tests

These certificates are used by test fixtures in `tests/conftest.py`:
- `sample_cert_path` - Points to sample.pem
- `intermediate_cert_path` - Points to intermediate.pem
- `multi_cert_bundle` - Combines both into a single bundle

See `tests/conftest.py` for fixture definitions and usage examples.
