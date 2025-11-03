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

### 4. Google Cloud Storage Fetcher (`type: gcs`)

Retrieves certificates from Google Cloud Storage buckets with native GCP authentication.

**Use cases:**

- Certificates stored in GCS buckets
- Multi-region certificate distribution via GCS
- Integration with GCP infrastructure
- Cloud-native certificate management

**Security features:**

- Google Cloud SDK authentication (Application Default Credentials)
- Service account authentication via JSON key files
- IAM-based access control
- Content integrity verification (SHA256)
- Configurable retry and timeout behavior

**Required GCS Permissions:**

- `storage.objects.get` - Read objects from buckets
- `storage.buckets.get` - (Optional) Verify bucket access

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

### Google Cloud Storage (GCS) Fetcher Configuration

```yaml
fetch:
  - name: gcs_roots
    type: gcs
    bucket: my-certificates-bucket        # GCS bucket name
    object_path: certs/root-ca.pem        # Path to object in bucket (also accepts 'object' or 'path')
    project: my-gcp-project               # optional, GCP project ID
    credentials_file: /path/to/creds.json # optional, defaults to GOOGLE_APPLICATION_CREDENTIALS
    verify:
      sha256: "expected-sha256-hash"      # optional content verification
    # Optional: Override fetch retry/timeout settings
    timeout: 60         # Request timeout in seconds (default: 30)
    retries: 5          # Number of retry attempts (default: 3)
    backoff_factor: 2.0 # Exponential backoff multiplier (default: 2.0)
    retry_on_status: [429, 502, 503, 504]  # HTTP status codes to retry
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

### Google Cloud Storage Integration

```yaml
fetch:
  - name: gcp_roots
    type: gcs
    bucket: company-pki-certificates
    object_path: production/root-ca-bundle.pem
    project: my-company-pki
    verify:
      sha256: "expected-sha256-of-bundle"
    timeout: 60
    retries: 5
```

**Authentication Options:**

1. **Service Account Key File** (recommended for CI/CD):
   ```yaml
   fetch:
     - name: gcp_certs
       type: gcs
       bucket: secure-certs
       object_path: certs/root.pem
       credentials_file: config/gcp-service-account.json
   ```

2. **Application Default Credentials** (for GCE/GKE/Cloud Run):
   ```yaml
   fetch:
     - name: gcp_certs
       type: gcs
       bucket: secure-certs
       object_path: certs/root.pem
       # No credentials_file needed - uses ADC
   ```

3. **Environment Variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
   ```
   ```yaml
   fetch:
     - name: gcp_certs
       type: gcs
       bucket: secure-certs
       object_path: certs/root.pem
       # Uses GOOGLE_APPLICATION_CREDENTIALS env var
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
| Vault | `VAULT_TOKEN` | Vault authentication token |
| Vault | `VAULT_ADDR` | Vault server address (optional, can be in config) |
| GCS | `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key file (optional, can use ADC) |
| GCS | `GOOGLE_CLOUD_PROJECT` | Default GCP project ID (optional) |

### Setting Environment Variables

```bash
# For API fetchers
export KEYFACTOR_TOKEN="your-keyfactor-api-token"

# For Vault fetchers
export VAULT_TOKEN="hvs.your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"

# For custom APIs
export CUSTOM_API_TOKEN="your-custom-token"

# For GCS fetcher
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="my-gcp-project"  # Optional

# Alternatively, use gcloud CLI to configure Application Default Credentials
gcloud auth application-default login
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

#### "GCS: google-cloud-storage not installed" Error

**Problem:** Missing GCS dependencies when using Python package installation

**Solution:** Install with fetcher dependencies:
```bash
pip install bundlecraft[fetchers]
```

Note: When using containers, GCS support is included by default.

#### "GCS: Access denied" or "403 Forbidden" Error

**Problem:** Insufficient permissions to access GCS bucket or object

**Solution:** 

1. Verify service account has required IAM permissions:
   ```bash
   # Grant required permissions (run as GCP admin)
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
     --role="roles/storage.objectViewer"
   ```

2. Ensure the bucket and object path are correct:
   ```bash
   # List objects in bucket to verify
   gsutil ls gs://your-bucket-name/path/to/
   ```

3. Verify credentials are valid:
   ```bash
   # Test authentication
   gcloud auth application-default print-access-token
   ```

#### "GCS: Object not found" or "404 Not Found" Error

**Problem:** Bucket or object doesn't exist or path is incorrect

**Solution:**

1. Verify bucket exists and is accessible:
   ```bash
   gsutil ls gs://bucket-name
   ```

2. Check object path (case-sensitive):
   ```bash
   gsutil ls gs://bucket-name/path/to/object.pem
   ```

3. Ensure you have the correct bucket name and object path in your config

#### "GCS: Authentication failed" or "401 Unauthorized" Error

**Problem:** Invalid or expired credentials

**Solution:**

1. Refresh Application Default Credentials:
   ```bash
   gcloud auth application-default login
   ```

2. Verify service account key is valid and not expired:
   ```bash
   gcloud auth activate-service-account --key-file=/path/to/key.json
   ```

3. Check that GOOGLE_APPLICATION_CREDENTIALS points to a valid file:
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   cat $GOOGLE_APPLICATION_CREDENTIALS | jq .type  # Should output "service_account"
   ```

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