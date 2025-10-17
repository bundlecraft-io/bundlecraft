# 🧰 BundleCraft Scripts

This folder contains helper scripts used locally and in CI.

Quick catalog:

| Script | Purpose |
|---|---|
| `detect_env_targets.py` | Discover environment targets from `config/envs/*.yaml` and emit a JSON matrix for CI |
| `trust_matrix.py` | Build an Environment × Bundle trust matrix from env configs (table/markdown/csv/json) |
| `vault-local.sh` | Spin up a local HashiCorp Vault dev instance for testing the Vault fetcher |


## 🔎 detect_env_targets.py

Parse `config/envs/*.yaml` and output a JSON array describing the CI build matrix.


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

Generate a trust matrix showing which environments (rows) trust which bundles (columns), based on `targets.<name>.includes` in `config/envs/*.yaml`.

Supported formats:

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


## 🔐 BundleCraft: Local Vault Test Environment

This section explains how to spin up a **local HashiCorp Vault instance** for testing BundleCraft’s Vault fetch integration.

It supports two methods:
1. **Direct binary mode (recommended)** — runs the Vault binary directly on your system in dev mode.
2. **Container mode (optional)** — runs Vault in a rootless Podman container.


### 🚀 Overview

This test environment:


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

*(Podman supports rootless containers — safer and Docker-compatible syntax.)*


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

And a minimal environment file:

```yaml
# config/envs/dev.yaml
name: Dev
```

Then run:

```bash
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --env dev --bundle local-vault
```

This will stage the local Vault-provided PEM under `sources/fetched/dev/local-vault/from_vault.pem`.


Reference:


# BundleCraft: Local Vault Test Environment

This document explains how to spin up a **local HashiCorp Vault instance** for testing BundleCraft’s Vault fetch integration.

It supports two methods:
1. **Direct binary mode (recommended)** — runs the Vault binary directly on your system in dev mode.
2. **Container mode (optional)** — runs Vault in a rootless Podman container.

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
| `detect_env_targets.py` | Discover environment targets from `config/envs/*.yaml` and emit a JSON matrix for CI |
| `trust_matrix.py` | Build an Environment × Bundle trust matrix from env configs (table/markdown/csv/json) |
| `vault-local.sh` | Spin up a local HashiCorp Vault dev instance for testing the Vault fetcher |

---

## 🔎 detect_env_targets.py

Parse `config/envs/*.yaml` and output a JSON array describing the CI build matrix.

- Reads env files for `targets: <name>.includes: [...]`
- Emits objects: `{ "env": "<env>", "target": "<target>", "output_root": "<build_path or dist>" }`
- Used by GitHub Actions to build per environment/target

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
- If an environment defines `build_path`, it is emitted as `output_root`.
- Environments without `targets` are ignored.

---

## 📐 trust_matrix.py

Generate a trust matrix showing which environments (rows) trust which bundles (columns), based on `targets.<name>.includes` in `config/envs/*.yaml`.

Supported formats:
- `table`: Unicode box table for terminals
- `markdown`: GitHub-friendly table
- `csv`: numeric matrix (1/0)
- `json`: structured data including per-env `targets` and `trusts`

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
- Trust for an env = union of all bundles listed in its targets' `includes`.
- Legacy `bundle_targets: [...]` is supported and treated as trusted bundles.

---

## 🔐 BundleCraft: Local Vault Test Environment

This section explains how to spin up a **local HashiCorp Vault instance** for testing BundleCraft’s Vault fetch integration.

It supports two methods:
1. **Direct binary mode (recommended)** — runs the Vault binary directly on your system in dev mode.
2. **Container mode (optional)** — runs Vault in a rootless Podman container.

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

*(Podman supports rootless containers — safer and Docker-compatible syntax.)*

---

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

- This environment is **ephemeral** — all data is lost on shutdown.
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

And a minimal environment file:

```yaml
# config/envs/dev.yaml
name: Dev
```

Then run:

```bash
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --env dev --bundle local-vault
```

This will stage the local Vault-provided PEM under `sources/fetched/dev/local-vault/from_vault.pem`.

### 🥏 BundleCraft Fetch Test Suite

You can manually test all BundleCraft fetch types end-to-end using a comprehensive GitHub Actions workflow:

- **Workflow:** `.github/workflows/test-bundlecraft-fetch.yaml`
- **Trigger:** Manually, via the GitHub Actions UI ("Run workflow")
- **Test coverage:**
  - **Vault fetcher:** Spins up local Vault dev server, fetches PEM from KV secret
  - **HTTP fetcher:** Flask HTTPS server with self-signed cert, tests TLS fingerprint pinning
  - **API fetcher:** Prism mock of Keyfactor API (from OpenAPI spec), tests bearer token auth

**To use:**

1. Go to the **Actions** tab in your GitHub repository.
2. Select **"🥏 BundleCraft Fetch Test Suite"** from the workflow list.
3. Click **"Run workflow"**.

Each test job:
- Generates a temporary bundle config (e.g., `ci-test-vault.yaml`, `ci-test-http.yaml`, `ci-test-api.yaml`)
- Spins up the required service (Vault, Flask, Prism)
- Runs `bundlecraft fetch --config-file <config>` using the new `--config-file` flag
- Verifies staged outputs and provenance

**Outputs:** All jobs stage to `sources/fetched/ci/<test-id>/` with:
- Fetched PEM files
- `provenance.fetch.json` with origin and SHA256

This workflow is a safe, modular way to validate all fetch integrations without modifying your main configs.

---

Reference:

- HashiCorp Vault official install guide: https://developer.hashicorp.com/vault/tutorials/get-started/install-binary
- Podman documentation: https://podman.io/getting-started

---
