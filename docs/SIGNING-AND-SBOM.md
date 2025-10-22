# Release Signing and SBOM Generation Guide

## Overview

BundleCraft supports GPG/OpenPGP signing of release artifacts and automatic SBOM (Software Bill of Materials) generation in CycloneDX format. This enables supply chain integrity and production-grade trust verification for your CA trust bundles.

## Key Features

- ✅ **GPG/OpenPGP Signatures**: Sign all release artifacts with detached ASCII-armored signatures (.asc files)
- ✅ **SBOM Generation**: Automatic generation of CycloneDX JSON SBOMs with certificate metadata and provenance
- ✅ **BYOK Model**: Bring Your Own Key - no embedded or auto-generated signing keys
- ✅ **Verification Tooling**: Built-in verification commands for signed releases
- ✅ **CI/CD Ready**: Environment variable support for secure key management in pipelines

---

## GPG Signing

### Prerequisites

**Install GPG:**
```bash
# Ubuntu/Debian
sudo apt-get install gnupg

# macOS
brew install gnupg

# Verify installation
gpg --version
```

### Generate a GPG Key (First Time Setup)

If you don't already have a GPG key for signing:

```bash
# Generate a new key pair
gpg --full-generate-key

# Follow the prompts:
# - Choose (1) RSA and RSA (default)
# - Key size: 4096 bits (recommended for signing)
# - Expiration: 1y or 2y (set an expiration for security)
# - Enter your name and email (this will identify your key)
# - Set a strong passphrase

# List your keys to get the key ID
gpg --list-secret-keys --keyid-format=long

# Output will look like:
# sec   rsa4096/ABCD1234EFGH5678 2025-01-15 [SC] [expires: 2026-01-15]
#       1234567890ABCDEF1234567890ABCDEF12345678
# uid                 [ultimate] Your Name <your.email@example.com>
# ssb   rsa4096/1234ABCD5678EFGH 2025-01-15 [E] [expires: 2026-01-15]

# The key ID is: ABCD1234EFGH5678 (or use the full fingerprint)
```

**Export your public key for verification:**
```bash
# Export to share with others for verification
gpg --armor --export ABCD1234EFGH5678 > public-key.asc
```

### Sign Release Artifacts

**Basic signing during build:**
```bash
# Sign with key ID specified
bundlecraft build --env prod --bundle mozilla \
  --sign --gpg-key-id ABCD1234EFGH5678

# Or use environment variable
export GPG_KEY_ID=ABCD1234EFGH5678
bundlecraft build --env prod --bundle mozilla --sign
```

**With passphrase (optional):**
```bash
# Provide passphrase via environment variable (for CI/CD)
export GPG_KEY_ID=ABCD1234EFGH5678
export GPG_PASSPHRASE="your-passphrase"
bundlecraft build --env prod --bundle mozilla --sign

# Note: If GPG_PASSPHRASE is not set, GPG will prompt for it interactively
```

**What gets signed:**
When `--sign` is used, BundleCraft creates detached signatures (.asc files) for:
- `manifest.json` - Build metadata
- `checksums.sha256` - File integrity checksums
- `bundlecraft-ca-trust.pem` - Canonical PEM bundle
- `bundlecraft-ca-trust.p7b` - PKCS#7 bundle
- `bundlecraft-ca-trust.jks` - Java KeyStore
- `bundlecraft-ca-trust.p12` - PKCS#12 bundle
- `package.tar.gz` - Compressed archive (if packaging is enabled)
- `sbom.json` - Software Bill of Materials

**Example output structure:**
```
dist/Production/mozilla/
├── bundlecraft-ca-trust.pem
├── bundlecraft-ca-trust.pem.asc      # ← GPG signature
├── bundlecraft-ca-trust.p7b
├── bundlecraft-ca-trust.p7b.asc      # ← GPG signature
├── bundlecraft-ca-trust.jks
├── bundlecraft-ca-trust.jks.asc      # ← GPG signature
├── bundlecraft-ca-trust.p12
├── bundlecraft-ca-trust.p12.asc      # ← GPG signature
├── checksums.sha256
├── checksums.sha256.asc              # ← GPG signature
├── manifest.json
├── manifest.json.asc                 # ← GPG signature
├── package.tar.gz
├── package.tar.gz.asc                # ← GPG signature
├── sbom.json
└── sbom.json.asc                     # ← GPG signature
```

### Verify Signed Artifacts

**Using BundleCraft's built-in verification:**
```bash
# Import the public key (one-time setup)
gpg --import public-key.asc

# Verify all signatures in a bundle directory
bundlecraft verify --target dist/Production/mozilla \
  --verify-signatures

# Verify with a specific keyring file
bundlecraft verify --target dist/Production/mozilla \
  --verify-signatures --gpg-keyring public-key.asc

# Verify a single file
bundlecraft verify --target dist/Production/mozilla/bundlecraft-ca-trust.pem \
  --verify-signatures
```

**Manual verification with GPG:**
```bash
# Verify individual files
gpg --verify dist/Production/mozilla/manifest.json.asc \
     dist/Production/mozilla/manifest.json

# Expected output:
# gpg: Signature made Mon 15 Jan 2025 10:30:45 AM UTC
# gpg:                using RSA key ABCD1234EFGH5678
# gpg: Good signature from "Your Name <your.email@example.com>" [ultimate]
```

**Trust the signing key:**
```bash
# After importing, you may need to trust the key
gpg --edit-key ABCD1234EFGH5678
# At the gpg> prompt, type: trust
# Choose trust level (5 = ultimate if it's your key)
# Type: quit
```

---

## SBOM (Software Bill of Materials)

### Overview

BundleCraft automatically generates a CycloneDX JSON SBOM for every build, providing:
- Certificate metadata (serial, issuer, subject, fingerprints, validity dates)
- Fetch provenance (source URLs, verification hashes)
- Tooling metadata (Python version, cryptography version, dependencies)
- Build metadata (craft, target, timestamp, certificate count)

### SBOM Generation

**Enabled by default:**
```bash
# SBOM is generated automatically
bundlecraft build --env prod --bundle mozilla
```

**Disable SBOM generation:**
```bash
# Skip SBOM if not needed
bundlecraft build --env prod --bundle mozilla --no-sbom
```

**SBOM output location:**
```
dist/Production/mozilla/
├── sbom.json                         # ← CycloneDX SBOM
└── (other artifacts)
```

### SBOM Contents

**Example SBOM structure:**
```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "metadata": {
    "component": {
      "name": "bundlecraft-ca-trust-Production-mozilla",
      "version": "2025-01-15T10:30:45Z",
      "type": "data",
      "description": "BundleCraft CA Trust Bundle: Production/mozilla",
      "properties": [
        { "name": "build.craft", "value": "Production" },
        { "name": "build.target", "value": "mozilla" },
        { "name": "build.timestamp", "value": "2025-01-15T10:30:45Z" },
        { "name": "build.certificate_count", "value": "138" },
        { "name": "tool.python_version", "value": "3.12.3" },
        { "name": "tool.cryptography_version", "value": "46.0.3" }
      ]
    }
  },
  "components": [
    {
      "name": "certificate-1",
      "version": "abc123",
      "type": "data",
      "description": "X.509 Certificate: CN=Example Root CA",
      "hashes": [
        {
          "alg": "SHA-256",
          "content": "ca11d3b71361f63926556c9882d4cf70c146bffde1dd4f475b389a0584e1b6b8"
        }
      ],
      "properties": [
        { "name": "subject", "value": "CN=Example Root CA" },
        { "name": "issuer", "value": "CN=Example Root CA" },
        { "name": "serial", "value": "abc123" },
        { "name": "not_before", "value": "2025-01-01T00:00:00Z" },
        { "name": "not_after", "value": "2028-01-01T00:00:00Z" }
      ]
    }
  ]
}
```

### SBOM Use Cases

1. **Supply Chain Security**: Track all certificates and their origins
2. **Compliance**: Provide auditable records of bundle contents
3. **Vulnerability Management**: Identify and track certificate lifecycles
4. **Provenance Tracking**: Verify where certificates were fetched from

### SBOM Tools

**Validate SBOM:**
```bash
# Using cyclonedx-cli (install separately)
cyclonedx validate --input-file dist/Production/mozilla/sbom.json
```

**Convert SBOM formats:**
```bash
# Convert to SPDX (if needed, using third-party tools)
# Note: SPDX format support in BundleCraft is planned for Phase 2
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Sign Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Import GPG key
        run: |
          echo "${{ secrets.GPG_PRIVATE_KEY }}" | base64 -d | gpg --import

      - name: Build and sign bundle
        env:
          GPG_KEY_ID: ${{ secrets.GPG_KEY_ID }}
          GPG_PASSPHRASE: ${{ secrets.GPG_PASSPHRASE }}
        run: |
          bundlecraft build --env prod --bundle mozilla --sign

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: signed-bundle
          path: dist/Production/mozilla/

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/Production/mozilla/package.tar.gz
            dist/Production/mozilla/package.tar.gz.asc
            dist/Production/mozilla/sbom.json
            dist/Production/mozilla/sbom.json.asc
```

### Secret Management

**GitHub Actions Secrets:**
1. `GPG_PRIVATE_KEY`: Base64-encoded GPG private key
   ```bash
   gpg --armor --export-secret-keys ABCD1234EFGH5678 | base64 > gpg-key.b64
   # Add contents of gpg-key.b64 to GitHub Secrets
   ```

2. `GPG_KEY_ID`: Your GPG key ID (e.g., `ABCD1234EFGH5678`)

3. `GPG_PASSPHRASE`: Passphrase for the GPG key

**Other CI Systems:**
- **GitLab CI**: Use GitLab CI/CD variables (masked)
- **Jenkins**: Use Jenkins Credentials Plugin
- **Azure DevOps**: Use Azure Key Vault or Pipeline Variables

---

## Best Practices

### Key Management

1. **Use dedicated signing keys**: Don't use your personal GPG key for automated signing
2. **Set key expiration**: Keys should expire after 1-2 years for security
3. **Rotate keys regularly**: Update to new keys before old ones expire
4. **Store keys securely**: Use secrets management (HashiCorp Vault, AWS Secrets Manager, etc.)
5. **Backup private keys**: Securely backup your private key in case of loss
6. **Publish public keys**: Make your public key available for verification (e.g., in GitHub repo or on keyserver)

### Signing in Production

1. **Always sign production releases**: Use `--sign` for all production builds
2. **Generate SBOMs**: Keep SBOM enabled (default) for supply chain transparency
3. **Verify before distribution**: Always verify signatures before distributing bundles
4. **Document your key**: Include key ID and public key location in release notes
5. **Maintain key registry**: Keep a registry of all signing keys used over time

### Release Workflow

**Recommended release process:**
1. Build with signing enabled
2. Verify all signatures locally
3. Review SBOM for accuracy
4. Upload signed artifacts to release storage
5. Publish public key for verification
6. Include verification instructions in release notes

### Security Considerations

- **Never commit private keys**: Use `.gitignore` to prevent accidental commits
- **Use strong passphrases**: Protect your GPG key with a strong passphrase
- **Limit key access**: Only authorized release managers should have signing keys
- **Monitor key usage**: Track when and where signing keys are used
- **Revoke compromised keys**: If a key is compromised, revoke it immediately and generate a new one

---

## Troubleshooting

### Common Issues

**"GPG key ID not provided"**
```bash
# Solution: Set the key ID
export GPG_KEY_ID=ABCD1234EFGH5678
# Or use --gpg-key-id flag
bundlecraft build --env prod --bundle mozilla --sign --gpg-key-id ABCD1234EFGH5678
```

**"Key not found in keyring"**
```bash
# Solution: Verify key is imported
gpg --list-secret-keys --keyid-format=long
# If missing, import the key
gpg --import private-key.asc
```

**"Bad passphrase"**
```bash
# Solution: Check GPG_PASSPHRASE environment variable
echo $GPG_PASSPHRASE
# Or let GPG prompt interactively (remove GPG_PASSPHRASE)
unset GPG_PASSPHRASE
```

**"Signature verification failed"**
```bash
# Solution: Import the correct public key
gpg --import public-key.asc
# Or specify keyring explicitly
bundlecraft verify --target dist/Production/mozilla \
  --verify-signatures --gpg-keyring public-key.asc
```

**"SBOM generation failed"**
```bash
# Check for dependency issues
pip install cyclonedx-bom
# Or skip SBOM generation if not needed
bundlecraft build --env prod --bundle mozilla --no-sbom
```

---

## References

- [GPG Documentation](https://www.gnupg.org/documentation/)
- [CycloneDX Specification](https://cyclonedx.org/specification/overview/)
- [Supply Chain Security Best Practices](https://slsa.dev/)
- [NIST Guidelines for Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

---

## Support

For questions or issues:
- Open an [issue](https://github.com/bundlecraft-io/bundlecraft/issues)
- Join [GitHub Discussions](https://github.com/bundlecraft-io/bundlecraft/discussions)
