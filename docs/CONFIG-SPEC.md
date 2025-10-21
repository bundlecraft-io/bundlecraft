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

- `bundle_name`: string (logical identifier)
- `description`: string (purpose/context)

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

BundleCraft supports multiple fetcher types for various sources. See [FETCHERS.md](./FETCHERS.md) for comprehensive documentation.

**Common fetcher types:**

```yaml
fetch:
  # Public root programs (recommended with SHA256 pinning)
  - name: mozilla_roots
    type: mozilla_roots
    verify:
      sha256: <expected_sha256>

  - name: microsoft_roots
    type: microsoft_roots
    verify:
      sha256: <expected_sha256>

  # Cloud storage
  - name: s3_cert
    type: s3
    bucket: my-pki-bucket
    key: certs/rootCA.pem
    region: us-east-1
    verify:
      sha256: <expected_sha256>

  - name: azure_blob_cert
    type: azure_blob
    container: pki-certs
    blob_name: certs/rootCA.pem
    connection_string_ref: AZURE_STORAGE_CONNECTION_STRING

  - name: gcs_cert
    type: gcs
    bucket: my-pki-bucket
    blob_name: certs/rootCA.pem

  # Artifact repositories
  - name: artifactory_cert
    type: artifactory
    url: https://artifactory.company.com/artifactory
    repository: libs-release-local
    path: certs/rootCA.pem
    token_ref: ARTIFACTORY_TOKEN

  - name: github_release_cert
    type: github_release
    owner: myorg
    repo: pki-certs
    asset_name: rootCA.pem
    tag: v1.0.0

  # Key management
  - name: azure_keyvault_cert
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net/
    certificate_name: my-root-ca

  - name: vault_cert
    type: vault
    mount_point: secret
    path: pki/trusted_roots
    pem_field: pem
    addr: https://vault.company.com:8200
    token_ref: VAULT_TOKEN

  # Generic sources
  - name: url_cert
    type: url
    url: https://example.com/cert.pem
    verify:
      sha256: <expected_sha256>
      tls_fingerprint_sha256: <cert_pin>
      sha256: <expected_sha256>  # Content pinning (recommended)
    # Optional: Override fetch retry/timeout settings
    timeout: 60         # Request timeout in seconds (default: 30)
    retries: 5          # Number of retry attempts (default: 3)
    backoff_factor: 2.0 # Exponential backoff multiplier (default: 2.0)
    retry_on_status: [429, 502, 503, 504]  # HTTP status codes to retry

  - name: api_cert
    type: api
    endpoint: https://api.partner.com/pki/roots
    token_ref: PARTNER_API_TOKEN
    verify:
      ca_file: sources/partner-ca.pem
```

**Installation:**
Extended fetchers require additional dependencies:
```bash
pip install 'bundlecraft[cloud,fetchers]'
      tls_fingerprint_sha256: <cert_pin>
    # Example: Slower API needs longer timeout
    timeout: 120
    retries: 5

  - name: vault_roots
    type: vault
    mount: secret
    path: pki/trusted_roots
    pem_field: pem
    addr: http://127.0.0.1:8200
    token_ref: VAULT_TOKEN
```

**Fetch Retry and Timeout Configuration:**

All fetch operations support configurable timeout and retry behavior to handle transient network failures gracefully:

- **`timeout`** (integer, 1-600): Request timeout in seconds. Default: 30
- **`retries`** (integer, 0-10): Number of retry attempts on transient failures. Default: 3
- **`backoff_factor`** (float, 1.0-10.0): Exponential backoff multiplier between retries. Default: 2.0
  - Retry delays: backoff_factor^attempt with random jitter (e.g., 2.0^0=1s, 2.0^1=2s, 2.0^2=4s)
- **`retry_on_status`** (list of integers): HTTP status codes that trigger retry. Default: [429, 502, 503, 504]
  - 429: Too Many Requests (rate limiting)
  - 502: Bad Gateway (temporary proxy error)
  - 503: Service Unavailable (temporary service error)
  - 504: Gateway Timeout (temporary timeout)

These settings can be configured globally in `config/defaults.yaml` under the `fetch:` section, or overridden per-source in bundle configs. Network errors (timeouts, connection failures) are always retried automatically.

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

### Output Metadata for GitOps

BundleCraft supports attaching structured metadata (annotations and labels) to build outputs for GitOps orchestration systems like ArgoCD, Flux, and Kubernetes.

```yaml
output_metadata:
  annotations:
    # Static annotations
    argocd.argoproj.io/sync-wave: "1"
    kustomize.toolkit.fluxcd.io/prune: "true"
    
    # Dynamic annotations with template variables
    build-timestamp: "{{timestamp}}"
    bundle-version: "{{bundle}}-{{env}}-{{date}}"
    git-commit: "{{git_commit}}"
    
  labels:
    # Static labels
    app.kubernetes.io/component: "trust-bundle"
    app.kubernetes.io/managed-by: "bundlecraft"
    
    # Dynamic labels with template variables
    environment: "{{env}}"
    bundle-id: "{{bundle}}"
```

**Template Variables:**

- `{{bundle}}` - Target name (e.g., "internal-prod")
- `{{env}}` - Craft/environment name (e.g., "production")
- `{{timestamp}}` - ISO 8601 timestamp in UTC (e.g., "2025-10-21T12:00:00Z")
- `{{date}}` - Date in YYYY-MM-DD format (e.g., "2025-10-21")
- `{{git_commit}}` - Git commit hash (short form, 7 chars, or "unknown")

**Output:**

1. **manifest.json** - Expanded metadata is always included in the `output_metadata` field
2. **metadata.yaml** - Optional YAML sidecar for Kubernetes ConfigMap/Secret generation

**Example manifest.json snippet:**

```json
{
  "craft": "Production",
  "target": "internal-prod",
  "timestamp_utc": "2025-10-21T12:00:00Z",
  "output_metadata": {
    "annotations": {
      "argocd.argoproj.io/sync-wave": "1",
      "build-timestamp": "2025-10-21T12:00:00Z",
      "bundle-version": "internal-prod-production-2025-10-21",
      "git-commit": "d0dfaa2"
    },
    "labels": {
      "app.kubernetes.io/component": "trust-bundle",
      "environment": "production",
      "bundle-id": "internal-prod"
    }
  }
}
```

**Example metadata.yaml:**

```yaml
annotations:
  argocd.argoproj.io/sync-wave: '1'
  build-timestamp: '2025-10-21T12:00:00Z'
  bundle-version: internal-prod-production-2025-10-21
  git-commit: d0dfaa2
labels:
  app.kubernetes.io/component: trust-bundle
  bundle-id: internal-prod
  environment: production
```

**Use Cases:**

- **ArgoCD Sync Waves**: Control deployment order with `argocd.argoproj.io/sync-wave`
- **Flux Prune Policy**: Manage resource cleanup with `kustomize.toolkit.fluxcd.io/prune`
- **Kubernetes Labels**: Organize and select resources with standard labels
- **Versioning**: Track bundle versions with dynamic template variables
- **Traceability**: Link builds to git commits for audit trails
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

# Output metadata for GitOps orchestration (ArgoCD, Flux, Kubernetes)
output_metadata:
  annotations:
    # Template variables: {{bundle}}, {{env}}, {{timestamp}}, {{date}}, {{git_commit}}
    build-timestamp: "{{timestamp}}"
    bundle-version: "{{bundle}}-{{env}}-{{date}}"
    git-commit: "{{git_commit}}"
    argocd.argoproj.io/sync-wave: "1"
  labels:
    environment: "{{env}}"
    bundle-id: "{{bundle}}"
    app.kubernetes.io/component: "trust-bundle"
    app.kubernetes.io/managed-by: "bundlecraft"
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

output_metadata:
  annotations:
    build-timestamp: "{{timestamp}}"
    bundle-version: "{{bundle}}-{{env}}-{{date}}"
    git-commit: "{{git_commit}}"
    argocd.argoproj.io/sync-wave: "1"
  labels:
    environment: "{{env}}"
    bundle-id: "{{bundle}}"
    app.kubernetes.io/component: "trust-bundle"

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

fetch:
  timeout: 30  # Request timeout in seconds (1-600)
  retries: 3   # Number of retry attempts on transient failures (0-10)
  backoff_factor: 2.0  # Exponential backoff multiplier (1.0-10.0)
  retry_on_status: [429, 502, 503, 504]  # HTTP status codes that trigger retry

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

## Schema Validation

BundleCraft uses Pydantic v2 for comprehensive configuration validation. All configs are validated at load time with clear error messages.

For step-by-step guidance on interpreting and fixing validation errors (plus pytest and pre-commit tips), see:
- docs/troubleshooting.md → YAML schema/validation failures
- docs/troubleshooting.md → Pytest failures: quick navigation
- docs/troubleshooting.md → pre-commit failures: common hooks and fixes

### Required Fields

**Bundle Configs:**
- `bundle_name` (string, non-empty) - Unique identifier for the bundle
- `description` (string, non-empty) - Human-readable purpose/context
- At least one of: `repo[]` or `fetch[]` - Must define at least one certificate source

**Craft Configs:**
- `name` (string, non-empty) - Display name for the craft
- `description` (string, non-empty) - Human-readable purpose/context
- `targets` (dict or list, non-empty) - At least one build target required

**Defaults Config:**
- No strictly required fields (all have sensible defaults)

### Value Constraints

**Output Formats:**
- Valid values: `pem`, `p7b`, `jks`, `p12`, `pkcs12`, `der`
- Invalid formats trigger a clear error with the list of valid options

**Key Size Requirements (Security):**
- RSA keys: minimum 1024 bits (configurable via `filters.minimum_key_size_rsa`)
- ECC keys: minimum 192 bits (configurable via `filters.minimum_key_size_ecc`)

**Expiry Warnings:**
- `warn_days_before_expiry`: must be between 0 and 365 days

**URL Security:**
- Only `https://` and `file://` URLs are allowed (enforced for `fetch[].url` and `fetch[].endpoint`)
- Exception: `http://localhost` and `http://127.0.0.1` are permitted for local development
- Insecure HTTP URLs trigger: `"Only HTTPS URLs are allowed for security"`

**Reserved Names:**
- The following names are reserved and cannot be used for bundle names, repo names, or fetch names:
  - `include`, `exclude`, `fetch`, `repo`
- Using a reserved name triggers: `"'<name>' is a reserved name and cannot be used"`

**Name Uniqueness:**
- All `repo[].name` values must be unique within a bundle
- All `fetch[].name` values must be unique within a bundle
- No `repo[].name` can conflict with any `fetch[].name` in the same bundle

**Type-Specific Requirements:**
- `fetch[].type: url` → requires `url` field
- `fetch[].type: vault` → requires both `mount` and `path` fields
- `fetch[].type: api` → requires `endpoint` field

**Target Requirements:**
- Each target in `targets` must have at least one of: `includes`, `include_bundles`, or `compose`
- Empty targets trigger: `"At least one of 'includes', 'include_bundles', or 'compose' must be provided"`

**Inline PEM Entries:**
- Dictionary entries in `repo[].include[]` must have either `inline` or `path` key
- Invalid: `{"invalid_key": "value"}` → triggers error

### Common Validation Errors

**Error: Missing required field**
```
1 validation error for BundleConfig
bundle_name
  Field required [type=missing, input_value={...}, input_type=dict]
```
**Fix:** Add the required field:
```yaml
bundle_name: my-bundle
description: My bundle description
```

---

**Error: Empty string**
```
1 validation error for BundleConfig
description
  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]
```
**Fix:** Provide a non-empty value:
```yaml
description: Internal CA roots for production
```

---

**Error: Invalid output format**
```
1 validation error for CraftConfig
output_formats
  Value error, Invalid output format 'jsk'. Valid formats: der, jks, p12, p7b, pem, pkcs12
```
**Fix:** Use a valid format name:
```yaml
output_formats: [pem, jks, p7b, p12]  # Fixed: jsk → jks
```

---

**Error: Insecure HTTP URL**
```
1 validation error for BundleConfig
fetch.0.url
  Value error, Only HTTPS URLs are allowed for security. Use https:// or file:// schemes.
```
**Fix:** Use HTTPS or file:// URLs:
```yaml
fetch:
  - name: mozilla_roots
    type: url
    url: https://curl.se/ca/cacert.pem  # Changed from http:// to https://
```

---

**Error: Reserved name**
```
1 validation error for BundleConfig
bundle_name
  Value error, 'fetch' is a reserved bundle name
```
**Fix:** Use a different name:
```yaml
bundle_name: mozilla-fetch  # Changed from 'fetch'
```

---

**Error: Duplicate names**
```
1 validation error for BundleConfig
  Value error, Duplicate repo names found: internal
```
**Fix:** Ensure all repo and fetch names are unique:
```yaml
repo:
  - name: internal-roots
    include: [sources/internal/roots/]
  - name: internal-intermediates  # Changed from 'internal'
    include: [sources/internal/intermediate/]
```

---

**Error: No sources defined**
```
1 validation error for BundleConfig
  Value error, Bundle must have at least one 'repo' or 'fetch' entry
```
**Fix:** Add at least one source:
```yaml
repo:
  - name: local
    include: [sources/internal/]
```

---

**Error: Missing type-specific field**
```
1 validation error for BundleConfig
fetch.0
  Value error, 'url' is required for fetch type 'url'
```
**Fix:** Add the required field for the fetch type:
```yaml
fetch:
  - name: mozilla
    type: url
    url: https://curl.se/ca/cacert.pem  # Added missing url field
```

---

**Error: Key size too small**
```
1 validation error for DefaultsConfig
filters.minimum_key_size_rsa
  Value error, RSA key size must be at least 1024 bits for security
```
**Fix:** Use minimum required key sizes:
```yaml
filters:
  minimum_key_size_rsa: 2048  # Changed from 512
  minimum_key_size_ecc: 256   # Changed from 128
```

---

**Error: Numeric policy_version**
```
# This is automatically handled - no error!
# The validator converts numeric versions to strings:
metadata:
  policy_version: 1.0  # Automatically converted to "1.0"
```

### Validation Architecture

- **Location:** `bundlecraft/helpers/config_schema.py`
- **Framework:** Pydantic v2 with `ConfigDict` and field validators
- **Validation Points:**
  - Bundle configs: validated in `builder.py` and `fetch.py`
  - Craft configs: validated in `builder.py`
  - Defaults config: validated in `builder.py`
- **Error Handling:** All validation errors are caught and re-raised as `ValueError` with full Pydantic error details
- **Extra Fields:** Allowed via `ConfigDict(extra="allow")` for forward compatibility

### Testing

Comprehensive validation tests are located in `tests/test_config_validation.py` with 30+ test cases covering:
- Missing required fields
- Empty values
- Invalid formats
- Reserved names
- Duplicate names
- Name conflicts
- Security constraints (HTTPS, key sizes)
- Type-specific requirements
- Valid configurations (positive tests)

---

## Security Best Practices

1. **Fetch verification**: Always pin `sha256` for public/static sources (Mozilla)
2. **TLS pinning**: Use `ca_file` and/or `tls_fingerprint_sha256` for API fetches
3. **Secrets**: Never hardcode passwords; always use `*_env` keys to reference environment variables
4. **Distribution**: Use `enabled: false` to disable distribution targets in lower environments
5. **Tags**: Use environment tags to control CI/CD pipeline routing (e.g., only sign/publish `production` tagged envs)
6. **HTTPS enforcement**: The schema automatically rejects insecure HTTP URLs (except localhost)
7. **Key sizes**: Configure minimum key size requirements to enforce cryptographic standards
