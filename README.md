# 🧩 PKI CA Trust — Centralized Trust Store Management

## Overview

**PKI-CA-Trust** provides a configuration-as-code workflow for building, verifying, and distributing certificate **trust bundles** across environments.  
It ingests versioned certificate sources (roots, intermediates, vendor bundles) and produces reproducible multi-format outputs for OS, Java, and app stacks.

**Outputs per build (deterministic):**
- Canonical **PEM** (annotated, deduplicated)
- **PKCS#7 (.p7b)** — DER bundle
- **Java KeyStore (.jks)** — per-cert aliasing
- **PKCS#12 (.p12)** — multi-cert export
- `manifest.json` and `checksums.sha256` for traceability

---

## ✨ Features

- **Reproducible builds** from YAML configs
- **Multi-format export**: PEM, P7B, JKS, P12
- **Cross-format verification**: expiry, empties, count consistency
- **Extensible config model**: defaults → environment → bundle
- **Portable tooling**: Python + `openssl` + `keytool`

---

## 🧱 Architecture

```
sources/        # raw certificate inputs (roots, intermediates, vendor)
config/         # policy and build config (YAML)
  defaults.yaml
  envs/
  bundles/
scripts/        # build, verify, convert CLIs + helpers
  build_trust_store.py
  verify_bundle.py
  convert_format.py
  helpers/
    converters.py
    verifiers.py
    utils.py
build/          # generated outputs (per env/bundle)
```

Each **build** yields a self-contained directory under `build/<env>/<bundle>/` with all formats + manifest + checksums.

---

## ⚙️ Configuration Model

Three layers are merged at runtime:

| Layer | Path | Purpose |
|---|---|---|
| **Defaults** | `config/defaults.yaml` | Global baseline (verification, filters, formats) |
| **Environment** | `config/envs/<env>.yaml` | Execution context (paths, passwords, overrides) |
| **Bundle** | `config/bundles/<bundle>.yaml` | Content definition (what to include/exclude) |

**Example bundle (`config/bundles/internal.yaml`):**
```yaml
id: internal
include:
  - sources/internal/roots/
  - sources/internal/intermediates/
exclude: []
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30
pem:
  include_subject_comments: true
output_formats: ["pem", "p7b", "jks", "p12"]
package: false
```

**Example env (`config/envs/prod.yaml`):**
```yaml
build_path: build/prod/
output_formats: ["pem", "p7b", "jks", "p12"]
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD
    alias_format: "{subject.CN}-{serial}"
  pkcs12:
    password_env: TRUST_P12_PASSWORD
verify:
  fail_on_expired: true
  warn_days_before_expiry: 60
```

---

## 🚀 Quickstart

### 1) Install prerequisites
```bash
pip install pyyaml cryptography click
# System tools:
#   - OpenSSL (openssl)
#   - Java keytool (e.g., openjdk-17-jre-headless)
```

### 2) Build a trust bundle
```bash
python scripts/build_trust_store.py --env prod --bundle internal
```
Produces:
```
build/prod/internal/
 ├─ ca-trust.pem
 ├─ ca-trust.p7b
 ├─ ca-trust.jks
 ├─ ca-trust.p12
 ├─ manifest.json
 └─ checksums.sha256
```

### 3) Verify a bundle (expiry, empties, counts)
```bash
python scripts/verify_bundle.py build/prod/internal/
```
Sample result:
```
[SUMMARY] Verified 2 certificate(s):
          Expired = 0, Expiring Soon = 0, Errors = 0
[INFO] Certificate count summary: {'PEM': 2, 'P7B': 2, 'P12': 2, 'JKS': 2}
[RESULT] ✅ All certificates valid.
```

### 4) Convert PEM ad-hoc (optional)
```bash
# Defaults to safe behavior; uses env vars if set
export TRUST_JKS_PASSWORD="changeit"     # or your secret
export TRUST_P12_PASSWORD="changeit"     # or your secret
python scripts/convert_format.py build/prod/internal/ca-trust.pem build/prod/internal/ jks p12
```

---

## 🔐 Defaults & Conventions

- **Passwords:** fallback to `"changeit"` if `TRUST_JKS_PASSWORD` / `TRUST_P12_PASSWORD` not set
- **JKS Aliases:** default `{subject.CN}-{serial}` (safe characters only)
- **PEM:** includes `# Subject:` comment headers (configurable)
- **JKS rebuilds cleanly:** keystore file removed before import to avoid duplicate aliases
- **P7B/P12 completeness:** generated from the full PEM bundle (not single certs)

---

## 🧪 Verification Details

Checks performed by `scripts/verify_bundle.py`:
- **Expiry**: errors on expired (if configured), warnings on soon-to-expire
- **Empty outputs**: fails on 0-byte `.p7b` / `.p12`
- **Count consistency**: compares cert counts across **PEM / P7B / JKS / P12**

Exit codes:
- `0` — all good
- `1` — warnings only (e.g., expiring soon)
- `5` — fatal (expired, parse error, empty/mismatched outputs)

---

## 🧰 Scripts Reference

| Script | Purpose |
|---|---|
| `scripts/build_trust_store.py` | Orchestrate build from configs; writes all outputs + manifest + checksums |
| `scripts/verify_bundle.py` | Verify PEMs or built bundle directories (expiry + integrity) |
| `scripts/convert_format.py` | Convert canonical PEM → P7B/JKS/P12 (ad-hoc) |

For CLI usage examples and deeper details, see [`scripts/README.md`](scripts/README.md).

---

## 🧭 Troubleshooting

- **Empty P7B**: ensure OpenSSL is installed; tool uses `crl2pkcs7 -certfile` on a temp PEM chain.
- **JKS shows duplicate aliases**: keystore is now nuked per run; re-run build with updated scripts.
- **P12 contains only one cert**: fixed — exporter now uses `-in first` + `-certfile rest`.
- **Verifier says JKS=0**: ensure `keytool` exists on PATH; we parse `Alias name:` and fallback to “contains N entries”.

---

## 🔮 Roadmap

- Chain validation (issuer/subject path building)
- Manifest (`checksums.sha256`) verification step
- Parallelized conversions for speed
- Unified `trustctl` CLI wrapper
- Test suite + CI templates

---

## 📄 License

MIT © 2025
