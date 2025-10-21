# BundleCraft Fetchers Guide

This document provides comprehensive documentation for all available fetchers in BundleCraft, including configuration examples and provider-specific details.

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [Cloud Storage Providers](#cloud-storage-providers)
  - [AWS S3](#aws-s3)
  - [Azure Blob Storage](#azure-blob-storage)
  - [Google Cloud Storage (GCS)](#google-cloud-storage-gcs)
- [Artifact Repositories](#artifact-repositories)
  - [JFrog Artifactory](#jfrog-artifactory)
  - [GitHub Releases](#github-releases)
- [Key Management Systems](#key-management-systems)
  - [Azure Key Vault](#azure-key-vault)
  - [HashiCorp Vault](#hashicorp-vault)
- [Public Root Certificate Programs](#public-root-certificate-programs)
  - [Mozilla Root Program](#mozilla-root-program)
  - [Microsoft Root Program](#microsoft-root-program)
  - [Apple Root Program](#apple-root-program)
- [Generic Fetchers](#generic-fetchers)
  - [URL (HTTPS/File)](#url-httpsfile)
  - [API](#api)

---

## Overview

BundleCraft supports multiple fetchers to retrieve certificates from various sources. Each fetcher is designed to work securely with specific providers and supports common security features like SHA256 content pinning and TLS verification.

### Installation

Extended fetchers require additional dependencies. Install them using:

```bash
# For cloud storage providers (S3, Azure Blob, GCS, Azure Key Vault)
pip install 'bundlecraft[cloud]'

# For HashiCorp Vault
pip install 'bundlecraft[fetchers]'

# For all extended fetchers
pip install 'bundlecraft[cloud,fetchers]'
```

---

## Common Options

All fetchers support the following common verification options under the `verify` key:

- **`sha256`**: Expected SHA256 hash of the fetched content (hex string). Highly recommended for static sources.
- **`ca_file`**: Path to a custom CA certificate file for TLS verification (relative to workspace root).
- **`tls_fingerprint_sha256`**: Expected SHA256 fingerprint of the server's TLS certificate for certificate pinning.

### Example

```yaml
fetch:
  - name: my-cert
    type: url
    url: https://example.com/cert.pem
    verify:
      sha256: abcdef1234567890...  # Content hash
      ca_file: config/certs/ca.pem  # Custom CA
      tls_fingerprint_sha256: 1234abcd...  # TLS cert pinning
```

---

## Cloud Storage Providers

### AWS S3

Fetch certificates from Amazon S3 or S3-compatible storage.

**Type:** `s3`

**Required Fields:**
- `bucket`: S3 bucket name
- `key`: Object key/path within the bucket

**Optional Fields:**
- `region`: AWS region (defaults to `AWS_DEFAULT_REGION` or `us-east-1`)
- `endpoint_url`: Custom S3 endpoint for S3-compatible storage (e.g., MinIO)
- `access_key_ref`: Environment variable name for AWS access key (default: `AWS_ACCESS_KEY_ID`)
- `secret_key_ref`: Environment variable name for AWS secret key (default: `AWS_SECRET_ACCESS_KEY`)

**Environment Variables:**
- `AWS_ACCESS_KEY_ID`: AWS access key (optional, uses IAM role if not set)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional)
- `AWS_DEFAULT_REGION`: Default AWS region

**Example:**

```yaml
fetch:
  - name: corporate-root-ca
    type: s3
    bucket: my-pki-bucket
    key: certs/rootCA.pem
    region: us-west-2
    verify:
      sha256: abc123...
```

**Example with MinIO (S3-compatible):**

```yaml
fetch:
  - name: minio-cert
    type: s3
    bucket: certificates
    key: internal/root.pem
    endpoint_url: https://minio.company.local:9000
    access_key_ref: MINIO_ACCESS_KEY
    secret_key_ref: MINIO_SECRET_KEY
```

**References:**
- [AWS S3 Documentation](https://aws.amazon.com/s3/)
- [boto3 S3 Client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)

---

### Azure Blob Storage

Fetch certificates from Azure Blob Storage.

**Type:** `azure_blob`

**Required Fields:**
- `container`: Blob container name
- `blob_name`: Blob name/path within the container

**Optional Fields:**
- `account_name`: Storage account name
- `account_url`: Full storage account URL (e.g., `https://myaccount.blob.core.windows.net`)
- `connection_string_ref`: Environment variable for connection string (default: `AZURE_STORAGE_CONNECTION_STRING`)
- `sas_token_ref`: Environment variable for SAS token (default: `AZURE_STORAGE_SAS_TOKEN`)

**Authentication Methods (in order of precedence):**
1. Connection string (via `connection_string_ref`)
2. SAS token (via `sas_token_ref`) with `account_url` or `account_name`
3. Default Azure credential (Managed Identity, Azure CLI, etc.)

**Environment Variables:**
- `AZURE_STORAGE_CONNECTION_STRING`: Azure Storage connection string
- `AZURE_STORAGE_SAS_TOKEN`: SAS token for access

**Example with Connection String:**

```yaml
fetch:
  - name: azure-root-ca
    type: azure_blob
    container: pki-certs
    blob_name: certificates/rootCA.pem
    connection_string_ref: AZURE_STORAGE_CONNECTION_STRING
```

**Example with Managed Identity:**

```yaml
fetch:
  - name: azure-root-ca
    type: azure_blob
    container: pki-certs
    blob_name: certificates/rootCA.pem
    account_url: https://myaccount.blob.core.windows.net
```

**References:**
- [Azure Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Azure Storage Python SDK](https://docs.microsoft.com/en-us/python/api/overview/azure/storage-blob-readme)

---

### Google Cloud Storage (GCS)

Fetch certificates from Google Cloud Storage.

**Type:** `gcs`

**Required Fields:**
- `bucket`: GCS bucket name
- `blob_name`: Blob name/path within the bucket

**Optional Fields:**
- `project`: GCP project ID (uses default if not specified)
- `credentials_ref`: Environment variable for service account JSON key path (default: `GOOGLE_APPLICATION_CREDENTIALS`)

**Authentication Methods:**
1. Service account JSON key file (via `credentials_ref`)
2. Default application credentials (gcloud CLI, Compute Engine, etc.)

**Environment Variables:**
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON key file

**Example with Service Account:**

```yaml
fetch:
  - name: gcs-root-ca
    type: gcs
    bucket: my-pki-bucket
    blob_name: certs/rootCA.pem
    project: my-gcp-project
    credentials_ref: GOOGLE_APPLICATION_CREDENTIALS
```

**Example with Default Credentials:**

```yaml
fetch:
  - name: gcs-root-ca
    type: gcs
    bucket: my-pki-bucket
    blob_name: certs/rootCA.pem
```

**References:**
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Google Cloud Storage Python Client](https://cloud.google.com/python/docs/reference/storage/latest)

---

## Artifact Repositories

### JFrog Artifactory

Fetch certificates from JFrog Artifactory Maven or generic repositories.

**Type:** `artifactory`

**Required Fields:**
- `url`: Full Artifactory URL to the artifact OR base Artifactory URL (requires `repository` and `path`)

**Optional Fields:**
- `repository`: Repository name (e.g., `libs-release-local`)
- `path`: Artifact path within repository (e.g., `com/example/certs/rootCA.pem`)
- `username_ref`: Environment variable for username (default: `ARTIFACTORY_USERNAME`)
- `password_ref`: Environment variable for password (default: `ARTIFACTORY_PASSWORD`)
- `token_ref`: Environment variable for API token (default: `ARTIFACTORY_TOKEN`, preferred)

**Authentication Methods (in order of precedence):**
1. API token (via `token_ref`) - recommended
2. Username/password (via `username_ref` and `password_ref`)

**Environment Variables:**
- `ARTIFACTORY_TOKEN`: JFrog Artifactory API token
- `ARTIFACTORY_USERNAME`: Artifactory username (if not using token)
- `ARTIFACTORY_PASSWORD`: Artifactory password (if not using token)

**Example with Full URL:**

```yaml
fetch:
  - name: artifactory-cert
    type: artifactory
    url: https://artifactory.company.com/artifactory/libs-release-local/certs/rootCA.pem
    token_ref: ARTIFACTORY_TOKEN
    verify:
      sha256: abc123...
```

**Example with Repository and Path:**

```yaml
fetch:
  - name: artifactory-cert
    type: artifactory
    url: https://artifactory.company.com/artifactory
    repository: libs-release-local
    path: com/example/certs/rootCA.pem
    token_ref: ARTIFACTORY_TOKEN
```

**References:**
- [JFrog Artifactory Documentation](https://jfrog.com/artifactory/)
- [Artifactory REST API](https://jfrog.com/help/r/jfrog-rest-apis/artifactory-rest-apis)

---

### GitHub Releases

Fetch certificates from GitHub Releases assets.

**Type:** `github_release`

**Required Fields:**
- `owner`: GitHub repository owner or organization (e.g., `curl`)
- `repo`: GitHub repository name (e.g., `curl`)
- `asset_name`: Name of the release asset to download (e.g., `cacert.pem`)

**Optional Fields:**
- `tag`: Release tag (e.g., `v1.0.0`). If not provided, fetches from latest release
- `token_ref`: Environment variable for GitHub token (default: `GITHUB_TOKEN`, optional for public repos)

**Environment Variables:**
- `GITHUB_TOKEN`: GitHub personal access token (required for private repos, optional for public)

**Example with Latest Release:**

```yaml
fetch:
  - name: mozilla-roots-via-github
    type: github_release
    owner: curl
    repo: curl
    asset_name: cacert.pem
    verify:
      sha256: abc123...
```

**Example with Specific Tag:**

```yaml
fetch:
  - name: company-certs
    type: github_release
    owner: mycompany
    repo: pki-certificates
    asset_name: rootCA.pem
    tag: v2023.12.01
    token_ref: GITHUB_TOKEN
```

**References:**
- [GitHub Releases Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [GitHub REST API - Releases](https://docs.github.com/en/rest/releases/releases)

---

## Key Management Systems

### Azure Key Vault

Fetch certificates from Azure Key Vault.

**Type:** `azure_keyvault`

**Required Fields:**
- `vault_url`: Key Vault URL (e.g., `https://myvault.vault.azure.net/`)
- `certificate_name`: Name of the certificate in Key Vault

**Optional Fields:**
- `version`: Certificate version (defaults to latest version)
- `tenant_id_ref`: Environment variable for Azure tenant ID (for service principal auth)
- `client_id_ref`: Environment variable for Azure client ID (for service principal auth)
- `client_secret_ref`: Environment variable for Azure client secret (for service principal auth)

**Authentication Methods (in order of precedence):**
1. Service principal (via `tenant_id_ref`, `client_id_ref`, `client_secret_ref`)
2. Default Azure credential (Managed Identity, Azure CLI, etc.)

**Environment Variables:**
- `AZURE_TENANT_ID`: Azure AD tenant ID
- `AZURE_CLIENT_ID`: Azure AD client/application ID
- `AZURE_CLIENT_SECRET`: Azure AD client secret

**Example with Service Principal:**

```yaml
fetch:
  - name: keyvault-cert
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net/
    certificate_name: my-root-ca
    tenant_id_ref: AZURE_TENANT_ID
    client_id_ref: AZURE_CLIENT_ID
    client_secret_ref: AZURE_CLIENT_SECRET
```

**Example with Managed Identity:**

```yaml
fetch:
  - name: keyvault-cert
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net/
    certificate_name: my-root-ca
```

**Example with Specific Version:**

```yaml
fetch:
  - name: keyvault-cert
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net/
    certificate_name: my-root-ca
    version: a1b2c3d4e5f6
```

**References:**
- [Azure Key Vault Documentation](https://docs.microsoft.com/en-us/azure/key-vault/)
- [Azure Key Vault Python SDK](https://docs.microsoft.com/en-us/python/api/overview/azure/keyvault-certificates-readme)

---

### HashiCorp Vault

Fetch certificates from HashiCorp Vault KV engine.

**Type:** `vault`

**Required Fields:**
- `path`: Secret path under the mount point (e.g., `pki/trusted_roots`)

**Optional Fields:**
- `mount_point`: KV engine mount name (default: `secret`)
- `pem_field`: Field name containing PEM content (default: `pem`)
- `addr`: Vault address (defaults to `VAULT_ADDR` environment variable)
- `token_ref`: Environment variable for Vault token (default: `VAULT_TOKEN`)
- `namespace`: Vault namespace (optional, for Vault Enterprise)

**Environment Variables:**
- `VAULT_ADDR`: Vault server address
- `VAULT_TOKEN`: Vault authentication token

**Example:**

```yaml
fetch:
  - name: vault-root-ca
    type: vault
    mount_point: secret
    path: pki/trusted_roots
    pem_field: certificate
    addr: https://vault.company.com:8200
    namespace: prod
```

**References:**
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault KV Secrets Engine](https://www.vaultproject.io/docs/secrets/kv)

---

## Public Root Certificate Programs

### Mozilla Root Program

Fetch Mozilla's trusted root certificate bundle (NSS root store).

**Type:** `mozilla_roots`

**Optional Fields:**
- `url`: URL to Mozilla's CA bundle (defaults to `https://curl.se/ca/cacert.pem`)

**Default Source:** [curl.se mirror of Mozilla CA bundle](https://curl.se/ca/cacert.pem)

**Example:**

```yaml
fetch:
  - name: mozilla-roots
    type: mozilla_roots
    verify:
      sha256: abc123...  # Highly recommended for reproducibility
```

**Example with Custom URL:**

```yaml
fetch:
  - name: mozilla-roots
    type: mozilla_roots
    url: https://ccadb-public.secure.force.com/mozilla/IncludedRootsPEMTxt
```

**References:**
- [Mozilla CA Certificate Program](https://wiki.mozilla.org/CA)
- [Mozilla Included CA List](https://wiki.mozilla.org/CA/Included_Certificates)
- [Common CA Database (CCADB)](https://www.ccadb.org/)

---

### Microsoft Root Program

Fetch Microsoft's trusted root certificate bundle.

**Type:** `microsoft_roots`

**Optional Fields:**
- `url`: URL to Microsoft's CA bundle (defaults to CCADB Microsoft roots)

**Default Source:** [CCADB Microsoft Roots (ServerAuth)](https://ccadb.my.salesforce-sites.com/microsoft/IncludedRootsPEMTxt?TrustBitsInclude=ServerAuth)

**Example:**

```yaml
fetch:
  - name: microsoft-roots
    type: microsoft_roots
    verify:
      sha256: def456...
```

**References:**
- [Microsoft Trusted Root Program](https://docs.microsoft.com/en-us/security/trusted-root/program-requirements)
- [Common CA Database (CCADB)](https://www.ccadb.org/)

---

### Apple Root Program

Fetch Apple's trusted root certificate bundle.

**Type:** `apple_roots`

**Optional Fields:**
- `url`: URL to Apple's CA bundle (defaults to CCADB Apple roots)

**Default Source:** [CCADB Apple Roots (ServerAuth)](https://ccadb.my.salesforce-sites.com/apple/IncludedRootsPEMTxt?TrustBitsInclude=ServerAuth)

**Example:**

```yaml
fetch:
  - name: apple-roots
    type: apple_roots
    verify:
      sha256: 789abc...
```

**References:**
- [Apple Root Certificate Program](https://www.apple.com/certificateauthority/)
- [Common CA Database (CCADB)](https://www.ccadb.org/)

---

## Generic Fetchers

### URL (HTTPS/File)

Fetch certificates from HTTPS URLs or local file paths.

**Type:** `url`

**Required Fields:**
- `url`: HTTPS URL or file:// path to the certificate

**Security Notes:**
- HTTP URLs are rejected for security reasons
- HTTPS URLs are verified against system CAs by default
- Use `verify.ca_file` for custom CA verification
- Use `verify.tls_fingerprint_sha256` for certificate pinning

**Example:**

```yaml
fetch:
  - name: external-ca
    type: url
    url: https://example.com/certs/rootCA.pem
    verify:
      sha256: abc123...
      tls_fingerprint_sha256: def456...
```

**Example with Custom CA:**

```yaml
fetch:
  - name: internal-ca
    type: url
    url: https://pki.internal.company.com/root.pem
    verify:
      ca_file: config/certs/internal-ca.pem
```

---

### API

Fetch certificates from generic REST APIs using Bearer token authentication.

**Type:** `api`

**Required Fields:**
- `endpoint` or `url`: API endpoint URL

**Optional Fields:**
- `provider`: Provider hint (e.g., `keyfactor` for provider-specific defaults)
- `token_ref`: Environment variable containing the bearer token
- `headers`: Custom HTTP headers (specified under `verify.headers`)

**Example:**

```yaml
fetch:
  - name: api-cert
    type: api
    endpoint: https://pki.company.com/api/v1/certificates/root
    token_ref: PKI_API_TOKEN
    verify:
      headers:
        X-Custom-Header: value
```

**Example with Keyfactor:**

```yaml
fetch:
  - name: keyfactor-cert
    type: api
    provider: keyfactor
    endpoint: https://keyfactor.company.com/api/v1/certificates/download
    token_ref: KEYFACTOR_TOKEN
```

---

## Best Practices

### Security

1. **Always use SHA256 content pinning** for static sources (public root bundles, etc.)
2. **Use TLS certificate pinning** (`tls_fingerprint_sha256`) for critical internal sources
3. **Never hardcode credentials** - always use environment variable references
4. **Prefer token-based authentication** over username/password where available
5. **Use managed identities** when running in cloud environments (Azure, AWS, GCP)

### Reproducibility

1. **Pin content hashes** for all external sources to ensure reproducible builds
2. **Document source URLs** and update procedures in bundle metadata
3. **Version control** your bundle configurations
4. **Test offline mode** (`--skip-fetch`) with pre-staged sources for air-gapped environments

### Performance

1. **Cache credentials** in CI/CD environments using native secret management
2. **Use regional endpoints** for cloud storage when possible
3. **Monitor fetch timeouts** and adjust network settings if needed
4. **Consider fetching during off-peak hours** for large bundles

---

## Troubleshooting

### Common Issues

**Authentication failures:**
- Verify environment variables are set correctly
- Check token/credential expiration
- Ensure correct IAM/RBAC permissions

**Network timeouts:**
- Check firewall rules and proxy settings
- Verify DNS resolution for endpoints
- Consider increasing timeout values

**SHA256 mismatches:**
- Source content may have been updated
- Verify you're fetching the correct version/tag
- Re-compute and update the hash in your config

**TLS verification failures:**
- Ensure system CA certificates are up to date
- Use `ca_file` for custom/internal CAs
- Verify certificate chain is complete

### Getting Help

- Check [troubleshooting.md](./troubleshooting.md) for common issues
- Review [CONFIG-SPEC.md](./CONFIG-SPEC.md) for configuration details
- See [adr-0002-fetch.md](./adr-0002-fetch.md) for fetch architecture decisions

---

## Examples

### Complete Bundle with Multiple Sources

```yaml
---
bundle_name: hybrid-trust-bundle
description: Hybrid trust bundle with public and private roots

# Public root programs
fetch:
  - name: mozilla-roots
    type: mozilla_roots
    verify:
      sha256: abc123...

  - name: microsoft-roots
    type: microsoft_roots
    verify:
      sha256: def456...

  # Corporate root from S3
  - name: corporate-root
    type: s3
    bucket: company-pki
    key: roots/corporate-ca.pem
    region: us-east-1
    verify:
      sha256: 789abc...

  # Partner CA from Artifactory
  - name: partner-ca
    type: artifactory
    url: https://artifactory.company.com/artifactory
    repository: pki-release
    path: partners/partner-root.pem
    token_ref: ARTIFACTORY_TOKEN

  # Internal CA from Vault
  - name: internal-ca
    type: vault
    mount_point: secret
    path: pki/internal-root
    addr: https://vault.company.com:8200

include: []
exclude: []

metadata:
  owner: security-team@company.com
  purpose: Production trust bundle for all services
  tags: [production, hybrid, multi-source]
```

---

## Migration Guide

### From URL fetcher to Cloud Storage

**Before (URL):**
```yaml
fetch:
  - name: my-cert
    type: url
    url: https://storage.example.com/certs/root.pem
```

**After (S3):**
```yaml
fetch:
  - name: my-cert
    type: s3
    bucket: certs
    key: root.pem
```

### Adding Authentication

**Before (no auth):**
```yaml
fetch:
  - name: my-cert
    type: url
    url: https://internal.company.com/cert.pem
```

**After (with token):**
```yaml
fetch:
  - name: my-cert
    type: api
    endpoint: https://internal.company.com/cert.pem
    token_ref: PKI_TOKEN
```

---

*For more information, see [CONFIG-SPEC.md](./CONFIG-SPEC.md) and [adr-0002-fetch.md](./adr-0002-fetch.md).*
