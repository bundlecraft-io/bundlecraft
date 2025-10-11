# 05-scripts-and-components.md

# Scripts & Components

This document describes each core script, its purpose, and how they interact in the build-to-distribute lifecycle.

---

## 🧱 build_trust_store.py

**Purpose:**  
Central build engine that produces **ready-to-distribute trust packages**.

**Responsibilities:**
- Reads environment and bundle configurations
- Loads and validates certificate sources
- Merges certificates into canonical PEM
- Converts to multiple formats (PEM, JKS, PKCS#7, etc.)
- Imports from `helpers.converters`
- Generates `manifest.json` and `checksums.sha256`
- Optionally packages bundle as `.tar.gz`
- Hands off to Distribution for publishing
- Admins can still run `python scripts/convert_format.py` manually

**Example Usage:**
```bash
python scripts/build_trust_store.py --env prod --bundle internal
```

**Output Example:**
```bash
/build/prod/internal/
 ├── ca-trust.pem
 ├── ca-trust.jks
 ├── ca-trust.p7b
 ├── manifest.json
 ├── checksums.sha256
 └── package.tar.gz
```

## 🔄 convert_format.py (CLI Wrapper)

**Purpose:**  
Provides a user-facing command-line interface for certificate bundle format conversion.

**Responsibilities:**
- Parses CLI arguments (`--input`, `--format`, `--output`, etc.)
- Calls the core functions from `helpers.converters`
- Displays progress, logging, and output paths
- Can be used standalone or from CI/CD pipelines

**Example Usage:**
```bash
python scripts/convert_format.py \
  --input build/prod/internal/ca-trust.pem \
  --format jks \
  --output build/prod/internal/ca-trust.jks \
  --password changeit
```

**Output Example:**
```bash
[INFO] Loading build/prod/internal/ca-trust.pem
[INFO] Converting PEM → JKS
[INFO] Added certificate: CN=RootCA, O=Example Corp
[INFO] Added certificate: CN=IssuingCA1, O=Example Corp
[INFO] Wrote: build/prod/internal/ca-trust.jks
```

## 🧩 helpers/converters.py (Core Logic)

**Purpose:**  
Implements reusable conversion functions that can be imported by any script.

**Responsibilities:**
- Converts PEM bundles to target formats (JKS, PKCS#7, DER, etc.)
- Supports per-format overrides (e.g., keystore password, include chain)
- Returns manifest entries and logs progress
- Provides consistent output structure for builds and CLI


**Example Usage:**
```python
from helpers.converters import convert_to_jks

convert_to_jks(
    input_pem="build/prod/internal/ca-trust.pem",
    output_file="build/prod/internal/ca-trust.jks",
    password="changeit"
)
```
##### TODO: PROVIDE OUTPUT EXAMPLES OF FILES AND MANIFESTS

## 🔍 verify_certs.py

**Purpose:**  
Verifies the validity and integrity of certificate sources.

**Responsibilities:**
- Validates expiration, trust chain, and signature
- Reports malformed or expired certificates
- Outputs JSON and CLI summaries
- Non-zero exit codes for pipeline enforcement (CI/CD friendly)

**Example Usage:**
```bash
python scripts/verify_certs.py --bundle internal --env prod
```
**Output Example:**
```json
{
  "bundle": "internal",
  "valid_certs": 2,
  "expired": 0,
  "warnings": []
}
```
## 🚚 distribute_artifacts.py

**Purpose:**  
Publishes fully built bundles to configured destinations.

**Responsibilities:**
- Reads publish_targets from environment config
- Supports multiple backends: file system, Git, Artifactory, S3, HTTP
- Logs publication actions for audit traceability
- Does not alter bundle contents—publishing only

**Example Usage:**
```bash
python scripts/distribute_artifacts.py --env prod --bundle internal
```
**Output Example:**
```
[INFO] Publishing build/prod/internal/package.tar.gz → Artifactory (pki-trust/prod)
[INFO] Publishing complete.
```