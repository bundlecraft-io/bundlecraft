# 🧰 Scripts Overview — PKI CA Trust

## Purpose

This folder contains all executable scripts and helper modules that power the PKI‑CA‑Trust build system.  
Each script is designed to be modular and reusable both from CI/CD pipelines and directly from the command line.

---

## 📂 Structure

```
scripts/
├── build_trust_store.py      # Main orchestrator for builds
├── verify_bundle.py          # Standalone verification utility
├── convert_format.py         # Standalone PEM converter
└── helpers/
    ├── converters.py         # Handles PEM→JKS/P12/P7B conversion logic
    ├── verifiers.py          # Validation, consistency, and expiry checks
    ├── utils.py              # File I/O, hashing, YAML helpers
    └── __init__.py
```

---

## ⚙️ Dependencies

All scripts depend only on standard Python 3 libraries plus:

```bash
pip install click cryptography pyyaml
sudo apt install openssl openjdk-17-jre-headless   # for keytool
```

System requirements:
- `openssl` on PATH (for P7B and P12 generation)
- `keytool` on PATH (for JKS generation and verification)

---

## 🚀 Usage Summary

### 🧩 Build Trust Store

**Purpose:** Merge certificate sources into canonical PEM and generate all configured output formats.

```bash
python scripts/build_trust_store.py --env prod --bundle internal
```

Options:
| Option | Description |
|---|---|
| `--env` | Environment name (e.g. dev, prod) |
| `--bundle` | Bundle name (e.g. internal, external) |
| `--package` | Create a `.tar.gz` of the build directory |
| `--verify-only` | Run certificate verification only |

Output example:
```
build/prod/internal/
 ├─ ca-trust.pem
 ├─ ca-trust.p7b
 ├─ ca-trust.jks
 ├─ ca-trust.p12
 ├─ manifest.json
 └─ checksums.sha256
```

---

### 🔍 Verify Bundle

**Purpose:** Validate certificate expiration, bundle completeness, and cross‑format consistency.

```bash
python scripts/verify_bundle.py build/prod/internal/
```

Checks performed:
- Expiry / expiring soon
- Empty or missing `.p7b` / `.p12`
- Count mismatches between PEM, P7B, JKS, and P12

Exit codes:
| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Warnings (expiring soon) |
| `5` | Failure (expired certs or invalid outputs) |

---

### 🔄 Convert Format

**Purpose:** Convert a canonical PEM file into one or more trust‑store formats.

```bash
python scripts/convert_format.py build/prod/internal/ca-trust.pem build/prod/internal/ jks p12
```

Notes:
- Defaults to output `p7b jks p12` if formats not specified.
- Uses environment variables for passwords (fallback `"changeit"`).

| Environment Variable | Purpose | Default |
|---|---|---|
| `TRUST_JKS_PASSWORD` | JKS keystore password | `"changeit"` |
| `TRUST_P12_PASSWORD` | PKCS#12 export password | `"changeit"` |

---

## 🧱 Helpers

| Module | Role |
|---|---|
| `helpers/converters.py` | PEM → JKS/P7B/P12 conversions (OpenSSL + keytool) |
| `helpers/verifiers.py` | Verifies certificate validity and bundle integrity |
| `helpers/utils.py` | Common file I/O utilities (YAML, hashing, etc.) |

---

## 🧪 Development Tips

- Run `verify_bundle.py` after each build to validate outputs.
- Use `convert_format.py` directly for ad‑hoc conversions or tests.
- To debug OpenSSL or keytool output, add `check=False` to subprocess calls temporarily.
- Passwords default to `"changeit"` to simplify local testing; override via env vars in CI.

---

## 🔮 Future Enhancements

- Unified CLI wrapper (`trustctl`) combining build/verify/convert.
- Parallelized conversions for large source sets.
- Direct manifest verification (hash validation).
- Optional JSON log output for CI pipelines.

---

## 📄 License

MIT © 2025
