# BundleCraft Configuration Examples

This directory contains example configurations for various BundleCraft features and fetcher types.

## Available Examples

### Vault PKI Issuer Example

**File:** `vault-pki-issuer-example.yaml`

Demonstrates how to fetch certificates from HashiCorp Vault's PKI secrets engine using the issuer endpoint. This example shows:

- Basic PKI issuer fetch with default settings
- Custom mount points and issuer references
- Vault Enterprise namespace support
- Custom retry/timeout configuration
- Fetching multiple issuers from the same mount
- Optional authentication configuration

**Use this example when:**
- You manage PKI infrastructure with HashiCorp Vault
- You need to fetch root or intermediate CA certificates from Vault PKI
- You want to automate certificate trust bundle management with Vault
- You're working with Vault Enterprise namespaces

**Prerequisites:**
- HashiCorp Vault instance with PKI secrets engine enabled
- BundleCraft installed with fetchers support: `pip install 'bundlecraft[fetchers]'`
- VAULT_ADDR environment variable set (or specify in config)
- Optional: VAULT_TOKEN for authenticated access

**Usage:**
```bash
# Set Vault address
export VAULT_ADDR="https://vault.example.com:8200"

# Optional: Set token if authentication is required
export VAULT_TOKEN="hvs.your-vault-token"

# Fetch using the example configuration
bundlecraft fetch --source-config-file docs/examples/vault-pki-issuer-example.yaml
```

**References:**
- [Vault PKI API Documentation](https://developer.hashicorp.com/vault/api-docs/secret/pki#read-issuer-certificate)
- [BundleCraft Fetchers Documentation](../fetchers.md)
- [Configuration Specification](../CONFIG-SPEC.md)

## Contributing Examples

If you have a useful configuration example that demonstrates a BundleCraft feature or use case, please consider contributing it:

1. Create a well-documented YAML file with inline comments
2. Add an entry to this README explaining the example
3. Submit a pull request

Examples should be:
- Self-contained and runnable (with minimal setup)
- Well-commented to explain each configuration option
- Representative of real-world use cases
- Following BundleCraft best practices
