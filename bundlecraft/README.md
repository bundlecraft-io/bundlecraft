# 🔐 BundleCraft CLI Reference

BundleCraft is a unified command-line toolkit for fetching, building, verifying, and converting CA trust bundles. It provides a single, consistent interface for PKI engineers and CI/CD systems to manage certificate trust stores across environments.

---

## 📦 Overview

The BundleCraft framework consists of four primary components (Fetch → Build → Verify → Convert):

| Component                      | Description                                                                 | Invocation            |
| ------------------------------ | --------------------------------------------------------------------------- | --------------------- |
| **Fetcher** (`fetch.py`)       | Securely fetches remote certificate sources and stages them for build.      | `bundlecraft fetch`   |
| **Builder** (`builder.py`)     | Builds trust bundles from configured certificate sources.                   | `bundlecraft build`   |
| **Verifier** (`verifier.py`)   | Verifies integrity, consistency, and certificate validity of built bundles. | `bundlecraft verify`  |
| **Converter** (`converter.py`) | Converts certificate bundles between any supported formats (PEM, P7B, JKS, P12, ZIP). Accepts DER as input. | `bundlecraft convert` |
| **CLI Wrapper** (`cli.py`)     | Aggregates tools into a single cohesive interface.                          | `bundlecraft`         |

Once installed via `pip install -e .`, the command `bundlecraft` becomes available system-wide.

---

## 🚀 Installation and Invocation

### Local installation (editable mode)

```bash
pip install -e .
```

This installs the CLI command `bundlecraft` globally (editable, so code changes take immediate effect).



### Manual module invocation (no install)

```bash
python -m bundlecraft.cli <subcommand> [options]
```

### CLI entrypoint

After installation, run:

```bash
bundlecraft --help
```

You’ll see:

```
Usage: bundlecraft [OPTIONS] COMMAND [ARGS]...

Commands:
  fetch    Securely fetch and stage certificates from declared sources.
  build     Build CA trust bundles from configured sources.
  verify    Verify integrity and consistency of built bundles.
  convert   Convert PEM bundles into alternate trust store formats.
```

### 🌐 `bundlecraft fetch`

Purpose: Reach out to preconfigured and trusted certificate sources at build-time, verify content, and stage PEMs for the builder. No persistent caching; artifacts are written to `sources/fetched/<craft>/<bundle>/` and cleaned on each run by default.

Usage:

```bash
bundlecraft fetch --craft <craft> --bundle <bundle_name> [--workspace-root <dir>] [--no-clean] [--offline]
```

Config excerpts (in `config/bundles/<bundle>.yaml`):

```yaml
fetch:
  - name: mozilla
    type: url
    url: https://curl.se/ca/cacert.pem
    verify:
      sha256: <expected_sha256>  # optional but recommended
      # Optional TLS enhancements:
      ca_file: config/certs/public-ca.pem            # custom CA bundle for TLS verification
      tls_fingerprint_sha256: <leaf_cert_fp_hex>     # pin to server leaf cert

# API example with bearer token from env var
fetch:
  - name: keyfactor_trusted
    type: api
    provider: keyfactor
    endpoint: https://pki.example.com/api/v1/collections/trusted
    token_ref: KEYFACTOR_TOKEN   # reads token from environment
```

Notes:
- Only HTTPS and file URLs are supported for URL fetchers; generic API fetcher supports bearer auth.
- Optional SHA256 pinning defends against tampering; mismatches abort the fetch.
- Optional TLS security: custom CA bundle and leaf certificate fingerprint pinning.
- Staging only: no persistent cache. Staging dir is cleaned per run unless `--no-clean`.
- Offline mode: `--offline` fails if a fetch section exists (no network access allowed).

Philosophy & best practices:
- You configure trust; BundleCraft enforces it and records provenance.
- Prefer HTTPS + CA pinning for APIs; add TLS leaf fingerprint pinning during rotations.
- Pin content hashes for static bundles (e.g., Mozilla public roots) when feasible.
- Keep secrets in env vars, not YAML; use CI secret stores.
- Treat `sources/fetched/` as ephemeral staging, not a cache.

### 🔐 Vault fetcher

Install optional dependency for Vault:

```bash
pip install -e .[fetchers]
```

Config example:

```yaml
fetch:
  - name: internal_roots
    type: vault
    mount_point: secret           # KV engine mount
    path: pki/trusted_roots      # secret path under mount
    pem_field: pem               # field containing PEM text
    addr: https://vault.example.com:8200  # or set VAULT_ADDR
    token_ref: VAULT_TOKEN       # env var name containing token
    namespace: my/team           # optional
    verify:
      ca_file: config/certs/vault-ca.pem  # custom TLS CA if needed
```

Environment variables supported:
- `VAULT_ADDR` and `VAULT_TOKEN` are used if `addr` or `token_ref` are not set.

### 🧩 Keyfactor fetcher (generic API)

The `type: api` fetcher can call Keyfactor endpoints with a Bearer token:

```yaml
fetch:
  - name: keyfactor_trusted
    type: api
    provider: keyfactor
    endpoint: https://pki.example.com/api/v1/collections/trusted
    token_ref: KEYFACTOR_TOKEN
    verify:
      ca_file: config/certs/pki-ca.pem
      tls_fingerprint_sha256: <leaf_cert_fp_hex>
```

Set the token in the environment (e.g., CI secret):

```bash
export KEYFACTOR_TOKEN=...
```

Testing without live Vault/Keyfactor:
- Use `file://` and `https://` against known public resources to validate fetch.
- For provider flows, mock the endpoints locally (e.g., with `pytest` monkeypatch or a tiny HTTP server) and point `endpoint:` to `http://127.0.0.1:NNNN` (note: the fetcher rejects insecure HTTP by default; for tests use HTTPS with self-signed + `verify.ca_file`, or patch the URL opener in tests).
- Unit tests in this repo exercise the fetch module via file URLs and hash pinning; provider-specific tests can stub network calls.

Troubleshooting highlights:
- Insecure HTTP rejected → use HTTPS or file URLs.
- SHA256/TLS fingerprint mismatch → update pins after validating legitimate changes.
- `hvac` missing → install extras `.[fetchers]`.
- `--offline` with `fetch:` present → pre-stage in connected environments.

---

## ⚙️ Subcommands

### 🧱 `bundlecraft build`

**Purpose:** Build ready-to-distribute trust bundles from certificate sources and configuration files.

**Usage:**

```bash
bundlecraft build --craft <craft> --bundle <bundle_name> [OPTIONS]
```

**Options:**

| Option          | Description                                              |
| --------------- | -------------------------------------------------------- |
| `--craft`       | Craft name (e.g., `dev`, `prod`, `dmz`). Required. |
| `--bundle`      | Bundle name (e.g., `internal`, `external`). Required.    |
| `--package`     | Also create a `.tar.gz` archive of the build folder.     |
| `--verify-only` | Skip build; verify certificates only.                    |
| `--offline`     | Do not contact the network; fail if `fetch` is required. |
| `--output-root` | Root directory for build outputs (default: `./dist`).    |

**Outputs:**

* `bundlecraft-ca-trust.pem`: canonical PEM bundle
* `bundlecraft-ca-trust.jks`: Java KeyStore bundle
* `bundlecraft-ca-trust.p12`: PKCS#12 bundle
* `bundlecraft-ca-trust.p7b`: PKCS#7 bundle
* `checksums.sha256`: per-file integrity manifest
* `manifest.json`: build metadata summary

**Examples:**

```bash
# Build a composed target in a craft
bundlecraft build --craft prod --bundle internal

# Verify only (no rebuild)
bundlecraft build --env dev --bundle internal --verify-only

# Offline build: will fail if bundle config contains 'fetch:' entries
bundlecraft build --craft prod --bundle internal --offline
```

---

### 🔍 `bundlecraft verify`

**Purpose:** Verify the integrity, consistency, and validity of generated trust bundles.

**Usage:**

```bash
bundlecraft verify --target <build_dir_or_file> [OPTIONS]
```

**Options:**

| Option              | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `--target`          | Path to a build directory or a single file. Required.        |
| `--verify-manifest` | Display manifest info only (no verification).                |
| `--verify-all`      | Verify all bundle files and display manifest in one run.     |
| `--verbose`         | Show detailed file metadata, hashes, and certificate counts. |
| `--output-root`     | Root directory for build outputs (default: `./dist`).       |

**Verification Features:**

* Validates file checksums via `checksums.sha256`
* Ensures bundle consistency across formats
* Counts certificates in PEM, P12, P7B, and JKS
* Detects hash mismatches or empty bundles

**Examples:**

```bash
# Verify an entire bundle
bundlecraft verify --target dist/prod/internal

# Verify everything with full detail
bundlecraft verify --target dist/prod/internal --verify-all --verbose
```

---


### 🔄 `bundlecraft convert`

**Purpose:** Convert certificate bundles between any supported formats: PEM, PKCS#7, JKS, PKCS#12, or ZIP. Accepts DER as input only (not output).

**Usage:**

```bash
bundlecraft convert --input <input_file> --output-dir <output_path> --output-format <format> [OPTIONS]
```

**Options:**

| Option            | Description                                                                 |
| ----------------- | --------------------------------------------------------------------------- |
| `--input`         | Input file (PEM, DER, P7B, JKS, P12). Required.                             |
| `--output-dir`    | Directory to write converted output. Required.                              |
| `--output-format` | Output format to produce (one of: pem, p7b, jks, p12, zip). Required.       |
| `--force`         | Overwrite output files if they already exist. Default: false.               |
| `--password`      | Password for protected input formats (JKS, P12). Prefer env vars.           |
| `--verbose`       | Enable detailed logging during conversion.                                  |
| `--output-root`   | Root directory for build outputs (default: `./dist`).                      |

**Examples:**

```bash
# Convert DER to PEM
bundlecraft convert --input dist/prod/internal/bundlecraft-ca-trust.der --output-dir dist/prod/internal/ --output-format pem

# Convert PEM to P7B (with force overwrite)
bundlecraft convert --input dist/prod/internal/bundlecraft-ca-trust.pem --output-dir dist/prod/internal/ --output-format p7b --force

# Convert to ZIP (tarball of PEMs)
bundlecraft convert --input dist/prod/internal/bundlecraft-ca-trust.pem --output-dir dist/prod/internal/ --output-format zip
```

**Output Filenames:**
All outputs use standardized naming: `bundlecraft-ca-trust.[FORMAT]`
- Example: `bundlecraft-ca-trust.pem`, `bundlecraft-ca-trust.jks`, `bundlecraft-ca-trust.tar.gz`

**ZIP Output Format:**

- Produces a `.tar.gz` archive containing each certificate as an individual PEM file.
- Filenames: `{subject.CN}-{thumbprint}.pem`
- Useful for distributing certs as separate files in a single archive.

**Environment Variables:**

- `TRUST_JKS_PASSWORD`: Password for JKS keystores (default: `"changeit"`)
- `TRUST_P12_PASSWORD`: Password for PKCS#12 files (default: `"changeit"`)

**Notes:**

- Requires `openssl` and `keytool` binaries in PATH for some formats.
- Uses optional environment variables `TRUST_JKS_PASSWORD` and `TRUST_P12_PASSWORD` for keystore password overrides.
- Only one output format can be produced per invocation.
- Any supported input format (PEM, DER, P7B, JKS, P12) can be converted to any supported output format (PEM, P7B, JKS, P12, ZIP).
- DER is accepted as input only; use P7B for binary bundle output (DER is typically single-cert, not suitable for trust stores).

---

### 🧩 `bundlecraft` (the CLI root)

**Purpose:** Acts as the umbrella command to route subcommands to their respective tools.

**Usage:**

```bash
bundlecraft [COMMAND] [OPTIONS]
```

**Examples:**

```bash
bundlecraft build --env prod --bundle internal
bundlecraft verify --target dist/prod/internal --verify-all
bundlecraft convert --pem-file dist/prod/internal/bundlecraft-ca-trust.pem --output-dir dist/prod/internal/
```

**Help:**
Each subcommand supports `--help`, e.g.:

```bash
bundlecraft verify --help
```

---

## 🧱 Project Structure

```
bundlecraft/
├── __init__.py
├── cli.py          # Unified CLI entrypoint
├── fetch.py        # Fetch and stage remote sources
├── builder.py      # Build trust bundles
├── verifier.py     # Verify built bundles
├── converter.py    # Convert PEM to other formats
├── fetchers/
│   ├── __init__.py
│   └── http.py     # HTTPS and file URL fetcher
└── helpers/
    ├── __init__.py
    ├── utils.py
    ├── convert_utils.py
    └── verify_utils.py
```

---

## 🧠 Best Practices for Referencing in Docs and Scripts

* **Preferred (installed usage):** `bundlecraft <subcommand>` — this is the canonical CLI form.
* **Module form (uninstalled / dev use):** `python -m bundlecraft.cli <subcommand>`
* **Never reference file paths** like `bundlecraft/builder.py` in docs; this implies direct script execution, which breaks imports.

So in all documentation, use:

```bash
bundlecraft build ...
```

not:

```bash
python bundlecraft/builder.py ...
```

---

## 🧪 Testing and Validation

Local validation (editable mode):

```bash
bundlecraft build --env dev --bundle internal
bundlecraft verify --target dist/dev/internal
bundlecraft convert --pem-file dist/dev/internal/bundlecraft-ca-trust.pem --output-dir dist/dev/internal/
```

Automated CI/CD (non-editable install):

```bash
pip install .
bundlecraft build --env prod --bundle internal
bundlecraft verify --target dist/prod/internal --verify-all
```

---

## 📘 Notes for Contributors

* Always run from the project root or with the package installed.
* Use `pip install -e .` for iterative local testing.
* The project expects Python 3.9+ and system utilities `openssl` + `keytool`.

---

## 🧾 License

See the [LICENSE](../LICENSE) file for terms.
