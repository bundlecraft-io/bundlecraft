# 🔐 BundleCraft — Modern PKI Trust Store Builder

## Overview

![GitHub license](https://img.shields.io/github/license/chrisjpich/bundlecraft)
![GitHub release](https://img.shields.io/github/v/release/chrisjpich/bundlecraft)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/chrisjpich/bundlecraft/bundlecraft.yml)

---

## Overview

**BundleCraft** is a modern, configuration-as-code system for **building, verifying, and distributing multi-format certificate trust bundles** across environments.
It automates the ingestion of versioned certificate sources (roots, intermediates, vendor bundles) and produces reproducible, auditable outputs for OS, Java, and application platforms.

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
├── config/                 # YAML configuration (defaults, environments, bundles)
│   ├── defaults.yaml
│   ├── envs/
│   └── bundles/
├── bundlecraft/            # Python scripts for build, verify, convert, helpers
├── dist/                   # Generated outputs (per environment/bundle)
├── docs/                   # Project documentation
├── .github/
│   └── workflows/
│       └── bundlecraft.yaml  # CI/CD pipeline for builds, verification, releases
├── pyproject.toml        # Project metadata and dependencies
├── README.md               # This file
└── LICENSE                 # MIT License
```

---

## 🏗️ How It Works — Build Pipeline

BundleCraft uses a **layered configuration model**:

1. **Defaults** (`config/defaults.yaml`):
   Global settings (verification, filters, formats)

2. **Environment** (`config/envs/<env>.yaml`):
   Contextual overrides (paths, secrets, output formats)

3. **Bundle** (`config/bundles/<bundle>.yaml`):
   Content definition (certificate sources to include/exclude)

**Build Flow:**

- Merge config layers: defaults ← env ← bundle
- Deduplicate, verify, and annotate certs
- Generate canonical PEM bundle
- Convert to JKS, P7B, P12
- Generate `manifest.json` and `checksums.sha256`
- Package build into `.tar.gz` tarball if configured
- Verify all outputs and cross-format consistency
- Optionally sign and publish release artifacts

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

### Environment Config (`config/envs/*.yaml`)

Defines **how** bundles are built in a specific context, including secrets, output path, global filters, and format behavior.

```yaml
name: Example Environment
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
  contact: security-team@example.com
  policy_version: 1.0
```

### Defaults (`config/defaults.yaml`)

Baseline settings for verification, filters, output formats, and metadata.
These can be overridden by environment or bundle configs.

---

## 🚀 Quickstart — Building and Verifying Trust Bundles

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

### 3. Build a Bundle

```bash
bundlecraft build --env prod --bundle internal
```
- Produces artifacts in `dist/prod/internal/`:
  ```
  ca-trust.pem
  ca-trust.p7b
  ca-trust.jks
  ca-trust.p12
  manifest.json
  checksums.sha256
  package.tar.gz  # if enabled
  ```

### 4. Verify Outputs

```bash
bundlecraft verify --target dist/prod/internal --verbose --verify-all
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
- **Optional GPG signing:** secure release integrity for distributed bundles in GitHub workflow

---

## 🧰 Scripts Reference

|Script|Purpose|Example Usage|
|---|---|---|
| `bundlecraft.builder` (CLI: `bundlecraft build`) | Build trust bundles from configs, write all outputs | `bundlecraft build --env prod --bundle internal` |
| `bundlecraft.verifier` (CLI: `bundlecraft verify`) | Verify PEMs or built bundle directories (expiry + integrity) | `bundlecraft verify dist/prod/internal/` |
| `bundlecraft.converter` (CLI: `bundlecraft convert`) | Convert any supported input to any supported output (PEM, P7B, JKS, P12, ZIP) | `bundlecraft convert --input dist/prod/internal/ca-trust.pem --output-dir dist/prod/internal/ --output-format jks` |

For more detailed usage and options, see [`bundlecraft/README.md`](bundlecraft/README.md).

---

## 🏭 CI/CD Pipeline

The included [GitHub Actions workflow](.github/workflows/bundlecraft.yaml) automates:

- **Build & Verification** for all bundles/environments on push/PR/manual dispatch
- **Artifact Uploads** for all intermediate and final products
- **Release Publication**: Generates release tarballs, optional GPG signing, and release notes
- **Concurrency Control**: Ensures only one pipeline per branch at a time

**Manual trigger:**
You can dispatch builds from the Actions tab for custom scenarios.

---

## 📝 Documentation

- **CLI reference:** [`bundlecraft/README.md`](bundlecraft/README.md)
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

---

## 🔮 Roadmap & Future Enhancements

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
bundlecraft convert --input ca-trust.pem --output-dir ./ --output-format jks

# Build with packaging
bundlecraft build --env prod --bundle internal --package

# Force overwrite during conversion
bundlecraft convert --input ca-trust.der --output-dir ./ --output-format pem --force
```

### Configuration Files

- `config/defaults.yaml` - Global baseline settings
- `config/envs/*.yaml` - Environment-specific configs (dev, qa, prod)
- `config/bundles/*.yaml` - Bundle definitions (what certs to include)

### Output Artifacts

Every build produces:
- `ca-trust.pem` - Canonical PEM bundle
- `ca-trust.p7b` - PKCS#7 binary bundle
- `ca-trust.jks` - Java KeyStore
- `ca-trust.p12` - PKCS#12 bundle
- `manifest.json` - Build metadata
- `checksums.sha256` - File integrity hashes
- `package.tar.gz` - Complete bundle archive (if `--package` used)

---

## �📄 License

MIT © 2025 - [chrisjpich](https://github.com/chrisjpich)

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
