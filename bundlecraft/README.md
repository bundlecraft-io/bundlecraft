# 🔐 BundleCraft CLI Reference

BundleCraft is a unified command-line toolkit for fetching, building, verifying, and converting CA trust bundles. It provides a single, consistent interface for PKI engineers and CI/CD systems to manage certificate trust stores across environments.

______________________________________________________________________

## 📦 Overview

The BundleCraft framework consists of four primary components (Fetch → Build → Verify → Convert):

| Component | Description | Invocation |
| ------------------------------ | --------------------------------------------------------------------------- | --------------------- |
| **Fetcher** (`fetch.py`) | Securely fetches remote certificate sources and stages them for build. | `bundlecraft fetch` |
| **Builder** (`builder.py`) | Builds trust bundles from configured certificate sources. | `bundlecraft build` |
| **Bulk Builder** (`cli.py`) | Discovers and builds all environments automatically. | `bundlecraft build-all` |
| **Verifier** (`verifier.py`) | Verifies integrity, consistency, and certificate validity of built bundles. | `bundlecraft verify` |
| **Converter** (`converter.py`) | Converts certificate bundles between any supported formats (PEM, P7B, JKS, P12, ZIP). Accepts DER as input. | `bundlecraft convert` |
| **Differ** (`differ.py`) | Compares two bundle builds to identify added, removed, and unchanged certificates. | `bundlecraft diff` |
| **CLI Wrapper** (`cli.py`) | Aggregates tools into a single cohesive interface. | `bundlecraft` |

Once installed via `pip install -e .`, the command `bundlecraft` becomes available system-wide.

______________________________________________________________________

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

```text
Usage: bundlecraft [OPTIONS] COMMAND [ARGS]...

Commands:
  fetch      Securely fetch and stage certificates from declared sources.
  build      Build CA trust bundles from configured sources.
  build-all  Discover and build all environments automatically.
  verify     Verify integrity and consistency of built bundles.
  convert    Convert PEM bundles into alternate trust store formats.
  diff       Compare two bundle builds and generate diff reports.
```

### 🌐 `bundlecraft fetch`

Purpose: Reach out to preconfigured and trusted certificate sources at build-time, verify content, and stage PEMs for the builder. No persistent caching; artifacts are staged under `cert_sources/staged/<source_name>/` (remote entries under `fetch/<name>/`) by default (configurable via `--output-dir`) and cleaned on each run unless `--no-clean` is used.
Purpose: Reach out to preconfigured and trusted certificate sources at build-time, verify content, and stage PEMs for the builder. No persistent caching; artifacts are staged under `cert_sources/staged/<source_name>/` (remote entries under `fetch/<name>/`) by default (configurable via `--output-dir`) and cleaned on each run unless `--no-clean` is used.

Usage:

```bash
bundlecraft fetch --source-config-file config/sources/<source>.yaml \
  [--output-dir ./cert_sources/staged] [--fetch-name <name>] [--workspace-root <dir>] \
  [--no-clean] [--dry-run] [--json] [--verbose]
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
  Treat `cert_sources/staged/` as ephemeral staging, not a cache.
  Treat `cert_sources/staged/` as ephemeral staging, not a cache.

Philosophy & best practices:

- You configure trust; BundleCraft enforces it and records provenance.
- Prefer HTTPS + CA pinning for APIs; add TLS leaf fingerprint pinning during rotations.
- Pin content hashes for static bundles (e.g., Mozilla public roots) when feasible.
- Keep secrets in env vars, not YAML; use CI secret stores.
- Treat `cert_sources/staged/` as ephemeral staging, not a cache.
- Treat `cert_sources/staged/` as ephemeral staging, not a cache.

### 🔐 Vault fetcher

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
- Offline builds → pre-stage inputs using `bundlecraft fetch` in a connected environment, commit or package them, then run `bundlecraft build --skip-fetch`.

______________________________________________________________________

## ⚙️ Subcommands

### 🧱 `bundlecraft build`

**Purpose:** Build ready-to-distribute trust bundles from certificate sources and configuration files.

**Usage:**

```bash
bundlecraft build --env <env>  [OPTIONS]
```

**Options:**

| Option | Description |
| ----------------- | ----------- |
| `--env` | Environment identifier matching a config file in `config/envs/<env>.yaml` (e.g., `dev`, `prod`). Required. |
| `--bundle` | Bundle name to build (from env `bundles`). If omitted, builds all bundles|
| `--verify-only` | Skip build; only verify existing output or staged sources. |
| `--skip-fetch` | Skip the fetch stage; use existing staged inputs (offline-friendly). |
| `--skip-verify` | Skip verification (not recommended for production). |
| `--output-root` | Root directory for outputs (default: `./dist`). |
| `--verbose` | Enable verbose logging. |
| `--force` | Overwrite existing output files. |
| `--dry-run` | Show actions without writing files or executing external tools. |
| `--sign` | GPG-sign release artifacts. |
| `--gpg-key-id` | GPG key ID to use for signing. |
| `--generate-sbom` | Generate CycloneDX SBOM (default). |
| `--no-sbom` | Disable SBOM generation. |
| `--json` | Emit machine-readable JSON. |
| `--keep-temp` | Preserve temporary build directories on failure. |

**Outputs:**

- `bundlecraft-ca-trust.pem`: canonical PEM bundle
- `bundlecraft-ca-trust.jks`: Java KeyStore bundle
- `bundlecraft-ca-trust.p12`: PKCS#12 bundle
- `bundlecraft-ca-trust.p7b`: PKCS#7 bundle
- `checksums.sha256`: per-file integrity manifest
- `manifest.json`: build metadata summary
- `package.tar.gz`: deterministic tar archive of artifacts (controlled by env config `package`, default: enabled)
- `sbom.json`: CycloneDX SBOM (when enabled)

**Examples:**

```bash
# Build a composed bundle in an env
bundlecraft build --env prod --bundle internal

# Verify only (no rebuild)
bundlecraft build --env dev --bundle internal --verify-only

# Offline-friendly build:
# 1) Pre-stage in a connected environment: bundlecraft fetch --source-config-file config/bundles/internal.yaml
# 2) Commit or package staged inputs
# 3) Build without network access:
bundlecraft build --env prod --bundle internal --skip-fetch
```

Local source schema tip:

```yaml
# In config/bundles/<bundle>.yaml
repo:
  - name: roots
    include:
      # Path entries (string or {path: ...})
      - cert_sources/internal/roots/
      - { path: cert_sources/internal/rootCA.pem }
      - cert_sources/internal/roots/
      - { path: cert_sources/internal/rootCA.pem }
      # Inline PEM entry (optional name)
      - name: special-inline.pem
        inline: |
          -----BEGIN CERTIFICATE-----
          ...
          -----END CERTIFICATE-----
```

______________________________________________________________________

### 🏗️ `bundlecraft build-all`

**Purpose:** Discover and build all environments automatically. This command scans for environment configuration files and builds each one sequentially, eliminating the need to manually specify each environment.

**Usage:**

```bash
bundlecraft build-all [OPTIONS]
```

**Options:**

| Option | Description |
| ----------------- | ----------- |
| `--envs-path` | Path or glob to discover env yaml files. If a directory, scans for `*.yaml` inside. Relative paths are resolved under `config/envs/`. Examples: `'my_github_envs'`, `'my_github_envs/*.yaml'`, `'config/envs/custom/*.yaml'`. |
| `--recursive` | Recursively discover env configs in subdirectories (e.g., `**/*.yaml`). |
| `--print-plan` | Show which environment configs would be built and exit without building. |
| `--skip-fetch` | Skip fetch stage; use existing staged sources. |
| `--skip-verify` | Skip verification stage. |
| `--output-root` | Root directory for outputs (default: `./dist`). |
| `--verbose` | Enable verbose logging. |
| `--force` | Overwrite existing output files. |
| `--dry-run` | Show actions without writing files or executing external tools. |
| `--sign` | GPG-sign release artifacts. |
| `--gpg-key-id` | GPG key ID to use for signing. |
| `--no-sbom` | Skip SBOM generation. |
| `--json` | Emit machine-readable JSON output. |
| `--keep-temp` | Preserve temporary build directories on failure. |

**Discovery Logic:**

- By default, scans `config/envs/*.yaml` for environment configurations
- Skips files starting with "example" (e.g., `example-dev.yaml`)
- Each discovered environment builds all its configured bundles
- Uses the same outputs and artifacts as individual `bundlecraft build` commands

**Examples:**

```bash
# Build all environments in config/envs/
bundlecraft build-all

# Build environments in a specific subdirectory
bundlecraft build-all --envs-path my_group

# Use glob pattern for specific environments
bundlecraft build-all --envs-path "my_group/*.yaml"

# Recursively discover environments in subdirectories
bundlecraft build-all --recursive

# Show build plan without executing (useful for CI/CD planning)
bundlecraft build-all --print-plan

# JSON output for programmatic use
bundlecraft build-all --envs-path my_group --print-plan --json

# Recursive discovery with plan output
bundlecraft build-all --recursive --print-plan
```

**CI/CD Integration:**

The `--print-plan` option is particularly useful for CI/CD systems that need to understand what will be built:

```bash
# Get build plan in JSON format for matrix strategies
bundlecraft build-all --print-plan --json

# Scope to specific environment groups
bundlecraft build-all --envs-path teamA --print-plan --json
```

**Output Structure:**

When using `--print-plan --json`, the output includes:

- `pattern`: The resolved file pattern used for discovery
- `environments`: Array of discovered environments with:
  - `env`: Environment file stem (e.g., `prod`)
  - `name`: Display name from config or file stem
  - `path`: Full path to the environment config file
  - `build_path`: Computed output directory for this environment

______________________________________________________________________

### 🔍 `bundlecraft verify`

**Purpose:** Verify the integrity, consistency, and validity of generated trust bundles.

**Usage:**

```bash
bundlecraft verify --target <build_dir_or_file> [OPTIONS]
```

**Options:**

| Option | Description |
| ------------------- | ------------------------------------------------------------ |
| `--target` | Path to a build directory or a single file. Required. |
| `--verify-manifest` | Display manifest info only (no verification). |
| `--verify-all` | Verify all bundle files and display manifest in one run. |
| `--verbose` | Show detailed file metadata, hashes, and certificate counts. |
| `--output-root` | Root directory for build outputs (default: `./dist`). |

**Verification Features:**

- Validates file checksums via `checksums.sha256`
- Ensures bundle consistency across formats
- Counts certificates in PEM, P12, P7B, and JKS
- Detects hash mismatches or empty bundles

**Examples:**

```bash
# Verify an entire bundle
bundlecraft verify --target dist/prod/internal

# Verify everything with full detail
bundlecraft verify --target dist/prod/internal --verify-all --verbose
```

______________________________________________________________________

### 🔄 `bundlecraft convert`

**Purpose:** Convert certificate bundles between any supported formats: PEM, PKCS#7, JKS, PKCS#12, or ZIP. Accepts DER as input only (not output).

**Usage:**

```bash
bundlecraft convert --input <input_file> --output-dir <output_path> --output-format <format> [OPTIONS]
```

**Options:**

| Option | Description |
| ----------------- | --------------------------------------------------------------------------- |
| `--input` | Input file (PEM, DER, P7B, JKS, P12). Required. |
| `--output-dir` | Directory to write converted output. Required. |
| `--output-format` | Output format to produce (one of: pem, p7b, jks, p12, zip). Required. |
| `--force` | Overwrite output files if they already exist. Default: false. |
| `--password` | Password for protected input formats (JKS, P12). Prefer env vars. |
| `--verbose` | Enable detailed logging during conversion. |
| `--output-root` | Root directory for build outputs (default: `./dist`). |

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

- Requires `openssl` binary in PATH for P7B and P12 formats.
- Uses optional environment variables `TRUST_JKS_PASSWORD` and `TRUST_P12_PASSWORD` for keystore password overrides.
- Only one output format can be produced per invocation.
- Any supported input format (PEM, DER, P7B, JKS, P12) can be converted to any supported output format (PEM, P7B, JKS, P12, ZIP).
- DER is accepted as input only; use P7B for binary bundle output (DER is typically single-cert, not suitable for trust stores).

______________________________________________________________________

### 📊 `bundlecraft diff`

**Purpose:** Compare two bundle builds to identify added, removed, and unchanged certificates. Useful for auditing changes between releases, verifying expected certificate updates, and tracking trust store evolution over time.

**Usage:**

```bash
bundlecraft diff --from <old_bundle_dir> --to <new_bundle_dir> [OPTIONS]
```

**Options:**

| Option | Description |
| ----------------- | --------------------------------------------------------------------------- |
| `--from` | Path to the first (old) bundle directory. Required. |
| `--to` | Path to the second (new) bundle directory. Required. |
| `--output-format` | Output format: `human` (default) or `json`. |
| `-o, --output` | Write output to file instead of stdout. |

**Examples:**

```bash
# Compare two bundle builds (human-readable)
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal

# Generate JSON diff report
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal --output-format json

# Save diff to file
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal -o diff-report.txt

# JSON output to file for CI/CD processing
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal --output-format json -o diff.json
```

**Output:**

Human-readable format includes:

- Summary of changes (added, removed, unchanged counts)
- Full details of added certificates (subject, fingerprint, issuer, validity period)
- Full details of removed certificates
- Manifest metadata from both bundles (env, bundle, timestamp)

JSON format provides structured data suitable for:

- Automated CI/CD pipelines
- Integration with monitoring systems
- Historical tracking and analysis
- Programmatic processing

**Certificate Identification:**

Certificates are uniquely identified by their SHA256 fingerprints, ensuring accurate change detection even when certificates have similar subjects or issuers.

**Notes:**

- Both bundle directories must contain a `bundlecraft-ca-trust.pem` file
- Optionally reads `manifest.json` for metadata if present
- Exit code 0 for both changes detected and no changes (success cases)
- Exit code 1 for errors (missing files, parsing errors, etc.)

______________________________________________________________________

### 🧩 `bundlecraft` (the CLI root)

**Purpose:** Acts as the umbrella command to route subcommands to their respective tools.

**Usage:**

```bash
bundlecraft [COMMAND] [OPTIONS]
```

**Examples:**

```bash
bundlecraft build --env prod --bundle internal
bundlecraft build-all --print-plan
bundlecraft verify --target dist/prod/internal --verify-all
bundlecraft convert --pem-file dist/prod/internal/bundlecraft-ca-trust.pem --output-dir dist/prod/internal/
```

**Help:**
Each subcommand supports `--help`, e.g.:

```bash
bundlecraft verify --help
```

______________________________________________________________________

## 🧱 Project Structure

```text
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

______________________________________________________________________

## 🧠 Best Practices for Referencing in Docs and Scripts

- **Preferred (installed usage):** `bundlecraft <subcommand>` - this is the canonical CLI form.
- **Module form (uninstalled / dev use):** `python -m bundlecraft.cli <subcommand>`
- **Never reference file paths** like `bundlecraft/builder.py` in docs; this implies direct script execution, which breaks imports.

So in all documentation, use:

```bash
bundlecraft build ...
```

not:

```bash
python bundlecraft/builder.py ...
```

______________________________________________________________________

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

______________________________________________________________________

## 📘 Notes for Contributors

- Always run from the project root or with the package installed.
- Use `pip install -e .` for iterative local testing.
- The project expects Python 3.9+ and the `openssl` system utility.

______________________________________________________________________

## 🧾 License

See the [LICENSE](../LICENSE) file for terms.
