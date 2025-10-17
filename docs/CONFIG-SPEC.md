# BundleCraft Configuration Specification (ENV + BUNDLE)

This document defines the supported configuration schema for BundleCraft. It covers:

- Defaults (config/defaults.yaml)
- Environments (config/envs/*.yaml)
- Bundles (config/bundles/*.yaml)
- Fetch entries (staging-only, no persistent cache)

Merging order: defaults ← environment ← bundle. For composed targets (env.targets), multiple base bundle configs are merged as described below.

---

## 1) Defaults: `config/defaults.yaml`

Applied first; provides safe, global defaults.

Keys:
- output_formats: ["pem", "p7b", "jks", "p12"]
- verify:
  - fail_on_expired: bool (default true)
  - warn_days_before_expiry: int (days, default 30)
- package: bool (default false)
- pem:
  - include_subject_comments: bool (default true)
- filters:
  - unique_by_fingerprint: bool (default true)
  - not_expired_only: bool (default true)
  - ca_certs_only: bool (default true)
- format_overrides:
  - jks:
    - alias_format: string (default "{subject.CN}-{serial}")
  - pkcs12:
    - filename: string (optional)
  - pem:
    - include_subject_comments: bool (reinforces default)
- metadata: free-form object (optional)

Notes:
- Defaults are not required. Any missing keys fall back to built-in defaults.

---

## 2) Environment: `config/envs/<env>.yaml`

Defines how bundles are built/merged for a given environment.

High-importance keys:
- targets: map of target bundle name → composition
  - <target>:
    - includes: [bundleName, ...]  (list of base bundles to merge)
    - (reserved for future: exclude, extra include)
- output_formats: list (overrides defaults)
- verify: same shape as defaults.verify
- filters: same shape as defaults.filters
- format_overrides:
  - jks:
    - storepass_env: ENV_VAR_NAME (read from environment; default TRUST_JKS_PASSWORD)
    - alias_format: string
  - pkcs12:
    - password_env: ENV_VAR_NAME (default TRUST_P12_PASSWORD)
    - alias_format: string
  - force: bool (overwrite outputs when true)
- metadata: { name, contact, policy_version, ... } (optional)

Deprecated/Reserved:
- build_path: reserved (not currently consumed). Use CLI `--output-root` instead.
- publish_targets: reserved (not consumed by the builder).

Example:
```yaml
name: Dev
targets:
  internal-dev:
    includes: [internal, mozilla]
  mozilla:
    includes: [mozilla]
output_formats: [pem, p7b, jks, p12]
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD
  pkcs12:
    password_env: TRUST_P12_PASSWORD
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30
filters:
  unique_by_fingerprint: true
  not_expired_only: true
  ca_certs_only: true
```

Composition semantics:
- For `bundlecraft build --env <env> --bundle <target>`:
  - If `<target>` is in `env.targets`, the builder merges sources from each base bundle in `includes`.
  - Staged fetch sources for each base bundle (under `sources/fetched/<env>/<base>`) are included automatically if present.
  - The builder also loads each base bundle’s own include/exclude lists and merges them.
  - If a `config/bundles/<target>.yaml` file exists, its include/exclude are also honored as additional inputs.

---

## 3) Bundle: `config/bundles/<bundle>.yaml`

Defines what to include in a bundle and how to produce outputs (content, not environment policies).

High-importance keys:
- id: string (logical id; optional for naming)
- name: string (optional descriptive name)
- description: string (optional)
- include: [paths...] (files or directories, relative to repo root)
- exclude: [paths...] (optional)
- output_formats: list (e.g., [pem, p7b, jks, p12])
- package: bool (whether to create a .tar.gz)
- fetch: list of remote source declarations (see section 4)

Other keys:
- pem: { include_subject_comments: bool }
- verify: { fail_on_expired: bool, warn_days_before_expiry: int }
- filters: same shape as defaults.filters
- format_overrides: same shape as env.format_overrides (bundle-scoped tweaks)
- metadata: free-form object

Example:
```yaml
id: mozilla
include: []
output_formats: [pem, p7b]
fetch:
  - name: mozilla_roots
    type: url
    url: https://curl.se/ca/cacert.pem
    verify:
      sha256: <expected_sha256>
```

---

## 4) Fetch entries (staging-only)

Fetched artifacts are staged under `sources/fetched/<env>/<bundle>/` and cleaned each run; no persistent cache is kept. Provenance is written to `provenance.fetch.json` and embedded into the build manifest.

Supported types:

1) type: url
- url: https://... or file://...
- verify (optional):
  - sha256: hex string
  - ca_file: path to custom CA PEM bundle for TLS verification
  - tls_fingerprint_sha256: pin leaf certificate fingerprint (hex)

2) type: api
- endpoint: https://... (HTTPS required)
- provider: string (hint; optional)
- token_ref: ENV_VAR_NAME (Bearer token read from env)
- verify (optional):
  - ca_file: custom CA PEM bundle
  - tls_fingerprint_sha256: leaf fingerprint pin
  - headers: map of additional headers

3) type: vault
- mount_point: string (e.g., "secret")
- path: secret path under the mount (e.g., "pki/trusted_roots")
- pem_field: field name containing PEM text (default "pem")
- addr: Vault address (defaults to VAULT_ADDR)
- token_ref: ENV_VAR_NAME (defaults to VAULT_TOKEN)
- namespace: optional
- verify (optional):
  - ca_file: path to custom CA PEM bundle

Offline mode:
- `bundlecraft fetch --offline` fails if `fetch` is present.
- `bundlecraft build --offline` also fails if fetch is required; pre-stage in connected environments and commit/package inputs.

Security posture:
- HTTPS required for remote endpoints; `http://` is rejected.
- Optional CA pinning and leaf fingerprint pinning for defense in depth.
- Optional content `sha256` pin for static/public sources (recommended for Mozilla).

---

## 5) Precedence and overrides

1. Defaults → Environment → Bundle
   - Later layers override earlier ones for common keys (e.g., output_formats).
2. Composition uses the environment’s `targets.<target>.includes` list to gather base bundle sources.
3. Staged fetched sources are automatically included for each base bundle when present.

---

## 6) CLI notes

- Fetch first (optional): `bundlecraft fetch --env <env> --bundle <bundle>`
- Build composed targets: `bundlecraft build --env <env> --bundle <target> --prefetch`
- Offline build: `bundlecraft build --env <env> --bundle <target> --offline` (fails if fetch is required)

---

## 7) Reserved / not currently consumed

- Environment:
  - build_path (use CLI `--output-root` instead)
  - publish_targets (may be implemented by a publishing step in the future)
