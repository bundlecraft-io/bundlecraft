# 🧰 BundleCraft Scripts

This folder contains helper scripts used locally and in CI.

Quick catalog:

| Script | Purpose |
|---|---|
| `detect_env_targets.py` | Discover env bundles from `config/envs/*.yaml` and emit a JSON matrix for CI |
| `trust_matrix.py` | Build a trust matrix from env configs (table/markdown/csv/json) |
| `generate_test_cas.py` | Generate self-signed test CA certificates with automatic private key disposal (TESTING ONLY) |
| `test-server-local.py` | Local HTTPS test server for CI and development with Swagger UI |
| `vault-local.py` | Spin up a local HashiCorp Vault dev instance for testing the Vault fetcher |
| `json-output-examples.sh` | Demonstration of JSON output from BundleCraft commands for CI/CD automation (requires `jq`) |

______________________________________________________________________

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

```bash
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

```bash
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

______________________________________________________________________

## 🔎 detect_env_targets.py

Parse `config/envs/*.yaml` (or legacy `config/envs/*.yaml`) and output a JSON array describing the CI build matrix.

Usage:

```bash
python scripts/detect_env_targets.py > env_targets.json
cat env_targets.json
```

Example output:

```json
[
  {"env": "prod", "bundle": "internal", "output_root": "dist"},
  {"env": "prod", "bundle": "mozilla",  "output_root": "dist"}
]
```

## 📐 trust_matrix.py

Generate a holistic trust matrix showing:

- **Environments × Bundles**: Which environments build which bundles
- **Bundles × Sources**: Which sources are included in each bundle
- **Environments × Sources**: Which sources are trusted in each environment (via any bundle)

Supported formats:

- `table`: Unicode box tables for terminals (all three mappings)
- `markdown`: GitHub-friendly tables (all three mappings)
- `csv`: numeric matrices (all three mappings)
- `json`: structured data with full mappings

Usage:

```bash
# Terminal tables (all mappings)
python scripts/trust_matrix.py --config-dir config --format table

# Markdown tables
python scripts/trust_matrix.py --format markdown --output TRUST_MATRIX.md

# JSON
python scripts/trust_matrix.py --format json --output trust-matrix.json
```

Output includes:

- **[Environments × Bundles]**: ✔ if bundle is built in environment
- **[Bundles × Sources]**: ✔ if source is included in bundle
- **[Environments × Sources]**: ✔ if source is trusted in environment (via any bundle)

JSON output provides:

- `environments`: mapping of environment → bundles, sources, bundle_sources
- `bundles`: mapping of bundle → sources
- `sources`: list of all sources

This gives a one-stop view of how environments, bundles, and sources relate in your BundleCraft config.

______________________________________________________________________

## 📋 json-output-examples.sh

Demonstration script showing how to use BundleCraft's `--json` flag for CI/CD automation and programmatic consumption.

**Purpose:** Provides working examples of JSON output parsing with `jq` for all BundleCraft commands.

**Requirements:**

- `jq` - Command-line JSON processor (`sudo apt-get install jq` or `brew install jq`)

**Usage:**

```bash
# Run all examples
./scripts/json-output-examples.sh

# Or run individual commands manually
bundlecraft fetch --source-config-file config/cert_sources/mozilla.yaml --dry-run --json | jq .
bundlecraft verify --target tests/data/certs/sample.pem --json | jq '.success'
```

**What it demonstrates:**

- Fetch, convert, and verify commands with `--json` output
- Extracting specific fields with `jq` (e.g., `.success`, `.errors[]`)
- Error handling patterns for CI/CD pipelines
- Parsing structured responses for automation

**Example output parsing:**

```bash
# Check if operation succeeded
SUCCESS=$(bundlecraft fetch ... --json | jq -r '.success')
if [ "$SUCCESS" = "true" ]; then
  echo "✅ Operation succeeded"
fi

# Extract errors
bundlecraft build ... --json | jq -r '.errors[]'
```

See [JSON Output Schemas](../docs/JSON-OUTPUT.md) for complete schema documentation.

______________________________________________________________________

## 🌎 test-server-local.py

A self-contained HTTPS Flask server used for local testing of HTTP and API based Fetch modules. It provides:

- A friendly HTML homepage at `/`
- A plain HTTP download endpoint at `/test-cert.pem`
- A token-protected API endpoint at `/Certificates/Download` (Keyfactor-like)
- Built-in Swagger UI at `/apidocs`

Key features:

- Generates ephemeral TLS cert/key and stores them in a temp dir
- Prints the homepage URL first for convenience
- Runs Flask in its own process group for reliable shutdown
- Uses your project `virtualenv` Python if available

Usage

- Start in background (default):

  ```bash
  ./scripts/test-server-local.py up --port 8443 --token mock-token-12345
  ```

- Stop background server:

  ```bash
  ./scripts/test-server-local.py down
  ```

- Run in foreground:

  ```bash
  ./scripts/test-server-local.py serve --port 8443 --token mock-token-12345
  ```

Notes

- TLS material and a small flask log file are stored under `/tmp/test-server-local-<random>`.
- The latest instance directory is tracked at `/tmp/test-server-local-latest`.
- The CA certificate is at `<data_dir>/server.crt` for trusting the server in tests.
- The API expects `Authorization: Bearer <TOKEN>` and a JSON body like `{ "CertID": 12345, "CertificateFormat": "PEM", "IncludeChain": true }`.

## 🛡️ vault-local.py

Helper to run a local [HashiCorp Vault](https://developer.hashicorp.com/vault) server, with an option to run a post-start CI command. Useful for testing Vault-based fetch modules.

The script will use a local installation of the `vault` binary if available, but it also supports starting Vault via a Podman container. Either one of the two dependencies (as well as availability to retrieve the Vault image in the case of the latter) is needed to run the script.

### Option 1: Install Vault Binary

```bash
wget -O- <https://apt.releases.hashicorp.com/gpg> | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] <https://apt.releases.hashicorp.com> $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt-get update
sudo apt-get install -y vault

vault version
```

### Option 2: Install Podman Runtime

```bash
sudo apt-get install -y podman

# Then you can run Vault as:

# podman run --rm -p 8200:8200 \
#   -e 'VAULT_DEV_ROOT_TOKEN_ID=root' \
#   -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
#   docker.io/library/vault:latest
```

### 🧪 Script Usage

```bash
# Start Vault in local dev mode (binary runtime)
./vault-local.py up --runtime binary

# Run your BundleCraft fetch after exporting env vars (see config example below)
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --env dev --bundle local-vault

# Tear down environment
./vault-local.py down
```

#### CI/CD Mode

```bash
./vault-local.py up --runtime podman --ci-cmd "bundlecraft fetch --env dev --bundle local-vault"
```

Runs your test command, then removes the local Vault environment automatically.

### ⚙ Options

| Flag | Description |
| ------------------- | -------------------------------------------------- |
| `--runtime <mode>` | Runtime: `binary` (default) or `podman` |
| `--port <num>` | Port for Vault (default 8200) |
| `--data-dir <path>` | Directory for Vault data (default `./local_vault`) |
| `--token <string>` | Dev root token (default `root`) |
| `--image <name>` | Vault image when using podman (default `hashicorp/vault:latest`) |
| `--auto-cleanup` | Clean up automatically after use |
| `--ci-cmd "<cmd>"` | Run command in CI mode with VAULT\_\* exported, then teardown |
| `--verbose` | Enable detailed logging |
| `-h`, `--help` | Show help message |

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

And a minimal env file:

```yaml
# config/envs/dev.yaml
name: dev
description: dev environment trusting vault cert authority
bundles:
  vault-bundle:
    include_sources: [from_vault]

```

Then run:

```bash
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"
bundlecraft fetch --env dev --bundle vault-bundle
```

This will stage the local Vault-provided PEM under `cert_sources/staged/<source_name>/fetch/from_vault/from_vault.pem`.

References:

- [HashiCorp Vault KV secrets engine API docs](https://developer.hashicorp.com/vault/api-docs/secret/kv/kv-v2)
- [The hvac Python library docs](https://python-hvac.org/en/stable/overview.html)
