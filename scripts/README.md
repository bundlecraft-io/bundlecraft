# 🧰 BundleCraft Scripts

This folder contains helper scripts used locally and in CI.

Quick catalog:

| Script | Purpose |
|---|---|
| `detect_env_targets.py` | Discover craft targets from `config/crafts/*.yaml` (or legacy `config/envs/*.yaml`) and emit a JSON matrix for CI |
| `trust_matrix.py` | Build a Craft × Bundle trust matrix from craft configs (table/markdown/csv/json) |
| `generate_test_cas.py` | Generate self-signed test CA certificates with automatic private key disposal (TESTING ONLY) |
| `test-server-local.py` | Local HTTPS test server for CI and development with Swagger UI |
| `vault-local.py` | Spin up a local HashiCorp Vault dev instance for testing the Vault fetcher |
| `json-output-examples.sh` | Demonstration of JSON output from BundleCraft commands for CI/CD automation (requires `jq`) |

---

## 🔐 generate_test_cas.py

⚠️ **TESTING ONLY - DO NOT USE FOR PRODUCTION** ⚠️

Generate self-signed root CAs and subordinate certificate chains for testing. Automatically disposes of all private key material after certificate generation.

### Security Features

- **Zero key persistence**: Private keys are NEVER written to disk
- **Immediate disposal**: Keys are zeroed in memory after certificate generation
- **No export capability**: Intentionally prevents key export (aligns with BundleCraft's trust-only principle)
- **Interactive warning**: Requires typing "I UNDERSTAND" before generation (skip with `--no-warning` for automation)

### Quick Start

```bash
# Single root CA (outputs to ./generated-test-cas/)
python scripts/generate_test_cas.py --name my-test-root --no-warning

# Root with 2-tier subordinate chain
python scripts/generate_test_cas.py --name dev-root --depth 2 --env dev --boundary internal --no-warning

# Custom output directory
python scripts/generate_test_cas.py --name prod-root --output-dir /tmp/test-cas --no-warning

# Batch generation from config
python scripts/generate_test_cas.py --config scripts/example_ca_config.json --no-warning
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--name` | Root CA common name | *(required unless --config)* |
| `--depth` | Subordinate tiers (0-10) | 0 (root only) |
| `--env` | Environment label (dev/qa/prod) | None |
| `--boundary` | Network boundary (internal/dmz/external) | None |
| `--key-size` | RSA key size in bits | 2048 |
| `--validity` | Certificate validity (days) | 365 |
| `--output-dir` | Root output directory | `./generated-test-cas` |
| `--config` | JSON config for batch mode | None |
| `--no-warning` | Skip security confirmation | False |

### Output Structure

Certificates are organized hierarchically within the output directory:

```
generated-test-cas/
├── <env>/
│   └── <boundary>/
│       ├── root/
│       │   └── <name>.pem
│       ├── tier1/
│       │   └── <name>-sub1.pem
│       └── tier2/
│           └── <name>-sub2.pem
```

Or for a simple root-only CA without env/boundary:

```
generated-test-cas/
└── root/
    └── <name>.pem
```

### Example: Generate Test Chain

```bash
python scripts/generate_test_cas.py \
  --name dev-internal-root \
  --depth 3 \
  --env dev \
  --boundary internal \
  --key-size 2048 \
  --validity 365 \
  --no-warning
```

Output:
- `generated-test-cas/dev/internal/root/dev-internal-root.pem`
- `generated-test-cas/dev/internal/tier1/dev-internal-root-sub1.pem`
- `generated-test-cas/dev/internal/tier2/dev-internal-root-sub2.pem`
- `generated-test-cas/dev/internal/tier3/dev-internal-root-sub3.pem`

### Batch Generation

Create a config file (e.g., `my_hierarchies.json`):

```json
[
  {
    "root_name": "test-root-a",
    "depth": 1,
    "env": "test",
    "boundary": "internal"
  },
  {
    "root_name": "test-root-b",
    "depth": 2,
    "env": "test",
    "boundary": "dmz",
    "key_size": 4096,
    "validity_days": 730
  }
]
```

Run:

```bash
python scripts/generate_test_cas.py --config my_hierarchies.json --no-warning
```

### Integration with BundleCraft

Generated certificates can be used in BundleCraft configs:

```yaml
# config/bundles/test-bundle.yaml
id: test-internal
description: Test bundle with generated CAs
repo:
  - name: generated
    include:
      # Path entries (string or {path: ...})
      - generated-test-cas/dev/internal/root/dev-root.pem
      - { path: generated-test-cas/dev/internal/tier1/dev-root-sub1.pem }
      # Inline (optional)
      # - name: example-inline.pem
      #   inline: |
      #     -----BEGIN CERTIFICATE-----
      #     ...
      #     -----END CERTIFICATE-----
output_formats:
  - pem
```

Then build:

```bash
bundlecraft build --env dev --bundle test-internal
```

### Use Cases

✅ **Appropriate:**
- BundleCraft development and testing
- CI/CD pipeline certificate verification
- Local test environments
- PoC certificate chain validation

❌ **Inappropriate:**
- Production certificate generation
- Issuing certificates for live services
- Long-term key storage
- Personal CA infrastructure

### Requirements

```bash
pip install cryptography
```

Or install BundleCraft with dev dependencies:

```bash
pip install -e ".[dev]"
```

---

## 🔎 detect_env_targets.py

Parse `config/crafts/*.yaml` (or legacy `config/envs/*.yaml`) and output a JSON array describing the CI build matrix.


Usage:

```bash
python scripts/detect_env_targets.py > env_targets.json
cat env_targets.json
```

Example output:

```json
[
  {"env": "prod", "target": "internal", "output_root": "dist"},
  {"env": "prod", "target": "mozilla",  "output_root": "dist"}
]
```

Notes:


## 📐 trust_matrix.py

Generate a trust matrix showing which crafts (rows) trust which bundles (columns), based on `targets.<name>.includes` in `config/crafts/*.yaml`.

# Scripts

Local helper scripts for development and CI.

## test-server-local.py

A self-contained HTTPS Flask server used for local testing and CI. It provides:

- A friendly HTML homepage at `/` with quick usage tips and a link to BundleCraft
- A plain HTTP download endpoint at `/test-cert.pem`
- A token-protected API endpoint at `/Certificates/Download` (Keyfactor-like)
- Built-in Swagger UI at `/apidocs`

Key features:
- Generates ephemeral TLS cert/key and stores them in a temp dir
- Prints the homepage URL first for convenience
- Runs Flask in its own process group for reliable shutdown
- Uses your project virtualenv Python if available

Usage

- Start in background (default):

  ./scripts/test-server-local.py up --port 8443 --token mock-token-12345

- Stop background server:

  ./scripts/test-server-local.py down

- Run in foreground:

  ./scripts/test-server-local.py serve --port 8443 --token mock-token-12345

Notes

- TLS material and a small flask log file are stored under `/tmp/test-server-local-<random>`.
- The latest instance directory is tracked at `/tmp/test-server-local-latest`.
- The CA certificate is at `<data_dir>/server.crt` for trusting the server in tests.
- The API expects `Authorization: Bearer <TOKEN>` and a JSON body like `{ "CertID": 12345, "CertificateFormat": "PEM", "IncludeChain": true }`.

## vault-local.py

Helper to run a local Vault dev server using Podman during CI, with an option to run a post-start CI command.

# Add HashiCorp repo
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt-get update
sudo apt-get install -y vault
```

Verify:

```bash
vault version
```

#### Option 2: Podman Container (Alternative)

If you prefer isolation, install Podman:

```bash
sudo apt-get install -y podman
```

Then you can run Vault as:

```bash
podman run --rm -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=root' \
  -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
  docker.io/library/vault:latest
```

*(Podman supports rootless containers - safer and Docker-compatible syntax.)*


### 🧪 Usage

```bash
# Start Vault in local dev mode (binary runtime)
./vault-local.sh up --runtime binary

# Run your BundleCraft fetch after exporting env vars (see config example below)
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --env dev --bundle local-vault

# Tear down environment
./vault-local.sh down
```

#### Auto-Cleanup

```bash
./vault-local.sh up --auto-cleanup
```

Vault will wait for you to finish, then clean up automatically.

#### CI/CD Mode

```bash
./vault-local.sh up --ci-cmd "bundlecraft fetch --env dev --bundle local-vault"
```

Runs your test command, then removes the local Vault environment automatically.


### ⚙ Options

| Flag                | Description                                        |
| ------------------- | -------------------------------------------------- |
| `--runtime <mode>`  | Runtime: `binary` (default) or `podman`            |
| `--port <num>`      | Port for Vault (default 8200)                      |
| `--data-dir <path>` | Directory for Vault data (default `./local_vault`) |
| `--token <string>`  | Dev root token (default `root`)                    |
| `--image <name>`    | Vault image when using podman (default `hashicorp/vault:latest`) |
| `--auto-cleanup`    | Clean up automatically after use                   |
| `--ci-cmd "<cmd>"`  | Run command in CI mode with VAULT_* exported, then teardown |
| `--verbose`         | Enable detailed logging                            |
| `-h`, `--help`      | Show help message                                  |


### 🧩 Notes



### 🔗 BundleCraft integration example

When the script starts Vault, it configures a simple PKI test setup and writes a PEM to:


Configure your bundle to fetch this PEM via the Vault fetcher:

```yaml
# config/bundles/local-vault.yaml
id: local-vault
fetch:
  - name: from_vault
    type: vault
    mount_point: secret
    path: pki/trusted_roots
    pem_field: pem
    addr: http://127.0.0.1:8200
    token_ref: VAULT_TOKEN
```

And a minimal craft file:

```yaml
# config/crafts/dev.yaml
name: Dev
```

Then run:

```bash
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --craft dev --bundle local-vault
```

This will stage the local Vault-provided PEM under `sources/fetched/dev/local-vault/from_vault.pem`.


Reference:


# BundleCraft: Local Vault Test Environment

This document explains how to spin up a **local HashiCorp Vault instance** for testing BundleCraft’s Vault fetch integration.

It supports two methods:
1. **Direct binary mode (recommended)** - runs the Vault binary directly on your system in dev mode.
2. **Container mode (optional)** - runs Vault in a rootless Podman container.

---

## 🚀 Overview

This test environment:
- Starts Vault in **dev mode** (temporary, unsealed, no persistence)
- Enables the PKI secrets engine at `pki/trusted_roots`
- Generates a root CA and inserts its PEM into a KV path for testing
- Provides a teardown command to clean up all local state
- Supports CI/CD automation via `--ci-cmd`

---

# 🧰 BundleCraft Scripts

This folder contains helper scripts used locally and in CI.

Quick catalog:

| Script | Purpose |
|---|---|
| `detect_env_targets.py` | Discover craft targets from `config/crafts/*.yaml` (or legacy `config/envs/*.yaml`) and emit a JSON matrix for CI |
| `trust_matrix.py` | Build a Craft × Bundle trust matrix from craft configs (table/markdown/csv/json) |
| `vault-local.sh` | Spin up a local HashiCorp Vault dev instance for testing the Vault fetcher |

---

## 🔎 detect_env_targets.py

Parse `config/crafts/*.yaml` (or legacy `config/envs/*.yaml`) and output a JSON array describing the CI build matrix.

- Reads craft files for `targets: <name>.includes: [...]`
- Emits objects: `{ "env": "<craft>", "target": "<target>", "output_root": "<build_path or dist>" }`
- Used by GitHub Actions to build per craft/target

Usage:

```bash
python scripts/detect_env_targets.py > env_targets.json
cat env_targets.json
```

Example output:

```json
[
  {"env": "prod", "target": "internal", "output_root": "dist"},
  {"env": "prod", "target": "mozilla",  "output_root": "dist"}
]
```

Notes:
- If a craft defines `build_path`, it is emitted as `output_root`.
- Crafts without `targets` are ignored.

---

## 📐 trust_matrix.py

Generate a trust matrix showing which crafts (rows) trust which bundles (columns), based on `targets.<name>.includes` in `config/crafts/*.yaml`.

Supported formats:
- `table`: Unicode box table for terminals
- `markdown`: GitHub-friendly table
- `csv`: numeric matrix (1/0)
- `json`: structured data including per-craft `targets` and `trusts`

Usage:

```bash
# Terminal table
python scripts/trust_matrix.py --config-dir config --format table

# Markdown
python scripts/trust_matrix.py --format markdown --output TRUST_MATRIX.md

# JSON
python scripts/trust_matrix.py --format json --output trust-matrix.json
```

Notes:
- Trust for a craft = union of all bundles listed in its targets' `includes`.
- Legacy `bundle_targets: [...]` is supported and treated as trusted bundles.

---

## 🔐 BundleCraft: Local Vault Test Environment

This section explains how to spin up a **local HashiCorp Vault instance** for testing BundleCraft’s Vault fetch integration.

It supports two methods:
1. **Direct binary mode (recommended)** - runs the Vault binary directly on your system in dev mode.
2. **Container mode (optional)** - runs Vault in a rootless Podman container.

---

### 🚀 Overview

This test environment:
- Starts Vault in **dev mode** (temporary, unsealed, no persistence)
- Enables the PKI secrets engine at `pki/trusted_roots`
- Generates a root CA and inserts its PEM into a KV path for testing
- Provides a teardown command to clean up all local state
- Supports CI/CD automation via `--ci-cmd`

---

### 🧰 Requirements

#### Option 1: Direct Binary (Recommended)

Install Vault natively:

```bash
# Debian / Ubuntu
sudo apt-get update
sudo apt-get install -y wget gpg

# Add HashiCorp repo
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt-get update
sudo apt-get install -y vault
```

Verify:

```bash
vault version
```

#### Option 2: Podman Container (Alternative)

If you prefer isolation, install Podman:

```bash
sudo apt-get install -y podman
```

Then you can run Vault as:

```bash
podman run --rm -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=root' \
  -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
  docker.io/library/vault:latest
```

*(Podman supports rootless containers - safer and Docker-compatible syntax.)*

---

### 🧪 Usage

```bash
# Start Vault in local dev mode (binary runtime)
./vault-local.sh up --runtime binary

# Run your BundleCraft fetch after exporting env vars (see config example below)
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --craft dev --bundle local-vault

# Tear down environment
./vault-local.sh down
```

#### Auto-Cleanup

```bash
./vault-local.sh up --auto-cleanup
```

Vault will wait for you to finish, then clean up automatically.

#### CI/CD Mode

```bash
./vault-local.sh up --ci-cmd "bundlecraft fetch --craft dev --bundle local-vault"
```

Runs your test command, then removes the local Vault environment automatically.

---

### ⚙ Options

| Flag                | Description                                        |
| ------------------- | -------------------------------------------------- |
| `--runtime <mode>`  | Runtime: `binary` (default) or `podman`            |
| `--port <num>`      | Port for Vault (default 8200)                      |
| `--data-dir <path>` | Directory for Vault data (default `./local_vault`) |
| `--token <string>`  | Dev root token (default `root`)                    |
| `--image <name>`    | Vault image when using podman (default `hashicorp/vault:latest`) |
| `--auto-cleanup`    | Clean up automatically after use                   |
| `--ci-cmd "<cmd>"`  | Run command in CI mode with VAULT_* exported, then teardown |
| `--verbose`         | Enable detailed logging                            |
| `-h`, `--help`      | Show help message                                  |

---

### 🧩 Notes

- This environment is **ephemeral** - all data is lost on shutdown.
- It’s safe to run alongside an existing Vault or Podman environment.
- Default configuration listens on `http://127.0.0.1:8200`.
- The script exports `VAULT_ADDR` and `VAULT_TOKEN` internally; use `--ci-cmd` to run commands with those env vars, or export them in your shell as shown above.

---

### 🔗 BundleCraft integration example

When the script starts Vault, it configures a simple PKI test setup and writes a PEM to:

- KV mount: `secret`
- Secret path: `pki/trusted_roots`
- Field: `pem`

Configure your bundle to fetch this PEM via the Vault fetcher:

```yaml
# config/bundles/local-vault.yaml
id: local-vault
include: []
fetch:
  - name: from_vault
    type: vault
    mount_point: secret
    path: pki/trusted_roots
    pem_field: pem
    addr: http://127.0.0.1:8200
    token_ref: VAULT_TOKEN
```

And a minimal craft file:

```yaml
# config/crafts/dev.yaml
name: Dev
```

Then run:

```bash
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --craft dev --bundle local-vault
```

This will stage the local Vault-provided PEM under `sources/fetched/dev/local-vault/from_vault.pem`.

### 🥏 BundleCraft Fetch Test Suite

You can manually test all BundleCraft fetch types end-to-end using a comprehensive GitHub Actions workflow:

- **Workflow:** `.github/workflows/test-bundlecraft-fetch.yaml`
- **Trigger:** Manually, via the GitHub Actions UI ("Run workflow")
- **Architecture:** All services run in **Podman containers** for consistency and isolation
- **Test coverage:**
  - **Vault fetcher:** HashiCorp Vault container (via `vault-local.sh --runtime podman`), no binary required
  - **HTTP fetcher:** nginx container with self-signed cert, tests CA trust + TLS fingerprint pinning
  - **API fetcher:** Custom Flask mock API container (Keyfactor simulation), tests bearer token auth + HTTPS

**To use:**

1. Go to the **Actions** tab in your GitHub repository.
2. Select **"🥏 BundleCraft Fetch Test Suite"** from the workflow list.
3. Click **"Run workflow"**.

Each test job:
- Generates a temporary bundle config (e.g., `ci-test-vault.yaml`, `ci-test-http.yaml`, `ci-test-api.yaml`)
- Spins up the required containerized service (Vault, nginx, Flask API)
- Runs `bundlecraft fetch --config-file <config>` using the new `--config-file` flag
- Verifies staged outputs and provenance
- Automatically cleans up containers on completion

**Container-based approach:**
- ✅ No local dependencies (no Flask, Prism, or vault binary required)
- ✅ Clean isolation and reproducible environments
- ✅ Self-signed certificates properly handled via `ca_file` with absolute paths
- ✅ Automatic cleanup with `podman rm -f` in workflow cleanup steps

**Outputs:** All jobs stage to `sources/fetched/ci/<test-id>/` with:
- Fetched PEM files
- `provenance.fetch.json` with origin and SHA256

This workflow is a safe, modular way to validate all fetch integrations without modifying your main configs.

---

Reference:

- HashiCorp Vault official install guide: https://developer.hashicorp.com/vault/tutorials/get-started/install-binary
- Podman documentation: https://podman.io/getting-started

---
