# BundleCraft Fetch Layer Documentation

The BundleCraft **Fetch layer** enables secure retrieval of certificates from external systems, allowing you to build trust bundles from remote sources while maintaining full security and auditability.

## Table of Contents

- [Overview](#overview)
- [Core Principles](#core-principles)
- [Supported Fetchers](#supported-fetchers)
- [Configuration](#configuration)
- [Security Features](#security-features)
- [Common Usage Patterns](#common-usage-patterns)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The fetch layer is an optional component that runs during the `bundlecraft build` process. When a source configuration includes a `fetch:` section, BundleCraft will:

1. **Securely retrieve** certificates from remote sources using the configured method
2. **Validate** the retrieved content against verification policies
3. **Stage** the certificates under `cert_sources/staged/<source_name>/fetch/<name>/`
4. **Record provenance** for audit trails and debugging
5. **Clean up** staged content after each build (no persistent caching)

## Core Principles

- **Opt-in remote trust:** Nothing is fetched unless explicitly declared in `fetch:` sections
- **Defense in depth:** HTTPS + CA pinning + TLS fingerprint pinning + optional SHA256 content verification
- **No persistence:** Staging-only approach, cleaned per run; no hidden caches
- **Offline-friendly:** Builds can run offline if inputs are pre-staged or committed
- **Full provenance:** Every staged artifact is recorded and embedded in build manifests

## Supported Fetchers

### 1. URL Fetcher (`type: url`)

Retrieves certificates from HTTPS URLs. Ideal for public certificate bundles like Mozilla's CA collection.

**Use cases:**

- Mozilla CA bundle from curl.se
- Public certificate repositories
- Static certificate files hosted on secure servers

**Security features:**

- HTTPS-only (HTTP rejected)
- Optional SHA256 content verification
- Custom CA certificate validation
- TLS leaf certificate fingerprint pinning

### 2. API Fetcher (`type: api`)

Generic REST API client with support for various enterprise PKI systems.

**Supported providers:**

- **Keyfactor Command** - Enterprise PKI certificate collections
- **Generic** - Custom REST APIs with configurable authentication

**Use cases:**

- Enterprise certificate management systems
- Custom PKI APIs
- Certificate collection endpoints

**Security features:**

- Token-based authentication via environment variables
- Custom CA certificate validation
- TLS fingerprint pinning
- Response content validation

### 3. Vault Fetcher (`type: vault`)

Integrates with HashiCorp Vault for certificate retrieval from KV stores.

**Use cases:**

- Internal root certificates stored in Vault KV
- Certificate collections managed through Vault
- Secrets stored in Vault KV v1 or v2

**Security features:**

- Token-based authentication
- Custom Vault CA certificate validation
- Address validation
- Field-specific PEM extraction

### 4. Vault PKI Fetcher (`type: vault_pki`)

Retrieves issuer certificates from HashiCorp Vault PKI secrets engine.

**Use cases:**

- PKI root CA certificates
- PKI intermediate CA certificates
- Issuer certificates from Vault PKI engine

**Security features:**

- Token-based authentication
- Custom Vault CA certificate validation
- Namespace support (Vault Enterprise)
- Direct PKI issuer endpoint access

### 5. S3 Fetcher (`type: s3`)

Retrieves certificates from AWS S3 or S3-compatible object storage.

**Use cases:**

- Certificates stored in AWS S3 buckets
- S3-compatible storage (MinIO, Ceph, etc.)
- Cross-account S3 access with IAM roles

**Security features:**

- AWS access key authentication or IAM role
- Session token support for temporary credentials
- Custom endpoint URLs for S3-compatible services
- Configurable timeouts and retries

### 6. Azure Blob Storage Fetcher (`type: azure_blob`)

Retrieves certificates from Azure Blob Storage.

**Use cases:**

- Certificates stored in Azure Storage accounts
- Shared Access Signature (SAS) token access
- Managed identity authentication

**Security features:**

- Multiple authentication methods (connection string, account key, SAS token, managed identity)
- Custom endpoint support
- Configurable timeouts and retries

### 7. Google Cloud Storage Fetcher (`type: gcs`)

Retrieves certificates from Google Cloud Storage.

**Use cases:**

- Certificates stored in GCS buckets
- Service account authentication
- Application Default Credentials (ADC)

**Security features:**

- Service account JSON key authentication
- Application Default Credentials support
- Custom CA certificate validation
- Configurable timeouts and retries

### 8. Azure Key Vault Fetcher (`type: azure_keyvault`)

Retrieves certificates from Azure Key Vault.

**Use cases:**

- Certificates managed in Azure Key Vault
- Versioned certificate retrieval
- Service principal or managed identity access

**Security features:**

- Service principal authentication
- Managed identity support
- Certificate version control
- Automatic DER to PEM conversion

### 9. Mozilla Root Store Fetcher (`type: mozilla`)

Convenience wrapper to fetch the Mozilla root certificate store.

**Use cases:**

- Mozilla CA bundle for browser-trusted roots
- Quick setup for common root certificates
- Regular updates from curl.se

**Security features:**

- HTTPS-only access
- Optional SHA256 content verification
- All URL fetcher security features

## Configuration

### Basic Fetch Configuration

Add a `fetch:` section to your source configuration file (`config/sources/*.yaml`):

```yaml
apiVersion: bundlecraft.io/v1alpha1
kind: SourceConfig
source_name: example
description: Example remote certificates

fetch:
  - name: remote_certs
    type: url  # or 'api', 'vault'
    url: https://example.com/certificates.pem
    verify:
      sha256: "abc123..."  # optional content verification
```

### URL Fetcher Configuration

```yaml
fetch:
  - name: mozilla_bundle
    type: url
    url: https://curl.se/ca/cacert.pem
    verify:
      # Content integrity verification
      sha256: "expected-sha256-hash-of-content"
      
      # TLS validation options
      ca_file: config/certs/trusted-ca.pem          # optional custom CA
      tls_fingerprint_sha256: "leaf-cert-fp"        # optional leaf cert pinning
```

### API Fetcher Configuration

```yaml
fetch:
  - name: keyfactor_certs
    type: api
    provider: keyfactor  # or 'generic'
    endpoint: https://pki.example.com/api/v1/collections/trusted
    token_ref: KEYFACTOR_TOKEN  # environment variable name
    verify:
      ca_file: config/certs/pki-ca.pem
      tls_fingerprint_sha256: "server-leaf-fingerprint"
```

### Vault Fetcher Configuration

```yaml
fetch:
  - name: vault_roots
    type: vault
    mount_point: secret         # KV mount point
    path: pki/root_certificates # path within mount
    pem_field: certificate_pem  # field containing PEM data
    addr: https://vault.example.com:8200  # optional, uses VAULT_ADDR env var
    token_ref: VAULT_TOKEN      # environment variable name
    verify:
      ca_file: config/certs/vault-ca.pem
```

### Vault PKI Fetcher Configuration

```yaml
fetch:
  - name: pki_issuer
    type: vault_pki
    mount_point: pki            # PKI mount point
    issuer_ref: default         # issuer reference (default, issuer name, or ID)
    addr: https://vault.example.com:8200  # optional, uses VAULT_ADDR env var
    token_ref: VAULT_TOKEN      # environment variable name
    namespace: admin/prod       # optional, for Vault Enterprise
    verify:
      ca_file: config/certs/vault-ca.pem
    timeout: 30                 # optional, default 30s
    retries: 3                  # optional, default 3
```

### S3 Fetcher Configuration

```yaml
fetch:
  - name: s3_certs
    type: s3
    bucket: my-certificates-bucket
    key: prod/ca-bundle.pem
    region: us-east-1           # optional, defaults to AWS_DEFAULT_REGION or us-east-1
    access_key_id_ref: AWS_ACCESS_KEY_ID        # optional, env var for access key
    secret_access_key_ref: AWS_SECRET_ACCESS_KEY # optional, env var for secret key
    session_token_ref: AWS_SESSION_TOKEN         # optional, for temporary credentials
    endpoint_url: https://s3.example.com         # optional, for S3-compatible services
    verify:
      ca_file: config/certs/s3-ca.pem           # optional
    timeout: 60                 # optional, default 30s
    retries: 5                  # optional, default 3
```

### Azure Blob Storage Fetcher Configuration

```yaml
fetch:
  - name: azure_blob_certs
    type: azure_blob
    account_name: mystorageaccount
    container: certificates
    blob_name: prod/ca-bundle.pem
    connection_string_ref: AZURE_STORAGE_CONNECTION_STRING  # optional
    account_key_ref: AZURE_STORAGE_KEY                      # optional
    sas_token_ref: AZURE_STORAGE_SAS_TOKEN                  # optional
    endpoint_url: https://mystorageaccount.blob.core.windows.net  # optional
    verify:
      ca_file: config/certs/azure-ca.pem
    timeout: 60
    retries: 3
```

### Google Cloud Storage Fetcher Configuration

```yaml
fetch:
  - name: gcs_certs
    type: gcs
    bucket: my-certificates-bucket
    blob_name: prod/ca-bundle.pem
    project_id: my-gcp-project  # optional, inferred from credentials
    credentials_file_ref: GOOGLE_APPLICATION_CREDENTIALS  # optional, env var
    verify:
      ca_file: config/certs/google-ca.pem
    timeout: 60
    retries: 3
```

### Azure Key Vault Fetcher Configuration

```yaml
fetch:
  - name: akv_cert
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net
    certificate_name: production-ca
    version: abc123def456        # optional, uses latest if not specified
    client_id_ref: AZURE_CLIENT_ID          # optional, for service principal
    client_secret_ref: AZURE_CLIENT_SECRET  # optional, for service principal
    tenant_id_ref: AZURE_TENANT_ID          # optional, for service principal
    verify:
      ca_file: config/certs/azure-ca.pem
    timeout: 30
    retries: 3
```

### Mozilla Root Store Fetcher Configuration

```yaml
fetch:
  - name: mozilla_roots
    type: mozilla
    verify:
      sha256: "expected-sha256-hash-of-current-mozilla-bundle"
    timeout: 60
    retries: 3
```

## Security Features

### HTTPS Enforcement

All fetchers require HTTPS URLs. HTTP URLs are rejected for security:

```yaml
fetch:
  - name: secure_only
    type: url
    url: https://example.com/certs.pem  # ✅ Allowed
    # url: http://example.com/certs.pem   # ❌ Rejected
```

### Content Integrity Verification

Verify retrieved content matches expected SHA256 hash:

```yaml
verify:
  sha256: "expected-sha256-hash-of-the-certificate-content"
```

### TLS Certificate Validation

#### Custom CA Certificate

Validate server certificates against a custom CA:

```yaml
verify:
  ca_file: config/certs/custom-ca.pem
```

#### TLS Fingerprint Pinning

Pin to a specific server certificate (leaf certificate):

```yaml
verify:
  tls_fingerprint_sha256: "sha256-fingerprint-of-server-leaf-certificate"
```

### Token-Based Authentication

All API and Vault fetchers use environment variables for authentication:

```yaml
# Reference environment variable containing the token
token_ref: MY_API_TOKEN
```

## Common Usage Patterns

### Mozilla CA Bundle (Public Roots)

```yaml
fetch:
  - name: mozilla_roots
    type: mozilla  # Convenience wrapper for Mozilla root store
    verify:
      sha256: "current-mozilla-bundle-sha256-hash"
```

Or using the URL fetcher directly:

```yaml
fetch:
  - name: mozilla_roots
    type: url
    url: https://curl.se/ca/cacert.pem
    verify:
      sha256: "current-mozilla-bundle-sha256-hash"
```

### Keyfactor Enterprise PKI

```yaml
fetch:
  - name: enterprise_cas
    type: api
    provider: keyfactor
    endpoint: https://pki.company.com/api/v1/collections/production-roots
    token_ref: KEYFACTOR_API_TOKEN
    verify:
      ca_file: config/certs/company-pki-ca.pem
      tls_fingerprint_sha256: "keyfactor-server-fingerprint"
```

### HashiCorp Vault KV Integration

```yaml
fetch:
  - name: internal_roots
    type: vault
    mount_point: secret
    path: pki/internal/root-certificates
    pem_field: pem_data
    addr: https://vault.internal.company.com:8200
    token_ref: VAULT_TOKEN
    verify:
      ca_file: config/certs/vault-ca.pem
```

### HashiCorp Vault PKI Issuer

```yaml
fetch:
  - name: pki_root_ca
    type: vault_pki
    mount_point: pki_root
    issuer_ref: root-2024
    addr: https://vault.internal.company.com:8200
    token_ref: VAULT_TOKEN
```

### AWS S3 with IAM Role

```yaml
fetch:
  - name: s3_bundle
    type: s3
    bucket: company-certificates
    key: prod/ca-bundle.pem
    region: us-east-1
    # Uses IAM role attached to EC2/ECS/Lambda
```

### Azure Blob with Managed Identity

```yaml
fetch:
  - name: azure_bundle
    type: azure_blob
    account_name: companystore
    container: certificates
    blob_name: prod/ca-bundle.pem
    # Uses managed identity when no credentials provided
```

### Google Cloud Storage with Service Account

```yaml
fetch:
  - name: gcs_bundle
    type: gcs
    bucket: company-certificates
    blob_name: prod/ca-bundle.pem
    project_id: my-gcp-project
    credentials_file_ref: GOOGLE_APPLICATION_CREDENTIALS
```

### Azure Key Vault Certificate

```yaml
fetch:
  - name: akv_root_ca
    type: azure_keyvault
    vault_url: https://company-keyvault.vault.azure.net
    certificate_name: root-ca-2024
    # Uses managed identity or service principal
```

### Generic REST API

```yaml
fetch:
  - name: custom_api
    type: api
    provider: generic
    endpoint: https://certificates.example.com/api/v2/bundles/production
    token_ref: CUSTOM_API_TOKEN
    verify:
      ca_file: config/certs/api-ca.pem
```

## Environment Variables

### Required for Authentication

| Fetcher Type | Environment Variable | Purpose |
|--------------|---------------------|---------|
| API (Keyfactor) | `KEYFACTOR_TOKEN` | API authentication token |
| API (Generic) | `CUSTOM_API_TOKEN` | Custom API token (configurable name) |
| Vault (KV) | `VAULT_TOKEN` | Vault authentication token |
| Vault (KV) | `VAULT_ADDR` | Vault server address (optional, can be in config) |
| Vault PKI | `VAULT_TOKEN` | Vault authentication token |
| Vault PKI | `VAULT_ADDR` | Vault server address (optional, can be in config) |
| S3 | `AWS_ACCESS_KEY_ID` | AWS access key ID (optional with IAM role) |
| S3 | `AWS_SECRET_ACCESS_KEY` | AWS secret access key (optional with IAM role) |
| S3 | `AWS_SESSION_TOKEN` | AWS session token (for temporary credentials) |
| S3 | `AWS_DEFAULT_REGION` | AWS region (optional, defaults to us-east-1) |
| Azure Blob | `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection string |
| Azure Blob | `AZURE_STORAGE_KEY` | Azure Storage account key |
| Azure Blob | `AZURE_STORAGE_SAS_TOKEN` | Azure Storage SAS token |
| GCS | `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON file |
| Azure Key Vault | `AZURE_CLIENT_ID` | Service principal client ID |
| Azure Key Vault | `AZURE_CLIENT_SECRET` | Service principal client secret |
| Azure Key Vault | `AZURE_TENANT_ID` | Azure tenant ID |

### Setting Environment Variables

```bash
# For API fetchers
export KEYFACTOR_TOKEN="your-keyfactor-api-token"
export CUSTOM_API_TOKEN="your-custom-token"

# For Vault fetchers (KV and PKI)
export VAULT_TOKEN="hvs.your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"

# For AWS S3
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_SESSION_TOKEN="temporary-token"  # For temporary credentials
export AWS_DEFAULT_REGION="us-east-1"

# For Azure Blob Storage (choose one authentication method)
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
# OR
export AZURE_STORAGE_KEY="your-storage-account-key"
# OR
export AZURE_STORAGE_SAS_TOKEN="your-sas-token"

# For Google Cloud Storage
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# For Azure Key Vault (for service principal authentication)
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

## Troubleshooting

### Common Issues

#### "Insecure HTTP rejected" Error

**Problem:** Trying to use HTTP URLs

```yaml
fetch:
  - name: insecure
    type: url
    url: http://example.com/certs.pem  # ❌ HTTP not allowed
```

**Solution:** Use HTTPS only

```yaml
fetch:
  - name: secure
    type: url
    url: https://example.com/certs.pem  # ✅ HTTPS required
```

#### "SHA256 mismatch" Error

**Problem:** Content has changed or incorrect hash specified

**Solution:**

1. Verify the content hasn't changed unexpectedly
2. Update the expected SHA256 hash:

```bash
# Get current SHA256 of remote content
curl -s https://example.com/certs.pem | sha256sum
```

#### "TLS fingerprint mismatch" Error

**Problem:** Server certificate has been rotated

**Solution:** Update the fingerprint after verifying the certificate change is legitimate. You can use Python's cryptography module or other tools to extract the certificate fingerprint.

#### "Token authentication failed" Error

**Problem:** Missing or invalid authentication token

**Solution:** Verify environment variable is set correctly:
```bash
# Check if token is set
echo $KEYFACTOR_TOKEN

# Set token if missing
export KEYFACTOR_TOKEN="your-actual-token"
```

#### "Vault: hvac not installed" Error

**Problem:** Missing Vault dependencies when using Python package installation

**Solution:** Install with fetcher dependencies:
```bash
pip install bundlecraft[fetchers]
```

Note: When using containers, Vault support is included by default.

### Debugging Commands

```bash
# Verbose output for fetch operations
bundlecraft fetch --source-config-file config/sources/example.yaml --verbose

# JSON output for programmatic analysis
bundlecraft fetch --source-config-file config/sources/example.yaml --json

# Test fetch without building
bundlecraft fetch --env prod --bundle example --verbose
```

## Best Practices

### Security Best Practices

1. **Always use content verification for static bundles:**
   ```yaml
   verify:
     sha256: "known-good-hash-of-mozilla-bundle"
   ```

2. **Use CA pinning for enterprise systems:**
   ```yaml
   verify:
     ca_file: config/certs/enterprise-ca.pem
   ```

3. **Consider TLS fingerprint pinning during certificate rotation windows:**
   ```yaml
   verify:
     tls_fingerprint_sha256: "current-server-cert-fingerprint"
   ```

4. **Never commit tokens to version control:**
   ```bash
   # ✅ Use environment variables
   export VAULT_TOKEN="hvs.token"
   
   # ❌ Never in YAML files
   # token: "hvs.token"  # DON'T DO THIS
   ```

### Operational Best Practices

1. **Use staging environments for testing fetch configurations**
2. **Monitor certificate expiry in remote sources**
3. **Set up alerts for fetch failures in CI/CD pipelines**
4. **Document your remote certificate sources and approval processes**
5. **Regularly review and rotate authentication tokens**

### Configuration Management

1. **Keep fetch configurations in version control**
2. **Use separate tokens per environment (dev/staging/prod)**
3. **Document expected certificate sources and their purposes**
4. **Test fetch configurations in non-production environments first**

### Performance Considerations

1. **Fetch operations add network latency to builds**
2. **Consider pre-staging certificates for air-gapped environments**
3. **Use `--skip-fetch` for offline builds:**
   ```bash
   bundlecraft build --env prod --skip-fetch
   ```

4. **Monitor fetch operation duration in CI/CD pipelines**

---

For additional help, see:

- [BundleCraft Troubleshooting Guide](troubleshooting.md)
- [Configuration Specification](CONFIG-SPEC.md)
- [GitHub Discussions](https://github.com/bundlecraft-io/bundlecraft/discussions)