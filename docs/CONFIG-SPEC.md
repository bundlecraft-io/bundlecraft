# BundleCraft Configuration Specification

This document defines the configuration schema for BundleCraft, clearly separating concerns between:

- **Bundle configs** (`config/bundles/*.yaml`) — Certificate sourcing and gathering
- **Craft configs** (`config/crafts/*.yaml`) — Build, output, and deployment configuration
- **Defaults** (`config/defaults.yaml`) — Global fallback settings

---

## Schema Validation

**All configuration files are validated against a Pydantic schema at load time.**

Benefits:
- **Fail fast**: Invalid configs are rejected immediately with clear error messages
- **Type safety**: Field types (strings, integers, booleans, lists) are enforced
- **Required fields**: Missing required fields are caught early
- **Value constraints**: Min/max values, string patterns, and enums are validated

When validation fails, you'll see detailed error messages indicating:
- Which field failed validation
- The expected type or constraint
- The actual value that was provided

Example error message:
```
Config validation failed for config/bundles/invalid.yaml: Bundle config validation failed: 
2 validation errors for BundleConfig
bundle_name
  Field required [type=missing]
fetch.0.verify.sha256
  Input should be a valid string [type=string_type, input_value=0]
```

---

## Configuration Philosophy

### Bundle Configs: Source & Fetch Layer

**Purpose:** Define WHAT certificates to source and WHERE to get them

**Responsibilities:**

- Certificate source paths (`include`, `exclude`)
- Remote fetch definitions (`fetch`)
- Source verification and provenance
- Content metadata (descriptions, owners, tags)

**Forbidden:** Output formats, build paths, passwords, verification policies

### Craft Configs: Build & Deploy Layer

**Purpose:** Define HOW to build and WHERE to distribute

**Responsibilities:**

- Output formats (PEM, JKS, P7B, P12)
- Build paths and packaging
- Verification and filtering policies
- Format-specific secrets (passwords via env vars)
- Distribution targets and CI/CD tags
- Bundle composition (`targets.<name>.includes`)

**Forbidden:** Certificate sources, fetch entries, include/exclude paths

---

## 1) Bundle Configuration: `config/bundles/<bundle>.yaml`

Defines certificate sources for a logical bundle.

### Required Keys

- `bundle_name`: string (logical identifier, min length: 1)
- `description`: string (purpose/context, min length: 1)

### Schema Constraints

**Required Fields:**
- `bundle_name` and `description` are mandatory and cannot be empty

**Validation Rules:**
- Repository names (`repo[].name`) must be unique within a bundle
- Fetch names (`fetch[].name`) must be unique if explicitly provided
- Repository and fetch names cannot conflict with each other
- Reserved names (`include`, `exclude`, `fetch`) cannot be used as repo or fetch names
- Fetch type `url` requires a `url` field
- Fetch type `api` requires either `endpoint` or `url` field
- Fetch type `vault` requires `mount_point` and `path` fields
- Include items can be:
  - Plain strings (file/directory paths)
  - Objects with `path` field
  - Objects with `inline` field (for inline PEM content)
  - Objects cannot have both `path` and `inline`

### Source Definition

You can declare local certificate sources in two ways. The new preferred schema uses named repositories for clearer provenance and target path construction. The legacy flat include/exclude form remains supported for backward compatibility.

- Preferred: named repositories under `repo:`

  ```yaml
  repo:
    - name: roots
      include:  # "include" items support both path and inline entries
        # 1) Path entries (string or {path: ...})
        - sources/internal/roots/
        - { path: sources/internal/rootCA.pem }
        # 2) Inline PEM entries ({inline: <PEM>, name?: <filename>})
        # When "name" is omitted, a filename like inline-1.pem is generated.
        - name: special-inline.pem
          inline: |
            -----BEGIN CERTIFICATE-----
            ...PEM-CONTENT-ELIDED...
            -----END CERTIFICATE-----
      exclude:  # optional exclusions within this repo
        - sources/internal/roots/deprecated.pem

    - name: partners
      include:
        - sources/partners/
  ```

  Include item forms supported:
  - String: a file or directory path
  - Mapping with `path`: `{ path: <file-or-dir> }`
  - Mapping with `inline`: `{ inline: <PEM text>, name?: <filename> }`

  Notes for `inline` entries:
  - PEM text can be provided as a YAML block scalar (recommended).
  - Indentation is handled automatically; trailing whitespace is trimmed.
  - If `name` is omitted, files are created as `inline-<N>.pem` within the repo folder.

  Staging layout: `sources/staged/<craft>/<bundle>/<name>/...`

- Legacy: flat `include`/`exclude` keys at the top level

  ```yaml
  include:
    - sources/internal/rootCA.pem
    - sources/partners/
  exclude:
    - sources/partners/deprecated.pem
  ```

  Staging layout: `sources/staged/<craft>/<bundle>/include/...`

Validation rules for names:

- Each `repo[].name` must be unique and must not use reserved names like `include`.
- If `fetch[].name` is provided, those names must be unique as well.
- A `repo[].name` must not conflict with any `fetch[].name`.

### Minimal Examples

Repo with both path and inline entries:

```yaml
repo:
  - name: roots
    include:
      - sources/internal/roots/
      - { path: sources/internal/rootCA.pem }
      - name: special-inline.pem
        inline: |
          -----BEGIN CERTIFICATE-----
          ...
          -----END CERTIFICATE-----
```

Legacy form (paths only):

```yaml
include:
  - sources/internal/roots/
  - sources/internal/rootCA.pem
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

## 2) Craft Configuration: `config/crafts/<craft>.yaml`

Defines build behavior and deployment configuration for a craft.

### Schema Constraints

**Field Validation:**
- `output_formats`: Must be one of: `pem`, `p7b`, `jks`, `p12`, `pkcs12`
- `verify.warn_days_before_expiry`: Must be >= 0
- `filters.minimum_key_size_rsa`: Must be >= 1024 bits (if specified)
- `filters.minimum_key_size_ecc`: Must be >= 160 bits (if specified)
- `targets`: Can be dict format `{name: {includes: [...]}}` or list format with `target_name`/`name` and `includes`/`include_bundles`/`compose`

**Optional Fields:**
- Most fields have sensible defaults and are optional
- `name`, `description`, `targets` can be omitted for simple configs

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

# Outputs are written by default to: dist/<craft-name>/<target-name>/
package: true  # Create .tar.gz of outputs
```

### Verification & Filtering

```yaml
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30

filters:
  unique_by_fingerprint: true   # Deduplicate by SHA256 fingerprint
  not_expired_only: true         # Exclude expired certificates
  ca_certs_only: true            # Only CA certificates (BasicConstraints CA:TRUE)
  root_certs_only: true          # Only self-signed root CAs (default: true)
  # Optional filters (undefined by default):
  # signature_algorithms:        # Filter by signature algorithm
  #   include: ["sha256WithRSAEncryption", "ecdsa-with-SHA256"]
  #   exclude: ["sha1WithRSAEncryption", "md5WithRSAEncryption"]
  # minimum_key_size_rsa: 2048   # Minimum RSA key size in bits
  # minimum_key_size_ecc: 256    # Minimum ECC key size in bits

pem:
  include_subject_comments: true  # Add "# Subject:" comments
```

### Format-Specific Secrets

```yaml
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD  # Read from environment
    # Alias naming for each imported certificate
    # Placeholders: {subject.CN}, {serial}, {fingerprint}, {fingerprint_sha1}, {fingerprint_sha256}
    # Defaults to: '{subject.CN}-{fingerprint}'
    alias_format: '{subject.CN}-{fingerprint}'
  pkcs12:
    password_env: TRUST_P12_PASSWORD
    # Optional: control the friendly name (-name) inside the P12
    # Follows the same alias_format placeholders and default
    # alias_format: '{subject.CN}-{fingerprint}'
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
        - bundlecraft-trust-*.tar.gz
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
description: Production craft with full certificate suite

targets:
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
  root_certs_only: true  # Only self-signed roots (default)
  # Optional: signature_algorithms, minimum_key_size_rsa, minimum_key_size_ecc

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
        - bundlecraft-trust-*.tar.gz
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

### Schema Constraints

**Field Validation:**
- `output_formats`: Must be one of: `pem`, `p7b`, `jks`, `p12`, `pkcs12`
- All validation rules from craft configs apply to defaults

**Behavior:**
- Empty/minimal defaults configs are valid - model provides sensible defaults
- Defaults are merged with craft configs (craft settings override defaults)

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
  root_certs_only: true  # Only self-signed root CAs (default)
  # Optional filters (undefined by default):
  # signature_algorithms:
  #   include: ["sha256WithRSAEncryption"]
  #   exclude: ["sha1WithRSAEncryption"]
  # minimum_key_size_rsa: 2048
  # minimum_key_size_ecc: 256

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

**For build settings:** `built-in defaults` → `config/defaults.yaml` → `config/crafts/<craft>.yaml`

**For sources:** Only `config/bundles/<bundle>.yaml` is consulted (no merging with craft)

**For composed targets:**

- Craft defines `targets.<name>.includes: [bundle1, bundle2]`
- Builder loads each bundle config and merges their `include` + `exclude` lists
- Craft config controls ALL build behavior (formats, verification, etc.)

---

## CLI Integration

### Build

```bash
bundlecraft build --craft prod --bundle internal-prod
```

- Loads `config/crafts/prod.yaml` for build settings
- Composes sources from `internal` and `mozilla` bundle configs
- Outputs to `dist/Production/internal-prod/`

To overwrite existing artifacts:

```bash
bundlecraft build --craft prod --bundle internal-prod --force
```

### Fetch

```bash
bundlecraft fetch --bundle-config-file config/bundles/mozilla.yaml --workspace-root .
```

- Loads `config/bundles/mozilla.yaml` and stages into `sources/staged/<craft>/<bundle>/`
  - Stages into `sources/staged/<craft>/<target>/` during build
- Note: `bundlecraft build` performs fetch automatically unless `--skip-fetch` is used

### Using Existing Staged Sources

```bash
bundlecraft build --craft prod --bundle internal-prod --skip-fetch
```

- Uses existing staged sources at `sources/staged/prod/*` and does not perform network fetches

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
- `craft_cfg.publish_targets`: deprecated, use `distribution.targets` instead
- `craft_cfg.build_path`: deprecated; prefer CLI `--output-root`

---

## Common Validation Errors

### Bundle Config Errors

**Missing Required Fields**
```
Error: Field required [type=missing, input_value={...}]
Solution: Add required fields 'bundle_name' and 'description'
```

**Duplicate Names**
```
Error: Duplicate repository names found: roots
Solution: Ensure all repo[].name values are unique
```

**Name Conflicts**
```
Error: Name conflict between repo and fetch entries: remote1
Solution: Ensure repo names and fetch names don't overlap
```

**Reserved Names**
```
Error: Repository name 'include' is reserved. Choose a different name.
Solution: Don't use 'include', 'exclude', or 'fetch' as repo/fetch names
```

**Invalid Include Items**
```
Error: Include item cannot have both 'path' and 'inline' fields
Solution: Use either path OR inline, not both
```

### Craft Config Errors

**Invalid Output Format**
```
Error: Invalid output format 'bad_format'. Valid formats: jks, p12, p7b, pem, pkcs12
Solution: Use only supported format names
```

**Invalid Key Size**
```
Error: Input should be greater than or equal to 1024 [type=greater_than_equal]
Solution: Set minimum_key_size_rsa >= 1024 or minimum_key_size_ecc >= 160
```

**Negative Values**
```
Error: Input should be greater than or equal to 0 [type=greater_than_equal]
Solution: Set warn_days_before_expiry to a non-negative value
```

### General Tips

1. **Check YAML syntax**: Ensure proper indentation and structure
2. **Quote strings with special chars**: Use quotes for strings like "0000..." to prevent YAML from parsing as integers
3. **Required vs Optional**: Bundle configs require name and description; most craft/defaults fields are optional
4. **Validation on load**: Configs are validated immediately when loaded, so errors are caught early
5. **Detailed errors**: Pydantic provides the exact field path and constraint that failed

## Security Best Practices

1. **Fetch verification**: Always pin `sha256` for public/static sources (Mozilla)
2. **TLS pinning**: Use `ca_file` and/or `tls_fingerprint_sha256` for API fetches
3. **Secrets**: Never hardcode passwords; always use `*_env` keys to reference environment variables
4. **Distribution**: Use `enabled: false` to disable distribution targets in lower environments
5. **Tags**: Use environment tags to control CI/CD pipeline routing (e.g., only sign/publish `production` tagged envs)
6. **Validation**: Schema validation helps catch misconfigurations before they cause issues in production
