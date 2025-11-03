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

### 4. Vault PKI Issuer Fetcher (`type: vault_pki`)

Retrieves certificates directly from HashiCorp Vault's PKI secrets engine issuer endpoint.

**Use cases:**

- PKI root CA certificates from Vault PKI
- Intermediate CA certificates from Vault PKI issuers
- Dynamic certificate retrieval from managed PKI infrastructure

**Security features:**

- Unauthenticated access (endpoint is publicly readable by design)
- Optional token-based authentication for Enterprise environments
- Custom Vault CA certificate validation
- Namespace support for Vault Enterprise
- Configurable retry and timeout policies

**Key differences from Vault KV fetcher:**

- Accesses PKI issuer endpoint (`/v1/{mount}/issuer/{issuer_ref}/pem`)
- Returns certificate directly in PEM format (no field extraction needed)
- Endpoint is unauthenticated by design per Vault API documentation
- Optimized for PKI certificate chain retrieval

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

### Vault PKI Issuer Configuration

```yaml
fetch:
  - name: vault_pki_root
    type: vault_pki
    mount_point: pki            # PKI secrets engine mount (default: 'pki')
    issuer_ref: default         # Issuer reference or UUID (default: 'default')
    addr: https://vault.example.com:8200  # optional, uses VAULT_ADDR env var
    token_ref: VAULT_TOKEN      # optional, endpoint is unauthenticated
    namespace: prod             # optional, for Vault Enterprise
    verify:
      ca_file: config/certs/vault-ca.pem  # optional custom CA
    # Fetch retry/timeout configuration (optional)
    timeout: 30                 # request timeout in seconds
    retries: 3                  # number of retry attempts
    backoff_factor: 2.0         # exponential backoff multiplier
    retry_on_status: [429, 502, 503, 504]  # HTTP codes to retry
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
    mount_point: pki
    issuer_ref: root-2024
    addr: https://vault.internal.company.com:8200
    # Optional: token_ref not required as endpoint is unauthenticated
    verify:
      ca_file: config/certs/vault-ca.pem
```

### Vault PKI with Enterprise Namespace

```yaml
fetch:
  - name: prod_pki_issuer
    type: vault_pki
    mount_point: pki_prod
    issuer_ref: issuer-prod-2024
    addr: https://vault.company.com:8200
    namespace: production       # Vault Enterprise namespace
    token_ref: VAULT_TOKEN      # Optional authentication
    verify:
      ca_file: config/certs/vault-ca.pem
    # Custom retry/timeout for production
    timeout: 45
    retries: 5
    backoff_factor: 2.5
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
| Vault PKI | `VAULT_ADDR` | Vault server address (optional, can be in config) |
| Vault PKI | `VAULT_TOKEN` | Optional authentication token (endpoint is unauthenticated) |

### Setting Environment Variables

```bash
# For API fetchers
export KEYFACTOR_TOKEN="your-keyfactor-api-token"

# For Vault KV fetchers
export VAULT_TOKEN="hvs.your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"

# For Vault PKI fetchers (token optional, endpoint is unauthenticated)
export VAULT_ADDR="https://vault.example.com:8200"
# export VAULT_TOKEN="hvs.your-vault-token"  # Optional

# For custom APIs
export CUSTOM_API_TOKEN="your-custom-token"
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

### Vault PKI Access Policies

The Vault PKI Issuer endpoint (`/v1/{mount}/issuer/{issuer_ref}/pem`) is **unauthenticated by design** according to HashiCorp's Vault API documentation. This means:

1. **No special Vault policies are required** for reading issuer certificates
2. The endpoint is publicly accessible to any client that can reach the Vault server
3. Authentication tokens are optional and not required for basic certificate retrieval

**Reference:** [Vault PKI API - Read Issuer Certificate](https://developer.hashicorp.com/vault/api-docs/secret/pki#read-issuer-certificate)

However, if you're operating in a Vault Enterprise environment with namespaces or have custom access controls, you may need:

**Minimal Vault Policy (if authentication is enforced):**
```hcl
# Allow reading PKI issuer certificates
path "pki/issuer/+/pem" {
  capabilities = ["read"]
}

# For specific issuers only
path "pki/issuer/default/pem" {
  capabilities = ["read"]
}
```

**For Vault Enterprise with Namespaces:**
```hcl
# Within a specific namespace
path "pki/issuer/+/pem" {
  capabilities = ["read"]
}
```

**Note on Security:**
- The issuer certificate endpoint returns public certificates only
- No private keys or sensitive data are exposed through this endpoint
- This aligns with PKI best practices where CA certificates are public by design
- TLS verification is still performed for the Vault connection itself

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