# BundleCraft Configuration Specification

This document defines the configuration schema for BundleCraft, clearly separating concerns between:

- **Bundle configs** (`config/bundles/*.yaml`) — Certificate sourcing and gathering
- **Craft configs** (`config/crafts/*.yaml`) — Build, output, and deployment configuration
- **Defaults** (`config/defaults.yaml`) — Global fallback settings

---

## Configuration Philosophy

### Bundle Configs: Source & Fetch Layer

**Purpose:** Define WHAT certificates to source and WHERE to get them

**Responsibilities:**

- Certificate source paths (`include`, `exclude`)
- Remote fetch definitions (`fetch`)
- Source verification and provenance
- Content metadata (descriptions, owners, tags)

**Forbidden (enforced):** The following keys are **not allowed** in bundle configs and will be ignored with warnings:
- `verify` — Verification policies
- `pem` — PEM output options
- `output_formats` — Output format list
- `package` — Packaging options
- `filters` — Certificate filters
- `format_overrides` — Format-specific settings

These must be defined in craft configs or rely on defaults.

### Craft Configs: Build & Deploy Layer

**Purpose:** Define HOW to build and WHERE to distribute

**Responsibilities:**

- Output formats (PEM, JKS, P7B, P12)
- Build paths and packaging (`package`)
- Verification and filtering policies (`verify`, `filters`)
- PEM output options (`pem`)
- Format-specific secrets (passwords via env vars)
- Distribution targets and CI/CD tags
- Bundle composition (`targets.<name>.includes`)

**Forbidden:** Certificate sources, fetch entries, include/exclude paths

> **Note:** Starting with v0.1.0, config separation is strictly enforced. If bundle configs contain build settings, warnings will be issued and those settings will be ignored. See [CONFIG-MIGRATION.md](CONFIG-MIGRATION.md) for migration guidance.

---

## 1) Bundle Configuration: `config/bundles/<bundle>.yaml`

Defines certificate sources for a logical bundle.

### Required Keys

- `bundle_name`: string (logical identifier)
- `description`: string (purpose/context)

### Source Definition

```yaml
include:  # Relative paths from repo root
  - sources/internal/rootCA.pem
  - sources/partners/
exclude:  # Optional exclusions
  - sources/partners/deprecated.pem
```

### Fetch Definitions

```yaml
fetch:
  - name: mozilla_roots
    type: url
    url: https://curl.se/ca/cacert.pem
    verify:
      sha256: <expected_sha256>  # Content pinning (recommended)

  - name: partner_roots
    type: api
    endpoint: https://api.partner.com/pki/roots
    token_ref: PARTNER_API_TOKEN
    verify:
      ca_file: sources/partner-ca.pem
      tls_fingerprint_sha256: <cert_pin>

  - name: vault_roots
    type: vault
    mount_point: secret
    path: pki/trusted_roots
    pem_field: pem
    addr: http://127.0.0.1:8200
    token_ref: VAULT_TOKEN
```

### Metadata

```yaml
metadata:
  owner: security-team@example.com
  purpose: Internal PKI trust anchors
  change_control: CAB-2025-001
  tags: [internal, production]
```

### Complete Bundle Config Example

```yaml
---
bundle_name: internal
description: Trust bundle for internal PKI services (root + issuing CAs)

include:
  - sources/internal/rootCA.pem
  - sources/internal/issuingCA1.pem

exclude: []

metadata:
  owner: pki-team@example.com
  purpose: Internal service mesh authentication
  tags: [internal, ca-bundle]
```

---

## 2) Craft Configuration: `config/crafts/<env>.yaml`

Defines build behavior and deployment configuration for an environment.

### Bundle Composition

```yaml
targets:
  internal-prod:
    includes: [internal, mozilla]  # Merge multiple bundles
  mozilla-only:
    includes: [mozilla]
```

### Output Configuration

```yaml
output_formats:  # Which formats to produce
  - pem   # Canonical PEM (always recommended)
  - p7b   # PKCS#7 DER
  - jks   # Java KeyStore
  - p12   # PKCS#12

build_path: dist/prod/  # Override default (dist/<env>/<bundle>/)
package: true  # Create .tar.gz of outputs
```

### Verification & Filtering

```yaml
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30

filters:
  unique_by_fingerprint: true
  not_expired_only: true
  ca_certs_only: true

pem:
  include_subject_comments: true  # Add "# Subject:" comments
```

### Format-Specific Secrets

```yaml
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD  # Read from environment
    alias_format: '{subject.CN}-{serial}'
  pkcs12:
    password_env: TRUST_P12_PASSWORD
```

### Distribution Metadata (for CI/CD pipeline use only)

```yaml
distribution_metadata:
  # NOTE: BundleCraft CLI does NOT publish or upload bundles directly.
  # This section provides metadata for CI/CD pipelines (e.g., GitHub Actions)
  # to know where and how to distribute built bundles. Keys/values are flexible.
  targets:
    - type: github-release
      enabled: true
      assets:
        - bundlecraft-trust.tar.gz
        - bundlecraft-trust-env-*.tar.gz
    - type: artifactory
      enabled: false
      repository: libs-release-local
      path: com/example/truststore/${VERSION}/
    - type: s3
      enabled: false
      bucket: company-truststores
      prefix: prod/
  tags:
    - production
    - signed
    - automated-build
```

### Complete Craft Config Example

```yaml
---
name: Production
description: Production environment with full certificate suite

  internal-prod:
    includes: [internal, mozilla]
  mozilla-only:
    includes: [mozilla]

output_formats:
  - pem
  - p7b
  - jks
  - p12

verify:
  fail_on_expired: true
  warn_days_before_expiry: 30

filters:
  unique_by_fingerprint: true
  not_expired_only: true
  ca_certs_only: true

format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD
  pkcs12:
    password_env: TRUST_P12_PASSWORD

distribution_metadata:
  # NOTE: BundleCraft CLI does NOT publish or upload bundles directly.
  # This section provides metadata for CI/CD pipelines (e.g., GitHub Actions)
  # to know where and how to distribute built bundles. Keys/values are flexible.
  targets:
    - type: github-release
      enabled: true
      description: Publish to GitHub Releases (handled by pipeline)
      assets:
        - bundlecraft-trust.tar.gz
        - bundlecraft-trust-env-*.tar.gz
    - type: artifactory
      enabled: false
      description: Example: JFrog Artifactory (not used currently)
    - type: s3
      enabled: false
      description: Example: AWS S3 (not used currently)
  tags:
    - production
    - signed
    - ci-cd
    - github-release

metadata:
  name: Production
  contact: security@bundlecraft.io
```

---

## 3) Defaults: `config/defaults.yaml`

Global fallback settings applied before craft config.

```yaml
---
output_formats:
  - pem
  - p7b
  - jks
  - p12

verify:
  fail_on_expired: true
  warn_days_before_expiry: 30

package: false

pem:
  include_subject_comments: true

filters:
  unique_by_fingerprint: true
  not_expired_only: true
  ca_certs_only: true

format_overrides:
  jks:
    alias_format: '{subject.CN}-{serial}'
  pkcs12:
    filename: default-ca-bundle.p12

metadata:
  maintainer: pki-team@example.com
  policy_version: 1.0
```

---

## Configuration Precedence

**For build settings:** `built-in defaults` → `config/defaults.yaml` → `config/crafts/<env>.yaml`

**For sources:** Only `config/bundles/<bundle>.yaml` is consulted (no merging with env)

**For composed targets:**

- Environment defines `targets.<name>.includes: [bundle1, bundle2]`
- Builder loads each bundle config and merges their `include` + `exclude` lists
- Environment config controls ALL build behavior (formats, verification, etc.)

---

## CLI Integration

### Build

```bash
bundlecraft build --env prod --bundle internal-prod --prefetch
```

- Loads `config/crafts/prod.yaml` for build settings
- Composes sources from `internal` and `mozilla` bundle configs
- Outputs to `dist/prod/internal-prod/` (or custom `build_path`)

### Fetch

```bash
bundlecraft fetch --env prod --bundle mozilla
```

- Loads `config/bundles/mozilla.yaml` for fetch definitions
- Stages to `sources/fetched/prod/mozilla/`

### Offline Build

```bash
bundlecraft build --env prod --bundle internal-prod --offline
```

- Fails if any bundle requires fetch and sources aren't pre-staged

---

## Distribution Target Types

Supported values for `distribution_metadata.targets[].type`:

- **`github-release`**: GitHub Releases (current repo or external)
- **`artifactory`**: JFrog Artifactory Maven/generic repository
- **`s3`**: AWS S3 bucket
- **`azure-blob`**: Azure Blob Storage
- **`http-post`**: Generic HTTP POST to webhook/API
- **`custom`**: User-defined (parsed by external tooling)

**Note:** BundleCraft itself does NOT perform publishing. The `distribution_metadata` section provides hints for downstream CI/CD pipelines (e.g., GitHub Actions, GitLab CI).

---

## Migration Guide

### Moving from old configs

**Bundle configs:**

- ✅ Keep: `include`, `exclude`, `fetch`, `metadata`
- ❌ Remove: `output_formats`, `verify`, `pem`, `filters`, `format_overrides`, `package`

**Craft configs:**

- ✅ Keep: `targets`, `output_formats`, `verify`, `filters`, `format_overrides`
- ✅ Add: `distribution` section with targets and tags
- ❌ Remove: `include`, `exclude`, `fetch` (belongs in bundles)

---

## Reserved Fields

- `bundle_cfg.package`: reserved (may be used for bundle-level compression hints)
- `env_cfg.publish_targets`: deprecated, use `distribution.targets` instead
- `env_cfg.build_path`: supported but optional (CLI `--output-root` takes precedence)

---

## Security Best Practices

1. **Fetch verification**: Always pin `sha256` for public/static sources (Mozilla)
2. **TLS pinning**: Use `ca_file` and/or `tls_fingerprint_sha256` for API fetches
3. **Secrets**: Never hardcode passwords; always use `*_env` keys to reference environment variables
4. **Distribution**: Use `enabled: false` to disable distribution targets in lower environments
5. **Tags**: Use environment tags to control CI/CD pipeline routing (e.g., only sign/publish `production` tagged envs)
