# 🔐 BundleCraft — Modern PKI Trust Store Builder

## Overview

![GitHub license](https://img.shields.io/github/license/bundlecraft-io/bundlecraft)
![GitHub release](https://img.shields.io/github/v/release/bundlecraft-io/bundlecraft)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/bundlecraft-io/bundlecraft/bundlecraft.yaml)

---

## Overview

**BundleCraft** is a modern, configuration-as-code system for **fetching, building, verifying, and distributing multi-format certificate trust bundles** across environments.
It securely sources certificate material from trusted remote origins or local files, then produces reproducible, auditable outputs for OS, Java, and application platforms.

> **In short:** BundleCraft lets you define *how trust is built* — not just *what to trust*.

---

## 🎯 Problems Solved

Managing certificate trust stores at scale is notoriously difficult. BundleCraft addresses the key pain points:

### 📝 **Manual, Error-Prone Trust Management**

- **Problem:** Teams manually copy/paste PEMs, run OpenSSL commands, and maintain separate keystores for different platforms. One wrong cert = outages.
- **Solution:** Single source of truth with versioned configs. Build once, export to all formats (PEM, JKS, P12, P7B, ZIP) automatically.

### 🔄 **Format Fragmentation**

- **Problem:** Java needs JKS, Windows/IIS wants P12, Linux/Apache uses PEM, legacy systems require P7B. Keeping them synchronized is a nightmare.
- **Solution:** Universal converter that maintains certificate integrity across all formats. No more "works in dev, breaks in prod" due to format issues.

### 🚨 **Expired Certificate Surprises**

- **Problem:** Certs expire silently. No one knows until production fails at 3 AM.
- **Solution:** Built-in expiry validation with configurable warning thresholds. Fail builds early, prevent runtime disasters.

### 🏢 **Environment-Specific Trust Requirements**

- **Problem:** Dev needs test CAs, QA needs staging roots, Prod requires only production-approved CAs. Managing this across teams is chaos.
- **Solution:** Layered configuration model (defaults → environment → bundle) keeps trust policies explicit and environment-aware.

### 🔍 **Zero Auditability**

- **Problem:** "Who added this cert? When? Why?" No one knows. Compliance nightmares during audits.
- **Solution:** Every build produces manifest.json with full provenance, checksums.sha256 for integrity, and optional GPG signatures. Complete audit trail.

### 🔁 **Non-Reproducible Builds**

- **Problem:** "It works on my machine" but fails in CI. Different Python versions, missing tools, inconsistent outputs.
- **Solution:** Configuration-as-code with deterministic builds. Same inputs = same outputs, every time. Perfect for GitOps workflows.

**Key Outputs Each Build:**

- Canonical **PEM** bundle (with annotated subjects, deduplication)
- **PKCS#7 (.p7b)** — DER-encoded bundle
- **Java KeyStore (.jks)** — per-cert aliasing, password-protected
- **PKCS#12 (.p12/.pfx)** — multi-cert export, password-protected
- **ZIP** (tarball of PEMs, one per cert)
- Deterministic **manifest.json** and **checksums.sha256** (traceability)

---

## ✨ Features

- **Trusted Fetch layer**: Securely fetch certificates from HTTPS, APIs, and Vault with CA/fingerprint/sha256 pinning; staging-only (no cache) and full provenance.
- **Reproducible builds** using layered YAML configs
- **Multi-format export:** PEM, P7B, JKS, P12, ZIP
- **Cross-format verification:** expiry, empties, count consistency
- **Extensible config model:** defaults → environment → bundle
- **Portable tooling:** Python + OpenSSL + Java keytool
- **Manifest and checksum generation:** for auditing and release integrity
- **GPG signing integration** (optional, for release artifacts)
- **CI/CD ready:** Designed for (but not exclusive to) GitHub Actions, supports concurrency and artifact management
- **Flexible bundle and environment definitions**: Easily add new trust bundles or environments

---

## 📁 Repository Structure

```
├── sources/                # Certificate sources (roots, intermediates, vendor, etc.)
├── config/                 # YAML configuration (defaults, crafts, bundles)
│   ├── defaults.yaml
│   ├── crafts/
│   └── bundles/
├── bundlecraft/            # Python scripts for build, verify, convert, helpers
├── dist/                   # Generated outputs (per craft/target)
├── docs/                   # Project documentation
├── .github/
│   └── workflows/
│       └── bundlecraft.yaml  # CI/CD pipeline for builds, verification, releases
├── pyproject.toml        # Project metadata and dependencies
├── README.md               # This file
└── LICENSE                 # MIT License
```

---

## 🏗️ How It Works — Pipeline

BundleCraft uses a **layered configuration model** and a four-stage pipeline:

fetch → build → verify → convert (CI orchestrates discover → build → collect → verify → publish)

1. **Defaults** (`config/defaults.yaml`):
   Global settings (verification, filters, formats)

2. **Craft** (`config/crafts/<craft>.yaml`):
  Contextual overrides (paths, secrets, output formats, targets)

3. **Bundle** (`config/bundles/<bundle>.yaml`):
   Content definition (certificate sources to include/exclude)

4. **Fetch (optional but recommended)** (`fetch:` in bundle):
  Securely fetch and stage certificates from trusted remote origins into `sources/fetched/<env>/<bundle>/`. Staging is cleaned each run; no persistent cache.

**Flow:**

- Merge config layers: defaults ← env ← bundle
- If `fetch:` is present, securely stage remote sources under `sources/fetched/<env>/<bundle>/` with provenance
- Deduplicate, verify, and annotate certs
- Generate canonical PEM bundle
- Convert to JKS, P7B, P12
- Generate `manifest.json` and `checksums.sha256`
- Package build into `.tar.gz` tarball if configured
- Verify all outputs and cross-format consistency
- Optionally sign and publish release artifacts

### Craft composition (merge bundles per craft)

Environments can define composed target bundles that merge one or more base bundles.

In `config/crafts/dev.yaml`:

```yaml
targets:
  internal-dev:
    includes: [internal, mozilla]
  mozilla:
    includes: [mozilla]
```

Commands:

```bash
# Build the composed target (composed from bundles)
bundlecraft build --craft dev --bundle internal-dev

# Build one target from a production craft
bundlecraft build --craft prod --bundle mozilla
```

Outputs:

- `dist/Development/internal-dev/` contains both internal and mozilla certs (craft display name)
- `dist/Production/mozilla/` contains only mozilla certs

---

## 📦 Configuration Deep Dive

### Bundle Config (`config/bundles/*.yaml`)

Defines **what** certificates go into a bundle, filters, output formats, and per-format overrides.

```yaml
id: internal
description: Trust bundle for internal PKI services
include:
  - sources/internal/rootCA.pem
  - sources/internal/issuingCA1.pem
exclude: []
output_formats:
  - pem
  - jks
  - p7b
  - p12
pem:
  include_subject_comments: true
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30
package: true  # produce package.tar.gz
```

### Craft Config (`config/crafts/*.yaml`)

Defines **how** bundles are built in a specific context, including secrets, output path, global filters, and format behavior.

```yaml
name: Example Craft
build_path: dist/example/
package: false
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30
output_formats:
  - pem
  - p7b
  - jks
  - p12
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD
    alias_format: "{subject.CN}-{serial}"
  pkcs12:
    password_env: TRUST_P12_PASSWORD
filters:
  unique_by_fingerprint: true
  not_expired_only: true
  ca_certs_only: true
metadata:
  contact: security@bundlecraft.io
  policy_version: 1.0
```

### Defaults (`config/defaults.yaml`)

Baseline settings for verification, filters, output formats, and metadata.
These can be overridden by environment or bundle configs.

---

## 🚀 Quickstart — Fetching, Building, and Verifying Trust Bundles

### 1. Install Prerequisites

**System dependencies:**

```bash
# Required for conversions and verification
sudo apt-get install openssl openjdk-17-jre-headless  # (for keytool)
```

**Python dependencies:**

```bash
# Install with runtime dependencies
pip install -e .

# Or install with dev/test tools
pip install -e ".[dev]"
```

**Shell completion (optional):**

```bash
# Bash - add to ~/.bashrc for persistence
eval "$(_BUNDLECRAFT_COMPLETE=bash_source bundlecraft)"

# Zsh - add to ~/.zshrc for persistence
eval "$(_BUNDLECRAFT_COMPLETE=zsh_source bundlecraft)"
```

### 2. Prepare Certificate Sources

- Place PEM files in appropriate folders under `sources/`
- Update `config/bundles/` YAMLs to specify which sources to include/exclude
- Optionally add a `fetch:` section to stage certificates from trusted remote origins (HTTPS/API/Vault)

### 3. Fetch and Build

```bash
# Build a craft target (fetch is done automatically unless skipped)
```bash
bundlecraft build --craft prod --bundle internal-prod
```

```
- Produces artifacts in `dist/Production/internal-prod/`:

  ```text
  bundlecraft-ca-trust.pem
  bundlecraft-ca-trust.p7b
  bundlecraft-ca-trust.jks
  bundlecraft-ca-trust.p12
  manifest.json
  checksums.sha256
  package.tar.gz  # if enabled
  ```

### 4. Verify Outputs

```bash
bundlecraft verify --target dist/Production/internal-prod --verbose --verify-all
```

- Checks:
  - Expiry and soon-to-expire certificates
  - Empty or missing output files
  - Certificate count consistency across all formats

**Exit codes:**

- `0`: Success
- `1`: Warnings (certs expiring soon)
- `5`: Failure (expired certs, parse errors, empty/mismatched outputs)

### 5. Convert Bundles Ad-Hoc (if needed)

```bash
# Convert DER to PEM
bundlecraft convert --input sources/internal/rootCA.der --output-dir ./ --output-format pem

# Convert to P7B
bundlecraft convert --input sources/internal/rootCA.pem --output-dir ./ --output-format p7b

# Convert to ZIP (tarball of PEMs)
bundlecraft convert --input sources/internal/rootCA.pem --output-dir ./ --output-format zip
```

- Produces artifact in the output directory as `bundlecraft-ca-trust.{format}`
- Uses environment variables (or CLI option) for passwords:
  - `TRUST_JKS_PASSWORD` (default `"changeit"`)
  - `TRUST_P12_PASSWORD` (default `"changeit"`)

---

## ⚙️ Environment Variables

BundleCraft supports the following environment variables for configuration:

| Variable               | Purpose                                       | Default Value  | Used By          |
|------------------------|-----------------------------------------------|----------------|------------------|
| `TRUST_JKS_PASSWORD`   | Password for Java KeyStore operations         | `"changeit"`   | Convert, Verify  |
| `TRUST_P12_PASSWORD`   | Password for PKCS#12 operations               | `"changeit"`   | Convert, Verify  |

**Note:** These are used as fallback values. You can override them via CLI options or config files.

---

## 🔐 Security & Verification

- **Strict Expiry Handling:** Build fails if any cert is expired (unless configured otherwise)
- **Deduplication:** SHA256 fingerprint used for unique certs
- **Subject Annotation:** PEM includes `# Subject:` comments for traceability
- **Manifest & Checksums:** Every build records outputs with SHA256 in both JSON and text formats
- **Cross-format Verification:** Cert counts and file integrity checked for PEM, P7B, JKS, P12
- **Fetch provenance:** `provenance.fetch.json` recorded in staging and embedded into `manifest.json` under `fetched`
- **Network trust controls:** HTTPS only (for APIs and URLs), optional custom CA, optional TLS leaf fingerprint pinning, and optional content `sha256` pinning
- **Optional GPG signing:** secure release integrity for distributed bundles in GitHub workflow

---

## 🧰 Scripts Reference

|Script|Purpose|Example Usage|
|---|---|---|
| `bundlecraft.fetch` (CLI: `bundlecraft fetch`) | Securely fetch remote sources and stage them (no persistent cache) | `bundlecraft fetch --env prod --bundle internal` |
| `bundlecraft.builder` (CLI: `bundlecraft build`) | Build trust bundles from configs, write all outputs | `bundlecraft build --craft prod --bundle internal-prod` |
| `bundlecraft.verifier` (CLI: `bundlecraft verify`) | Verify PEMs or built bundle directories (expiry + integrity) | `bundlecraft verify dist/prod/internal/` |
| `bundlecraft.converter` (CLI: `bundlecraft convert`) | Convert any supported input to any supported output (PEM, P7B, JKS, P12, ZIP) | `bundlecraft convert --input dist/prod/internal/bundlecraft-ca-trust.pem --output-dir dist/prod/internal/ --output-format jks` |

For more detailed usage and options, see [`bundlecraft/README.md`](bundlecraft/README.md).

---

## 📐 Trust Matrix (Envs × Bundles)

The release pipeline now publishes a trust matrix that shows which crafts (rows) trust which bundles (columns), derived from `config/crafts/*.yaml` composition (`targets.<name>.includes`).

Artifacts attached to releases:

- `TRUST_MATRIX.md` — Markdown table (human-readable)
- `trust-matrix.json` — Structured JSON (machine-readable)

Generate locally:

```bash
# Table (terminal)
python scripts/trust_matrix.py --config-dir config --format table

# Markdown
python scripts/trust_matrix.py --config-dir config --format markdown --output TRUST_MATRIX.md

# JSON
python scripts/trust_matrix.py --config-dir config --format json --output trust-matrix.json
```

Notes:

- Trust for an environment is the union of all bundles included by its targets
- Legacy `bundle_targets: [...]` is also supported and treated as trusted bundles

---

## 🏭 CI/CD Pipeline

The included workflows automate builds and fetch tests:

- [bundlecraft.yaml](.github/workflows/bundlecraft.yaml): Build/verify/publish
- [test-bundlecraft-fetch.yaml](.github/workflows/test-bundlecraft-fetch.yaml): Fetch test suite (Vault, HTTP, API)

- Discover → Build → Collect → Verify → Publish
- Build per-craft “targets” declared in `config/crafts/<env>.yaml` under `targets:` (composition-aware)
- For each target, the job runs `bundlecraft build --prefetch` and respects `build_path` via `--output-root`
- Uploads artifacts per target using the naming `trust-store-<env>-<target>`
- Optionally signs and publishes a release tarball
- Concurrency: only one pipeline per branch at a time

Notes:

- Prefer declaring composed targets in env files (for example: `internal-dev` includes `[internal, mozilla]`).
- If you want bundles to build offline, pre-stage with `bundlecraft fetch` in a connected job, then run build with `--offline`.

Test server used in CI:

- HTTP and API fetch tests start `scripts/test-server-local.py` on port 8443, then trust the ephemeral CA at `<data_dir>/server.crt`.
- The script prints the data dir path and stores it at `/tmp/test-server-local-latest` to make CI trust setup easy.

More details in [`scripts/README.md`](scripts/README.md).

Manual trigger:
You can dispatch builds from the Actions tab for custom scenarios.

When triggering manually, you can optionally filter environments:

- Input: environments (comma-separated), e.g. `dev,qa`
- Default: empty = build all environments
- The workflow prints a selection summary (selected, available, filtered, target count)
- Validation: unknown environments or an empty result after filtering will fail fast with a clear error

---

## 📝 Documentation

- **CLI reference:** [`bundlecraft/README.md`](bundlecraft/README.md)
- **Configuration spec:** [`docs/CONFIG-SPEC.md`](docs/CONFIG-SPEC.md)
- **Contributing guide:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Security policy:** [`SECURITY.md`](SECURITY.md)
- **Test documentation:** [`tests/README.md`](tests/README.md)
- **Architecture decisions:** [`docs/`](docs/) (ADRs)

---

## 📊 Performance & Limitations

### Known Limitations

- **Certificate Formats**: Only X.509 certificates are supported
- **Private Keys**: Explicitly NOT supported (certs and public keys only)
- **Certificate Chains**: No automatic chain building or validation (yet)
- **Revocation**: No CRL or OCSP checking (verification is signature + expiry only)
- **Binary Executables**: Requires `openssl` and `keytool` in PATH for some operations
- **Concurrent Builds**: Safe for parallel CI jobs; no shared state

### Best Practices

- Keep bundles focused (< 200 certs recommended for performance)
- Use ZIP format for distributing individual certificates
- Run verification in CI to catch expiry issues early
- Pin dependencies in production pipelines

---

## 🧭 Troubleshooting & FAQ

- **Empty P7B?**
  Ensure OpenSSL is installed and available on PATH. The tool uses `crl2pkcs7 -certfile` for conversion.

- **Duplicate JKS aliases?**
  The build script removes existing keystore before import. Ensure the latest version is used.

- **P12 only contains one cert?**
  Fixed in exporter — uses `-in first` + `-certfile rest` for completeness.

- **Verifier says JKS=0?**
  Ensure `keytool` is installed and on PATH. The script parses `Alias name:` and certificate blocks.

- **Password issues?**
  Default passwords are `"changeit"` for both JKS and P12. Set env vars for production.

- **Fetch: Insecure HTTP rejected**
  Use only `https://` (or `file://` for local). For APIs, configure `verify.ca_file` and optionally `verify.tls_fingerprint_sha256`.

- **Fetch: SHA256 mismatch**
  Update the expected `verify.sha256` to the authoritative value, or investigate source changes before proceeding.

- **Fetch: TLS fingerprint mismatch**
  Re-check the server certificate fingerprint (leaf). If it rotated legitimately, update `verify.tls_fingerprint_sha256`.

- **Vault: hvac not installed**
  Install optional extras: `pip install -e .[fetchers]`.

- **Offline builds**
  `bundlecraft build --offline` fails if `fetch:` is present (by design). Pre-stage with `bundlecraft fetch` in connected environments, then commit or package the staged inputs.

See also: [Troubleshooting Guide](docs/troubleshooting.md)

---

## 🔮 Philosophy, Best Practices, and Roadmap

### Philosophy: BundleCraft as a trusted middleman

BundleCraft’s Fetch layer treats remote origins as configurable, auditable trust sources. You decide what to fetch, from where, and under which verification policies. BundleCraft enforces those policies and records provenance so downstream systems can trust the process as much as the result.

Core principles:

- Opt-in remote trust: nothing is fetched unless declared in `fetch:`
- Defense in depth: HTTPS + CA pin + TLS fingerprint pin + optional `sha256` content pin
- No persistence: staging-only, cleaned per run; no hidden caches
- Offline-friendly: builds can run offline if inputs are pre-staged or committed
- Full provenance: every staged artifact is recorded and embedded in build manifests

### Common usage patterns

- Mozilla CA bundle (public roots):

  ```yaml
  fetch:
    - name: mozilla_roots
      type: url
      url: https://curl.se/ca/cacert.pem
      verify:
        sha256: <expected_sha256>
  ```

- Keyfactor collection (generic API):

  ```yaml
  fetch:
    - name: keyfactor_trusted
      type: api
      provider: keyfactor
      endpoint: https://pki.example.com/api/v1/collections/trusted
      token_ref: KEYFACTOR_TOKEN
      verify:
        ca_file: config/certs/pki-ca.pem
        tls_fingerprint_sha256: <leaf_fp>
  ```

- Vault KV (internal roots):

  ```yaml
  fetch:
    - name: internal_roots
      type: vault
      mount_point: secret
      path: pki/trusted_roots
      pem_field: pem
      addr: https://vault.example.com:8200
      token_ref: VAULT_TOKEN
      verify:
        ca_file: config/certs/vault-ca.pem
  ```

Best config practices:

- Always use HTTPS; never `http://`
- Pin content (`verify.sha256`) for static/public bundles when possible (e.g., Mozilla)
- For APIs/services, prefer TLS CA pinning and optionally leaf fingerprint pinning during rollout windows
- Keep tokens in env vars (`*_TOKEN`) and never in YAML
- Commit sample configs but not secrets; use CI secret stores for tokens
- Treat `sources/fetched/` as ephemeral; do not rely on it as a cache

- Chain validation (issuer/subject path building)
- Test suite + CI templates
- Dynamic certificate fetching from committed trusted sources (i.e. KeyFactor collection, Mozilla public bundle, etc) upon build

---

## ⏳ Release & Signing

- **Release artifacts** are published automatically via GitHub Actions.
- **GPG signing** is supported if a key is provided via GitHub Secrets.
- **Verification instructions** are included in release notes:

  ```bash
  curl -O https://raw.githubusercontent.com/chrisjpich/bundlecraft/main/docs/public-gpg-key.asc
  gpg --import public-gpg-key.asc
  gpg --verify truststore_bundle.tar.gz.asc truststore_bundle.tar.gz
  ```

---

## 🧪 Development Tips

- Run `verifier.py` after each build to validate outputs and manifest.
- Use `converter.py` directly for ad-hoc conversions or tests.
- To debug OpenSSL or keytool output, temporarily add `check=False` to subprocess calls.
- Passwords default to `"changeit"` for local testing; override via environment variables in CI.

---

## � Quick Reference

### Common Commands

```bash
# Build a bundle
bundlecraft build --env prod --bundle internal

# Verify a bundle
bundlecraft verify --target dist/prod/internal --verify-all

# Convert formats
bundlecraft convert --input bundlecraft-ca-trust.pem --output-dir ./ --output-format jks

# Build with packaging
bundlecraft build --env prod --bundle internal --package

# Force overwrite during conversion
bundlecraft convert --input bundlecraft-ca-trust.der --output-dir ./ --output-format pem --force
```

### Configuration Files

- `config/defaults.yaml` - Global baseline settings
- `config/crafts/*.yaml` - Craft-specific configs (dev, qa, prod)
- `config/bundles/*.yaml` - Bundle definitions (what certs to include)

### Output Artifacts

Every build produces:

- `bundlecraft-ca-trust.pem` - Canonical PEM bundle
- `bundlecraft-ca-trust.p7b` - PKCS#7 binary bundle
- `bundlecraft-ca-trust.jks` - Java KeyStore
- `bundlecraft-ca-trust.p12` - PKCS#12 bundle
- `manifest.json` - Build metadata
- `checksums.sha256` - File integrity hashes
- `package.tar.gz` - Complete bundle archive (if `--package` used)

---

## 🤝 Contributing

- Issues and PRs are welcome!
- Please ensure all changes are reflected in relevant docs in [`docs/`](docs/).
- For major changes, propose in a GitHub Discussion.

---

## 🏷️ Tags & Metadata

- **Category:** PKI, Certificate Management, DevOps, Security Automation

---

## 🔗 Related Projects & References

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Java Keytool Documentation](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/keytool.html)
- [PKI Concepts](https://en.wikipedia.org/wiki/Public_key_infrastructure)

---

## 🙏 Acknowledgements

Certificates are easy. Certificate management is hard.

Special thanks to all the security and infrastructure teams out there, whose collective experience and guidance has fueled this project.

---

## 📣 Questions?

Open an [issue](https://github.com/chrisjpich/bundlecraft/issues)
or reach out via [GitHub Discussions](https://github.com/chrisjpich/bundlecraft/discussions)

---

© 2025 Chris J Pich
Licensed under the [MIT License](./LICENSE).

> Made with ❤️ (and ☕) for anyone who’s ever debugged a broken trust chain.
> BundleCraft is a passion project, built to make certificate trust a little less painful for everyone.
> Contributions, ideas, and curiosity are always welcome.
