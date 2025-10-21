# Artifact Signing and Verification

BundleCraft supports optional signing and verification of build artifacts using GPG or Sigstore. This feature enables you to create cryptographic signatures for your trust bundles, ensuring their authenticity and integrity.

## Overview

Artifact signing provides:

- **Authenticity**: Verify that artifacts were created by a trusted source
- **Integrity**: Detect any tampering or modification of artifacts
- **Non-repudiation**: Cryptographic proof of origin
- **Compliance**: Meet regulatory requirements for signed artifacts

## Supported Signing Methods

### GPG (GNU Privacy Guard)

GPG provides traditional PGP/OpenPGP signing using asymmetric cryptography. GPG is widely supported and works offline.

**Requirements:**
- GPG installed on the system (`gpg` command available)
- A GPG key pair for signing
- Public key distribution for verification

### Sigstore (Cosign)

Sigstore provides keyless signing using OIDC identity and transparency logs. Ideal for CI/CD environments.

**Requirements:**
- Cosign installed on the system (`cosign` command available)
- OIDC provider for authentication (GitHub, Google, etc.)
- Internet access for transparency log

## Configuration

Signing is configured via environment variables:

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BUNDLECRAFT_SIGN_METHOD` | Signing method: `gpg`, `sigstore`, or `none` | `none` |
| `BUNDLECRAFT_GPG_KEY_ID` | GPG key ID to use for signing | *(none)* |
| `BUNDLECRAFT_GPG_PASSPHRASE` | Passphrase for GPG key (use secure methods!) | *(none)* |
| `BUNDLECRAFT_GPG_HOME` | Custom GPG home directory | *(default)* |

### Example: GPG Configuration

```bash
# Set signing method
export BUNDLECRAFT_SIGN_METHOD=gpg

# Specify GPG key ID (fingerprint or email)
export BUNDLECRAFT_GPG_KEY_ID=user@example.com

# Optional: Set passphrase (not recommended for production)
export BUNDLECRAFT_GPG_PASSPHRASE=secret

# Optional: Use custom GPG home
export BUNDLECRAFT_GPG_HOME=/path/to/gpg-home
```

### Example: Sigstore Configuration

```bash
# Set signing method
export BUNDLECRAFT_SIGN_METHOD=sigstore

# Sigstore uses keyless signing with OIDC
# No additional configuration needed
```

## Usage

### Signing During Build

Sign artifacts automatically during the build process:

```bash
# Sign using method from environment
bundlecraft build --craft prod --sign

# Override signing method via CLI
bundlecraft build --craft prod --sign --sign-method gpg
```

This will:
1. Build the trust bundle as usual
2. Sign the `manifest.json` file
3. Create a signature file (e.g., `manifest.json.asc` for GPG)

### Manual Signing

Sign individual files using the `sign` command:

```bash
# Sign a file with GPG
bundlecraft sign --file dist/prod/ca-bundle/manifest.json --method gpg

# Sign a file with Sigstore
bundlecraft sign --file dist/prod/ca-bundle/manifest.json --method sigstore

# Sign with specific GPG key
bundlecraft sign \
  --file dist/prod/ca-bundle/manifest.json \
  --method gpg \
  --gpg-key-id user@example.com
```

### Signature Verification

Verify signatures during verification:

```bash
# Verify bundle and signatures
bundlecraft verify --target dist/prod/ca-bundle --verify-signatures

# Require signatures (fail if missing)
bundlecraft verify \
  --target dist/prod/ca-bundle \
  --verify-signatures \
  --signature-required
```

### Manual Verification

Verify individual file signatures:

```bash
# Auto-detect signature method
bundlecraft sign --verify --file dist/prod/ca-bundle/manifest.json

# Specify method explicitly
bundlecraft sign --verify --file dist/prod/ca-bundle/manifest.json --method gpg
```

## Signature File Formats

BundleCraft creates detached signature files alongside the signed artifacts:

| Method | Extension | Format | Description |
|--------|-----------|--------|-------------|
| GPG | `.asc` | ASCII-armored | Human-readable, copy-paste friendly |
| Sigstore | `.sig` | Binary | Compact binary signature |

### Example Directory Structure

After signing, your build directory will contain:

```
dist/prod/ca-bundle/
├── bundlecraft-ca-trust.pem
├── bundlecraft-ca-trust.jks
├── bundlecraft-ca-trust.p12
├── checksums.sha256
├── manifest.json
└── manifest.json.asc        ← GPG signature
```

## CI/CD Integration

### GitHub Actions Example (GPG)

```yaml
- name: Build and Sign with GPG
  env:
    BUNDLECRAFT_SIGN_METHOD: gpg
    BUNDLECRAFT_GPG_KEY_ID: ${{ secrets.GPG_KEY_ID }}
    BUNDLECRAFT_GPG_PASSPHRASE: ${{ secrets.GPG_PASSPHRASE }}
  run: |
    # Import GPG key from secret
    echo "${{ secrets.GPG_PRIVATE_KEY }}" | gpg --import
    
    # Build and sign
    bundlecraft build --craft prod --sign

- name: Verify Signatures
  run: |
    bundlecraft verify \
      --target dist/prod/ca-bundle \
      --verify-signatures \
      --signature-required
```

### GitHub Actions Example (Sigstore)

```yaml
- name: Install Cosign
  uses: sigstore/cosign-installer@v3

- name: Build and Sign with Sigstore
  env:
    BUNDLECRAFT_SIGN_METHOD: sigstore
  run: |
    bundlecraft build --craft prod --sign
  # Cosign will use OIDC from GitHub Actions token

- name: Verify Signatures
  run: |
    bundlecraft verify \
      --target dist/prod/ca-bundle \
      --verify-signatures
```

## Security Best Practices

### GPG Key Management

1. **Key Generation**: Use strong keys (RSA 4096-bit or ECC)
   ```bash
   gpg --full-generate-key
   ```

2. **Key Protection**: 
   - Never commit private keys to version control
   - Use strong passphrases
   - Store keys in secure vaults (Vault, Azure Key Vault, etc.)

3. **Key Distribution**:
   - Publish public keys to keyservers
   - Include public key fingerprint in documentation
   - Provide verification instructions

4. **Key Rotation**:
   - Rotate signing keys periodically
   - Maintain a key revocation certificate
   - Update documentation when keys change

### Passphrase Handling

**DO NOT** hardcode passphrases in scripts or configs. Use:

- **CI/CD Secrets**: GitHub Secrets, GitLab CI/CD variables
- **Environment Files**: `.env` files (gitignored)
- **Secret Managers**: Vault, AWS Secrets Manager, Azure Key Vault
- **GPG Agent**: For interactive signing

### Signature Verification

1. **Always verify** signatures in production deployments
2. **Require signatures** for critical environments (`--signature-required`)
3. **Automate verification** in deployment pipelines
4. **Monitor** signature verification failures

## Troubleshooting

### GPG Not Found

**Error**: `GPG is not available. Please install GnuPG.`

**Solution**: Install GPG:
```bash
# Debian/Ubuntu
apt-get install gnupg

# macOS
brew install gnupg

# RHEL/CentOS
yum install gnupg2
```

### GPG Signing Failed

**Error**: `GPG signing failed: gpg: signing failed: No secret key`

**Solution**: Verify key ID is correct and key exists:
```bash
gpg --list-secret-keys
```

### Passphrase Issues

**Error**: `gpg: signing failed: Inappropriate ioctl for device`

**Solution**: Use `--pinentry-mode loopback` or configure GPG agent:
```bash
export GPG_TTY=$(tty)
echo "use-agent" >> ~/.gnupg/gpg.conf
```

### Sigstore/Cosign Not Found

**Error**: `Sigstore (cosign) is not available.`

**Solution**: Install Cosign:
```bash
# Using brew
brew install sigstore/tap/cosign

# Using binary
curl -LO https://github.com/sigstore/cosign/releases/download/v2.2.0/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
```

### Signature Verification Failed

**Error**: `Signature verification: FAILED`

**Possible causes**:
1. File was modified after signing
2. Wrong public key used for verification
3. Signature file is corrupted
4. Key has expired or been revoked

**Solution**: Re-sign the file or investigate the cause of modification.

## Examples

### Complete GPG Workflow

```bash
# 1. Generate a GPG key (one-time setup)
gpg --full-generate-key

# 2. Export public key for distribution
gpg --armor --export user@example.com > public-key.asc

# 3. Configure signing
export BUNDLECRAFT_SIGN_METHOD=gpg
export BUNDLECRAFT_GPG_KEY_ID=user@example.com

# 4. Build and sign
bundlecraft build --craft prod --sign

# 5. Verify locally
bundlecraft verify --target dist/prod/ca-bundle --verify-signatures

# 6. Distribute artifacts and public key
# Users can verify with:
gpg --import public-key.asc
bundlecraft sign --verify --file manifest.json
```

### Complete Sigstore Workflow

```bash
# 1. Install Cosign
brew install sigstore/tap/cosign

# 2. Configure signing
export BUNDLECRAFT_SIGN_METHOD=sigstore

# 3. Build and sign (uses keyless signing)
bundlecraft build --craft prod --sign

# 4. Verify
bundlecraft verify --target dist/prod/ca-bundle --verify-signatures

# Signatures are verified against Sigstore's transparency log
```

## FAQ

**Q: Which signing method should I use?**

A: 
- **GPG**: Traditional environments, offline signing, long-term key management
- **Sigstore**: Modern CI/CD, keyless signing, transparency logs

**Q: Can I sign all bundle files, not just the manifest?**

A: Currently, BundleCraft signs the manifest.json file, which contains checksums of all bundle files. Verifying the manifest ensures the integrity of all files. Future versions may support signing additional artifacts.

**Q: How do I verify signatures without BundleCraft?**

A:
```bash
# GPG
gpg --verify manifest.json.asc manifest.json

# Cosign
cosign verify-blob --signature manifest.json.sig manifest.json
```

**Q: Can I use multiple signing methods?**

A: No, only one signing method can be active at a time. However, you can manually sign with multiple methods if needed.

**Q: Is signing required?**

A: No, signing is optional. Set `BUNDLECRAFT_SIGN_METHOD=none` (default) to disable signing.

## See Also

- [GPG Documentation](https://gnupg.org/documentation/)
- [Sigstore Documentation](https://docs.sigstore.dev/)
- [BundleCraft Security Guide](./SECURITY.md)
- [CI/CD Integration](./README.md#cicd-integration)
