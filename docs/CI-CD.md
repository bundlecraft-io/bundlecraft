# BundleCraft CI/CD Workflows

BundleCraft includes three GitHub Actions workflows for automated testing, building, and releasing CA trust bundles.

______________________________________________________________________

## 🧪 BundleCraft PyTest Suite

**Workflow:** `.github/workflows/test-pytest.yaml`

**Purpose:** Runs the full pytest test suite with coverage reporting on every push and pull request.

**Trigger:**

- Automatic on push to `main` or `develop` branches (except PR merge commits)
- Automatic on pull requests targeting `main` or `develop`

**What it does:**

1. Sets up Python 3.11 environment
1. Installs BundleCraft in editable mode with dev dependencies
1. Runs pytest with verbose output and short tracebacks
1. Generates coverage reports (XML and terminal)
1. Uploads coverage to Codecov (optional, won't fail CI if upload fails)

**Use cases:**

- Validate all code changes before merging
- Ensure test coverage doesn't regress
- Continuous quality assurance

______________________________________________________________________

## 🥏 BundleCraft Fetch Test Suite

**Workflow:** `.github/workflows/test-bundlecraft-fetch.yaml`

**Purpose:** End-to-end integration testing of all BundleCraft fetch types using containerized services.

**Trigger:** Manual, via GitHub Actions UI ("Run workflow")

**What it tests:**

- **Vault Fetcher** - HashiCorp Vault KV engine (v1 and v2)
- **HTTP Fetcher** - HTTPS with CA file trust and TLS fingerprint pinning
- **API Fetcher** - Bearer token authentication (Keyfactor-style mock API)

**Architecture:**

- All services run in **Podman containers** for consistency and isolation
- No local dependencies required (no Flask, Vault binary, etc.)
- Self-signed certificates properly handled via `ca_file` with absolute paths
- Automatic cleanup with `podman rm -f` in workflow cleanup steps

**How it works:**

Each test job (Vault, HTTP, API):

1. Generates a temporary source config (`ci-test-vault.yaml`, `ci-test-http.yaml`, `ci-test-api.yaml`)
1. Spins up the required containerized service
1. Runs `bundlecraft fetch --source-config-file <config.yaml> --json`
1. Verifies staged outputs exist at `cert_sources/staged/<source-name>/fetch/<fetch-name>/`
1. Checks for PEM file and provenance JSON
1. Cleans up containers on completion

**Outputs:**

- Fetched PEM files: `<fetch-name>.pem`
- Provenance metadata: `provenance.fetch.json` (with origin URL/config and SHA256)

**To use:**

1. Go to the **Actions** tab in your GitHub repository
1. Select **"🥏 BundleCraft Fetch Test Suite"** from the workflow list
1. Click **"Run workflow"**
1. Optionally filter by test type (vault, http, api) via workflow input

**Benefits:**

- ✅ Safe, modular validation without modifying main configs
- ✅ Clean isolation and reproducible environments
- ✅ Tests real-world scenarios (authentication, TLS verification, etc.)

______________________________________________________________________

## 🧱 BundleCraft CA Trust Pipeline

**Workflow:** `.github/workflows/bundlecraft.yaml`

**Purpose:** Complete build, verification, and release pipeline for production CA trust bundles.

**Trigger:** Manual, via GitHub Actions UI ("Run workflow")

**Workflow stages:**

### 1. Discover

Discovers which environment/bundle combinations to build:

- Scans `config/envs/*.yaml` for environment configurations
- Filters by optional `environments` input (comma-separated)
- Only includes environments with `github-release` enabled
- Outputs JSON matrix for parallel builds
- Validates environment selection and provides summary

### 2. Build

Builds trust bundles in parallel using matrix strategy:

- One job per environment/bundle combination
- Runs `bundlecraft build --env <env> --bundle <bundle>`
- Validates output exists and matches expected structure
- Uploads each bundle as a separate artifact (`trust-store-<env>-<bundle>`)

### 3. Collect

Collects and packages all build artifacts:

- Downloads all per-bundle artifacts
- Rehydrates to `bundlecraft/<env>/<bundle>/` directory structure
- Creates combined tarball: `bundlecraft-trust.tar.gz`
- Creates per-bundle tarballs: `bundlecraft-trust-env-<env>-bundle-<bundle>.tar.gz`
- Generates SHA256 checksums for all tarballs
- Generates trust matrix artifacts (Markdown and JSON)

### 4. Verify

Verifies integrity of built bundles:

- Runs `bundlecraft verify` on all bundles in combined directory
- Extracts and verifies combined tarball
- Ensures all checksums, manifests, and certificates are valid

### 5. Publish Release

Creates GitHub Release with signed artifacts:

- Generates timestamped release tag (`bundlecraft-truststore-v<YYYY.MM.DD-HHMM>`)
- Optionally signs artifacts with GPG (if `GPG_PRIVATE_KEY` secret is configured)
- Attaches all tarballs, checksums, and signatures
- Includes trust matrix (certificate inventory by environment/bundle)
- Provides verification instructions in release notes
- Supports both signed and unsigned releases

**Workflow inputs:**

- `environments` (optional): Comma-separated list of environments to build (e.g., "dev,prod")
  - Leave blank to build all environments with GitHub release enabled

**Concurrency:**

- Uses branch-based concurrency groups
- Cancels in-progress runs when new workflow is triggered

**Artifacts produced:**

- **Combined tarball:** `bundlecraft-trust.tar.gz` (all environments and bundles)
- **Per-bundle tarballs:** `bundlecraft-trust-env-<env>-bundle-<bundle>.tar.gz` (flat structure)
- **Checksums:** `.sha256` files for all tarballs
- **GPG signatures:** `.asc` files (if signing enabled)
- **Trust matrix:** `TRUST_MATRIX.md` and `trust-matrix.json`

**Release artifacts include:**

- Canonical PEM bundles (`.pem`)
- Additional formats: PKCS#7 (`.p7b`), PKCS#12 (`.p12`), JKS (`.jks`) - when configured
- `checksums.sha256` - SHA256 hashes of all files in bundle
- `manifest.json` - Certificate inventory with metadata
- `sbom.json` - CycloneDX Software Bill of Materials

**Use cases:**

- Production trust bundle releases
- Scheduled or on-demand bundle updates
- Auditable, signed releases with provenance

______________________________________________________________________

## Best Practices

### For Development

1. Run **PyTest Suite** automatically on all branches via push/PR
1. Use **Fetch Test Suite** manually when testing new fetch sources or configurations
1. Test locally before pushing with `pytest` and `bundlecraft build --dry-run`

### For Production

1. Use **CA Trust Pipeline** for official releases
1. Enable GPG signing by configuring `GPG_PRIVATE_KEY` and `GPG_PASSPHRASE` secrets
1. Filter environments to build specific subsets (e.g., "prod" only for hotfixes)
1. Review trust matrix in release notes before distribution

### Security Considerations

- All workflows run in isolated GitHub-hosted runners
- Secrets are only exposed to specific steps that need them
- Artifacts are automatically cleaned up after 90 days (configurable)
- GPG signatures provide release authenticity and integrity verification

______________________________________________________________________

## References

- **Podman Documentation:** <https://podman.io/getting-started>
- **HashiCorp Vault:** <https://developer.hashicorp.com/vault/tutorials/get-started/install-binary>
- **GitHub Actions:** <https://docs.github.com/en/actions>
