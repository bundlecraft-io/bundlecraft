# 🏛️ PKI CA Trust — Centralized Certificate Trust Store Management

## Overview

**PKI-CA-Trust** is a configuration-as-code system for building, verifying, and distributing multi-format certificate **trust bundles** across environments.  
It automates the ingestion of versioned certificate sources (roots, intermediates, vendor bundles) and produces reproducible outputs for OS, Java, and application platforms.

**Key Outputs Each Build:**
- Canonical **PEM** bundle (with annotated subjects, deduplication)
- **PKCS#7 (.p7b)** — DER-encoded bundle
- **Java KeyStore (.jks)** — per-cert aliasing, password-protected
- **PKCS#12 (.p12/.pfx)** — multi-cert export, password-protected
- Deterministic **manifest.json** and **checksums.sha256** (traceability)

---

## ✨ Features

- **Reproducible builds** using layered YAML configs
- **Multi-format export:** PEM, P7B, JKS, P12
- **Cross-format verification:** expiry, empties, count consistency
- **Extensible config model:** defaults → environment → bundle
- **Portable tooling:** Python + OpenSSL + Java keytool
- **Manifest and checksum generation:** for auditing and release integrity
- **GPG signing integration** (optional, for release artifacts)
- **CI/CD ready:** Designed for GitHub Actions, supports concurrency and artifact management
- **Flexible bundle and environment definitions**: Easily add new trust bundles or environments

---

## 📁 Repository Structure

```
├── sources/                # Certificate sources (roots, intermediates, vendor, etc.)
├── config/                 # YAML configuration (defaults, environments, bundles)
│   ├── defaults.yaml
│   ├── envs/
│   └── bundles/
├── scripts/                # Python scripts for build, verify, convert, helpers
│   ├── build_trust_store.py
│   ├── verify_bundle.py
│   ├── convert_format.py
│   └── helpers/
│       ├── converters.py
│       ├── verifiers.py
│       ├── utils.py
│       └── __init__.py
├── build/                  # Generated outputs (per environment/bundle)
├── docs/                   # Project documentation
├── .github/
│   └── workflows/
│       └── pki-ca-trust.yaml  # CI/CD pipeline for builds, verification, releases
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── LICENSE                 # MIT License
```

---

## 🏗️ How It Works — Build Pipeline

PKI-CA-Trust uses a **layered configuration model**:

1. **Defaults** (`config/defaults.yaml`):  
   Global settings (verification, filters, formats)

2. **Environment** (`config/envs/<env>.yaml`):  
   Contextual overrides (paths, secrets, output formats)

3. **Bundle** (`config/bundles/<bundle>.yaml`):  
   Content definition (certificate sources to include/exclude)

**Example Build Flow:**

- Discover all bundles and environments in config folders
- For each (env, bundle) pair:
  - Merge configs: defaults ← env ← bundle
  - Deduplicate, filter, and verify certificates
  - Write annotated canonical PEM
  - Convert to P7B, JKS, P12 (using OpenSSL/keytool)
  - Generate manifest and checksums for outputs
  - Package build into tarball if configured
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
build_path: build/example/
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

**Python dependencies:**
```bash
python3 -m pip install -r requirements.txt
```

**System dependencies:**
```bash
# Required for conversions and verification
sudo apt-get install openssl openjdk-17-jre-headless  # (for keytool)
```

### 2. Prepare Certificate Sources

- Place PEM files in appropriate folders under `sources/`
- Update `config/bundles/` YAMLs to specify which sources to include/exclude

### 3. Build a Bundle

```bash
python scripts/build_trust_store.py --env prod --bundle internal
```
- Produces artifacts in `build/prod/internal/`:
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
python scripts/verify_bundle.py build/prod/internal/
```
- Checks:
  - Expiry and soon-to-expire certificates
  - Empty or missing output files
  - Certificate count consistency across all formats

**Exit codes:**
- `0`: Success
- `1`: Warnings (certs expiring soon)
- `5`: Failure (expired certs, parse errors, empty/mismatched outputs)

### 5. Convert PEM Ad-Hoc (if needed)

```bash
python scripts/convert_format.py build/prod/internal/ca-trust.pem build/prod/internal/ jks p12
# Defaults to p7b, jks, p12 if formats not specified
```

- Uses environment variables for passwords:
  - `TRUST_JKS_PASSWORD` (default `"changeit"`)
  - `TRUST_P12_PASSWORD` (default `"changeit"`)

---

## 🔐 Security & Verification

- **Strict Expiry Handling:** Build fails if any cert is expired (unless configured otherwise)
- **Deduplication:** SHA256 fingerprint used for unique certs
- **Subject Annotation:** PEM includes `# Subject:` comments for traceability
- **Manifest & Checksums:** Every build records outputs with SHA256 in both JSON and text formats
- **Cross-format Verification:** Cert counts and file integrity checked for PEM, P7B, JKS, P12

---

## 🧰 Scripts Reference

| Script | Purpose | Example Usage |
|---|---|---|
| `build_trust_store.py` | Build trust bundles from configs, write all outputs | `python scripts/build_trust_store.py --env prod --bundle internal` |
| `verify_bundle.py` | Verify PEMs or built bundle directories (expiry + integrity) | `python scripts/verify_bundle.py build/prod/internal/` |
| `convert_format.py` | Convert canonical PEM to P7B/JKS/P12 (ad-hoc) | `python scripts/convert_format.py build/prod/internal/ca-trust.pem build/prod/internal/ jks p12` |

For more detailed usage and options, see [`scripts/README.md`](scripts/README.md).

---

## 🏭 CI/CD Pipeline

The included [GitHub Actions workflow](.github/workflows/pki-ca-trust.yaml) automates:

- **Build & Verification** for all bundles/environments on push/PR/manual dispatch
- **Artifact Uploads** for all intermediate and final products
- **Release Publication**: Generates release tarballs, optional GPG signing, and release notes
- **Concurrency Control**: Ensures only one pipeline per branch at a time

**Manual trigger:**  
You can dispatch builds from the Actions tab for custom scenarios.

---

## 📝 Documentation

- **Full docs:** [`docs/README.md`](docs/README.md)
- **Scripts reference:** [`scripts/README.md`](scripts/README.md)
- **Design, architecture, config details:** See [`docs/`](docs/)

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
- Unified `trustctl` CLI wrapper
- Test suite + CI templates
- Dynamic certificate fetching from committed trusted sources (i.e. KeyFactor collection, Mozilla public bundle, etc) upon build

---

## ⏳ Release & Signing

- **Release artifacts** are published automatically via GitHub Actions.
- **GPG signing** is supported if a key is provided via GitHub Secrets.
- **Verification instructions** are included in release notes:
  ```bash
  curl -O https://raw.githubusercontent.com/KunaiX/pki-ca-trust/main/docs/public-gpg-key.asc
  gpg --import public-gpg-key.asc
  gpg --verify truststore_bundle.tar.gz.asc truststore_bundle.tar.gz
  ```

---

## 🧪 Development Tips

- Run `verify_bundle.py` after each build to validate outputs and manifest.
- Use `convert_format.py` directly for ad-hoc conversions or tests.
- To debug OpenSSL or keytool output, temporarily add `check=False` to subprocess calls.
- Passwords default to `"changeit"` for local testing; override via environment variables in CI.

---

## 📄 License

MIT © 2025 - [KunaiX](https://github.com/KunaiX)

---

## 🤝 Contributing

- Issues and PRs are welcome!  
- Please ensure all changes are reflected in relevant docs in [`docs/`](docs/).
- For major changes, propose in a GitHub Discussion.

---

## 🏷️ Tags & Metadata

- **Category:** PKI, Certificate Management, DevOps, Security Automation
- **Status:** Stable, actively maintained
- **Contact:** `pki-team@example.com` (see config metadata)

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

Open an [issue](https://github.com/KunaiX/pki-ca-trust/issues)  
or reach out via [GitHub Discussions](https://github.com/KunaiX/pki-ca-trust/discussions)
