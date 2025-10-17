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

## 🧰 Requirements

### Option 1: Direct Binary (Recommended)

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
````

Verify:

```bash
vault version
```

### Option 2: Podman Container (Alternative)

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

## 🧪 Usage

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

### Auto-Cleanup

```bash
./vault-local.sh up --auto-cleanup
```

Vault will wait for you to finish, then clean up automatically.

### CI/CD Mode

```bash
./vault-local.sh up --ci-cmd "bundlecraft fetch --env dev --bundle local-vault"
```

Runs your test command, then removes the local Vault environment automatically.

---

## ⚙ Options

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

## 🧩 Notes

* This environment is **ephemeral** — all data is lost on shutdown.
* It’s safe to run alongside an existing Vault or Podman environment.
* Default configuration listens on `http://127.0.0.1:8200`.
* The script exports `VAULT_ADDR` and `VAULT_TOKEN` internally; use `--ci-cmd` to run commands with those env vars, or export them in your shell as shown above.

---

## 🔗 BundleCraft integration example

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

---

**Reference:**

* HashiCorp Vault official install guide: [https://developer.hashicorp.com/vault/tutorials/get-started/install-binary](https://developer.hashicorp.com/vault/tutorials/get-started/install-binary)
* Podman documentation: [https://podman.io/getting-started](https://podman.io/getting-started)

---
