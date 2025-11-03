# BundleCraft Configuration Examples

This directory contains example configurations demonstrating various BundleCraft features and use cases.

## Fetcher Examples

### Quick Start Examples

**File:** `quick-start-fetchers.yaml`

Simple, minimal configurations for common fetcher scenarios:
- Mozilla root store
- AWS S3 with IAM role
- Azure Blob with managed identity
- Google Cloud Storage with ADC
- HashiCorp Vault PKI
- Azure Key Vault

Perfect for getting started quickly with cloud-based certificate fetching.

### Comprehensive Cloud Fetcher Examples

**File:** `cloud-fetchers.yaml`

Complete examples demonstrating all available cloud fetchers with various authentication methods:

1. **Mozilla Root Store** - Convenience wrapper for Mozilla CA bundle
2. **AWS S3**
   - IAM role authentication (recommended for AWS environments)
   - Explicit credentials (access key + secret key)
   - Temporary credentials with session tokens
   - S3-compatible storage (MinIO, Ceph, etc.)
3. **Azure Blob Storage**
   - Connection string authentication
   - Account key authentication
   - Managed identity (recommended for Azure environments)
   - SAS token authentication
4. **Google Cloud Storage**
   - Service account with JSON key
   - Application Default Credentials (recommended for GCP environments)
5. **Azure Key Vault**
   - Managed identity (recommended for Azure environments)
   - Service principal with client credentials
   - Certificate version control
6. **HashiCorp Vault PKI**
   - Default issuer reference
   - Named issuer reference
   - Vault Enterprise with namespaces
7. **HashiCorp Vault KV** - For comparison with PKI fetcher

## Usage

### Testing Configurations

To test a fetcher configuration without building a full bundle:

```bash
bundlecraft fetch \
  --source-config-file docs/examples/quick-start-fetchers.yaml \
  --workspace-root .
```

### Dry Run

Preview what would be fetched without actually downloading:

```bash
bundlecraft fetch \
  --source-config-file docs/examples/cloud-fetchers.yaml \
  --dry-run
```

### Integration with Build Process

Copy the example to your config directory and reference it in your bundle config:

```bash
# Copy example
cp docs/examples/quick-start-fetchers.yaml config/sources/my-bundle.yaml

# Edit with your values
vim config/sources/my-bundle.yaml

# Build
bundlecraft build --env prod --bundle my-bundle
```

## Environment Variables

Make sure to set required environment variables before running:

```bash
# For AWS S3 (with explicit credentials)
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# For Azure Blob (with connection string)
export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"

# For GCS (with service account)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# For Vault
export VAULT_TOKEN="your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"

# For Azure Key Vault (with service principal)
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

## Security Best Practices

1. **Always use content verification** (SHA256) for static bundles like Mozilla roots
2. **Use managed identities** or IAM roles when running in cloud environments
3. **Pin TLS certificates** for internal endpoints if certificate rotation is infrequent
4. **Never commit credentials** to version control - use environment variables
5. **Use separate credentials** per environment (dev, staging, prod)
6. **Regularly rotate** authentication tokens and credentials
7. **Monitor fetch operations** for failures in CI/CD pipelines

## Additional Resources

- [Fetcher Documentation](../fetchers.md) - Complete guide to all fetchers
- [Configuration Specification](../CONFIG-SPEC.md) - Full config schema reference
- [Troubleshooting Guide](../troubleshooting.md) - Common issues and solutions

## Contributing Examples

To contribute a new example:

1. Create a clear, well-documented YAML file
2. Include comments explaining each configuration option
3. Add a description to this README
4. Test the example with `--dry-run` before submitting
5. Submit a pull request

Examples should be:
- **Practical** - Based on real-world use cases
- **Well-commented** - Explain non-obvious configuration choices
- **Secure** - Follow security best practices
- **Working** - Tested with actual BundleCraft commands
