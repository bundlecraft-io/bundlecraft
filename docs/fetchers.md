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

Integrates with HashiCorp Vault for certificate retrieval from KV stores or PKI secrets engines.

**Use cases:**

- Internal root certificates stored in Vault
- PKI intermediate certificates
- Certificate collections managed through Vault

**Security features:**

- Token-based authentication
- Custom Vault CA certificate validation
- Address validation
- Field-specific PEM extraction

### 4. Azure Blob Fetcher (`type: azure_blob`)

Retrieves certificates from Azure Blob Storage, supporting multiple authentication methods.

**Use cases:**

- Certificates stored in Azure Blob Storage
- Enterprise certificate repositories in Azure
- Cloud-native certificate distribution
- Multi-region certificate management

**Security features:**

- Multiple authentication methods (connection string, account key, SAS token, managed identity)
- HTTPS-only access
- Azure RBAC integration
- Content integrity verification

**Authentication methods (in priority order):**

1. **Connection String** - Full connection string including account credentials
2. **Account Key** - Storage account name with account key
3. **SAS Token** - Storage account name with shared access signature
4. **Managed Identity** - Azure Managed Identity for authentication
5. **Default Credential** - Azure SDK default credential chain (environment, managed identity, Azure CLI)

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

### Azure Blob Fetcher Configuration

```yaml
# Option 1: Using Connection String
fetch:
  - name: azure_certs
    type: azure_blob
    container: certificates           # Azure Blob container name
    blob_name: production/roots.pem   # Blob path within container
    connection_string_ref: AZURE_STORAGE_CONNECTION_STRING  # env var
    verify:
      sha256: "expected-content-hash"  # optional content verification

# Option 2: Using Account Key
fetch:
  - name: azure_certs
    type: azure_blob
    container: certificates
    blob_name: intermediate-ca.pem
    account_name: mystorageaccount    # Storage account name
    account_key_ref: AZURE_ACCOUNT_KEY  # env var with account key

# Option 3: Using SAS Token
fetch:
  - name: azure_certs
    type: azure_blob
    container: certificates
    blob_name: partner-ca.pem
    account_name: mystorageaccount
    sas_token_ref: AZURE_SAS_TOKEN    # env var with SAS token

# Option 4: Using Managed Identity (Azure VMs, AKS, etc.)
fetch:
  - name: azure_certs
    type: azure_blob
    container: certificates
    blob_name: internal-ca.pem
    account_name: mystorageaccount
    use_managed_identity: true        # Use Azure Managed Identity

# Option 5: Using Default Credential Chain (recommended for Azure environments)
fetch:
  - name: azure_certs
    type: azure_blob
    container: certificates
    blob_name: trusted-roots.pem
    account_name: mystorageaccount
    # No explicit auth - uses DefaultAzureCredential
    # Tries: environment vars, managed identity, Azure CLI, etc.
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

### HashiCorp Vault Integration

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

### Azure Blob Storage

```yaml
# Production certificates from Azure Blob
fetch:
  - name: azure_prod_roots
    type: azure_blob
    container: production-certificates
    blob_name: trusted-roots/ca-bundle.pem
    account_name: prodstorageaccount
    sas_token_ref: AZURE_PROD_SAS_TOKEN
    verify:
      sha256: "production-bundle-sha256-hash"

# Using managed identity in Azure Kubernetes Service (AKS)
fetch:
  - name: azure_internal_ca
    type: azure_blob
    container: internal-pki
    blob_name: ca-certificates/root-ca.pem
    account_name: internalstorage
    use_managed_identity: true
    timeout: 45
    retries: 5
```

## Environment Variables

### Required for Authentication

| Fetcher Type | Environment Variable | Purpose |
|--------------|---------------------|---------|
| API (Keyfactor) | `KEYFACTOR_TOKEN` | API authentication token |
| API (Generic) | `CUSTOM_API_TOKEN` | Custom API token (configurable name) |
| Vault | `VAULT_TOKEN` | Vault authentication token |
| Vault | `VAULT_ADDR` | Vault server address (optional, can be in config) |
| Azure Blob | `AZURE_STORAGE_CONNECTION_STRING` | Full Azure Storage connection string |
| Azure Blob | `AZURE_ACCOUNT_KEY` | Azure Storage account key |
| Azure Blob | `AZURE_SAS_TOKEN` | Azure Storage SAS token |

**Note:** Azure Blob also supports managed identity and DefaultAzureCredential, which don't require environment variables when running in Azure environments (VMs, AKS, Functions, etc.).

### Setting Environment Variables

```bash
# For API fetchers
export KEYFACTOR_TOKEN="your-keyfactor-api-token"

# For Vault fetchers
export VAULT_TOKEN="hvs.your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"

# For custom APIs
export CUSTOM_API_TOKEN="your-custom-token"

# For Azure Blob Storage
# Option 1: Connection String (includes account name and key)
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"

# Option 2: Account Key (requires account_name in config)
export AZURE_ACCOUNT_KEY="your-storage-account-key"

# Option 3: SAS Token (requires account_name in config)
export AZURE_SAS_TOKEN="sv=2021-06-08&ss=bfqt&srt=sco&sp=rwdlacupitfx&se=2024-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=..."
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

#### "Azure Blob not found" Error

**Problem:** Container or blob doesn't exist, or incorrect names specified

**Solution:** Verify the container and blob names:
```bash
# Using Azure CLI to list containers
az storage container list --account-name mystorageaccount

# List blobs in a container
az storage blob list --container-name certificates --account-name mystorageaccount
```

#### "Azure authentication failed" Error

**Problem:** Invalid credentials or insufficient permissions

**Solution:** 
1. Verify credentials are correct and not expired
2. Check that the storage account exists and is accessible
3. Ensure proper RBAC roles are assigned (e.g., "Storage Blob Data Reader")
4. For managed identity, verify the identity is assigned to the resource and has proper permissions

```bash
# Test connection using Azure CLI
az storage blob download --account-name mystorageaccount \
  --container-name certificates --name test.pem --file /tmp/test.pem

# Check managed identity assignment (for Azure VMs)
az vm identity show --resource-group myResourceGroup --name myVM
```

#### "azure-storage-blob not installed" Error

**Problem:** Missing Azure SDK when using Python package installation

**Solution:** Install with fetcher dependencies:
```bash
pip install bundlecraft[fetchers]
```

Note: When using containers, Azure Blob support is included by default.

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

### Azure Blob-Specific Best Practices

1. **Use SAS tokens with minimal permissions and time-bound access:**
   - Generate SAS tokens with read-only permissions
   - Set expiration dates appropriate to your rotation schedule
   - Use account or service-level SAS, not container-level

2. **Prefer managed identity in Azure environments:**
   ```yaml
   # Best practice for Azure VMs, AKS, Azure Functions
   fetch:
     - name: azure_certs
       type: azure_blob
       container: certificates
       blob_name: ca-bundle.pem
       account_name: mystorageaccount
       use_managed_identity: true
   ```

3. **Implement proper RBAC:**
   - Assign "Storage Blob Data Reader" role for read-only access
   - Avoid using account keys when possible
   - Use Azure AD authentication (managed identity or service principal)

4. **Enable Azure Storage logging and monitoring:**
   - Track certificate access patterns
   - Monitor for authentication failures
   - Set up alerts for unusual access

5. **Use private endpoints for enhanced security:**
   - Restrict storage account access to specific VNets
   - Disable public access when running in Azure

6. **Organize blobs with clear naming conventions:**
   ```
   certificates/
     production/
       roots/ca-bundle.pem
       intermediate/issuing-ca.pem
     staging/
       roots/ca-bundle.pem
   ```

7. **Enable blob versioning for rollback capability:**
   - Track certificate updates over time
   - Quickly revert to previous versions if needed

### Azure Access and Authentication Policies

**Required Azure Permissions:**

For connection string or account key auth:
- Storage account key access (usually admin-level)

For SAS token:
- Read permission on blobs (`r`)
- List permission on container (`l`) - optional but recommended

For managed identity or DefaultAzureCredential:
- Azure role assignment: `Storage Blob Data Reader` (or `Storage Blob Data Contributor` if write access needed)
- Role assignment can be at storage account, container, or blob level

**Setting up Managed Identity:**

```bash
# 1. Enable managed identity on your resource (VM, AKS, Function, etc.)
az vm identity assign --resource-group myResourceGroup --name myVM

# 2. Get the principal ID
PRINCIPAL_ID=$(az vm identity show --resource-group myResourceGroup --name myVM --query principalId -o tsv)

# 3. Assign Storage Blob Data Reader role
az role assignment create \
  --role "Storage Blob Data Reader" \
  --assignee $PRINCIPAL_ID \
  --scope /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Storage/storageAccounts/{storage-account}
```

**Setting up SAS Token:**

```bash
# Generate a read-only SAS token with 90-day expiration
az storage container generate-sas \
  --account-name mystorageaccount \
  --name certificates \
  --permissions rl \
  --expiry $(date -u -d "90 days" '+%Y-%m-%dT%H:%MZ') \
  --https-only \
  --output tsv
```

**Azure Blob Storage Documentation:**
- [Authentication overview](https://learn.microsoft.com/en-us/azure/storage/common/storage-auth)
- [Managed identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)
- [SAS tokens](https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview)
- [RBAC roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#storage-blob-data-reader)

---

For additional help, see:

- [BundleCraft Troubleshooting Guide](troubleshooting.md)
- [Configuration Specification](CONFIG-SPEC.md)
- [GitHub Discussions](https://github.com/bundlecraft-io/bundlecraft/discussions)