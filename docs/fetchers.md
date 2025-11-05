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

### 4. S3 Fetcher (`type: s3`)

Retrieves certificates from AWS S3 storage buckets or S3-compatible object storage services.

**Use cases:**

- Certificate bundles stored in S3 for centralized distribution
- Certificates managed through AWS infrastructure
- Integration with existing S3-based artifact repositories
- S3-compatible storage (MinIO, Ceph, etc.)

**Security features:**

- AWS credential chain (env variables, IAM roles, profiles)
- Support for IAM policies and bucket policies
- Custom CA validation for S3-compatible endpoints
- Regional deployment support
- Content verification via SHA256

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

### S3 Fetcher Configuration

```yaml
fetch:
  # Using s3:// URL format
  - name: s3_bundle
    type: s3
    url: s3://my-bucket/certificates/bundle.pem
    region: us-west-2           # optional, uses default AWS region if not specified
    verify:
      sha256: "expected-content-hash"  # optional content verification
  
  # Using explicit bucket and key parameters
  - name: s3_explicit
    type: s3
    bucket: my-certificate-bucket
    key: production/root-ca.pem
    region: us-east-1
    verify:
      sha256: "expected-content-hash"
  
  # S3-compatible storage (MinIO, Ceph, etc.)
  - name: minio_bundle
    type: s3
    bucket: certificates
    key: bundles/internal-ca.pem
    endpoint_url: https://minio.example.com:9000  # custom S3-compatible endpoint
    region: us-east-1           # required for signature calculation
    verify:
      ca_file: config/certs/minio-ca.pem  # for self-signed certificates
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

### AWS Credential Chain (S3 Fetcher)

The S3 fetcher uses the standard AWS credential chain for authentication, checking credentials in this order:

1. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
2. **Shared credential file**: `~/.aws/credentials` (selected by `AWS_PROFILE` if set)
3. **AWS config file**: `~/.aws/config`
4. **IAM role for Amazon EC2**: When running on EC2 instances
5. **IAM role for ECS tasks**: When running in ECS containers
6. **IAM role for Lambda**: When running in AWS Lambda

**Recommended approach for production:**
- Use IAM roles when running on AWS infrastructure (EC2, ECS, Lambda)
- Use dedicated IAM users or roles with least-privilege policies
- Rotate access keys regularly if using long-term credentials

**Required IAM Permissions:**

Minimum IAM policy for S3 fetcher:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": [
        "arn:aws:s3:::your-certificate-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-certificate-bucket"
      ]
    }
  ]
}
```

For cross-account access, add trust relationships to the IAM role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT-ID:role/BundleCraftRole"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
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

### AWS S3 Bucket

```yaml
fetch:
  - name: s3_certificates
    type: s3
    bucket: company-certificates
    key: bundles/production/root-ca-bundle.pem
    region: us-west-2
    verify:
      sha256: "expected-bundle-hash"
```

### S3-Compatible Storage (MinIO)

```yaml
fetch:
  - name: minio_certs
    type: s3
    bucket: pki-bundles
    key: certificates/internal-roots.pem
    endpoint_url: https://minio.internal.company.com:9000
    region: us-east-1  # required for AWS signature
    verify:
      ca_file: config/certs/minio-ca.pem  # for self-signed MinIO
```

## Environment Variables

### Required for Authentication

| Fetcher Type | Environment Variable | Purpose |
|--------------|---------------------|---------|
| API (Keyfactor) | `KEYFACTOR_TOKEN` | API authentication token |
| API (Generic) | `CUSTOM_API_TOKEN` | Custom API token (configurable name) |
| Vault | `VAULT_TOKEN` | Vault authentication token |
| Vault | `VAULT_ADDR` | Vault server address (optional, can be in config) |
| S3 | `AWS_ACCESS_KEY_ID` | AWS access key (optional, see AWS credential chain) |
| S3 | `AWS_SECRET_ACCESS_KEY` | AWS secret key (optional, see AWS credential chain) |
| S3 | `AWS_SESSION_TOKEN` | AWS session token for temporary credentials (optional) |
| S3 | `AWS_REGION` | Default AWS region (optional, can be in config) |
| S3 | `AWS_PROFILE` | AWS credential profile to use (optional) |

### Setting Environment Variables

```bash
# For API fetchers
export KEYFACTOR_TOKEN="your-keyfactor-api-token"

# For Vault fetchers
export VAULT_TOKEN="hvs.your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"

# For custom APIs
export CUSTOM_API_TOKEN="your-custom-token"

# For S3 fetchers (if not using IAM roles)
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_REGION="us-west-2"  # optional, can be specified in config

# For S3 with AWS credential profiles
export AWS_PROFILE="production"
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

#### "AWS credentials not found" Error

**Problem:** S3 fetcher cannot locate AWS credentials

**Solution:** Configure AWS credentials using one of these methods:

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-west-2"

# Option 2: AWS credential file
aws configure
# Enter your credentials when prompted

# Option 3: Use IAM role (when running on AWS)
# No configuration needed - automatic
```

#### "S3 bucket not found" Error

**Problem:** Specified S3 bucket does not exist or is in a different region

**Solution:**
1. Verify bucket name is correct
2. Check that bucket exists: `aws s3 ls s3://your-bucket-name/`
3. Ensure region is correctly specified in config if bucket is not in default region
4. Verify IAM permissions allow ListBucket on the bucket

#### "S3 object not found" Error

**Problem:** Specified object key does not exist in the bucket

**Solution:**
1. Verify object key is correct (check for typos, extra slashes)
2. List bucket contents: `aws s3 ls s3://your-bucket-name/path/`
3. Check if object is in a different prefix/folder
4. Ensure object hasn't been deleted or moved

#### "Access denied to S3 bucket" Error

**Problem:** IAM permissions do not allow access to bucket or object

**Solution:**
1. Verify IAM policy allows `s3:GetObject` on the specific bucket/key
2. Check bucket policy allows access from your AWS account/role
3. Review any S3 bucket ACLs that might restrict access
4. For cross-account access, verify trust relationships are configured
5. Test access: `aws s3 cp s3://your-bucket-name/key /tmp/test`

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
