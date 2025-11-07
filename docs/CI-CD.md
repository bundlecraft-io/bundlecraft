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

## 📦 BundleCraft Release Workflow

**Workflow:** `.github/workflows/release.yaml`

**Purpose:** Automated build, signing, and publishing of BundleCraft package releases to PyPI, TestPyPI, and GHCR.

**Trigger:** Automatic on version tags (`v*`)

**Release Channels:**

- **Production** (`main` branch): Tags like `v1.2.3` → PyPI + GHCR
- **Pre-release** (`pre-release` branch): Tags like `v1.2.3-beta.1` → TestPyPI + GHCR

**Workflow Stages:**

### 1. Branch Detection & Validation

- Determines which branch the tag originated from
- Validates tag format (semantic versioning)
- Sets release channel (main or pre-release)

### 2. Testing & Quality Checks

- Runs full pytest suite with coverage
- Executes ruff linting
- Pre-release: Runs BundleCraft Fetch integration tests (non-blocking)

### 3. Package Building

- Builds Python wheel (`.whl`) and source distribution (`.tar.gz`)
- Updates changelog URL in package metadata
- Validates distributions with twine

### 4. Container Image Building

- Builds multi-platform container images
- Tags images with version and semantic version tags
- Production: `ghcr.io/bundlecraft-io/bundlecraft:X.Y.Z`, `:latest`
- Pre-release: `ghcr.io/bundlecraft-io/bundlecraft-test:X.Y.Z-beta.N`, `:pre-release`

### 5. Sigstore Signing & Attestations

**Container Images:**

- Signs images with [cosign](https://docs.sigstore.dev/cosign/) using keyless OIDC
- Uses GitHub Actions identity for signing
- Verifies signatures post-signing
- Records signatures in Rekor transparency log

**Python Packages:**

- Generates build provenance attestations with `actions/attest-build-provenance`
- Enables Sigstore attestations in PyPI publishing
- Links packages to specific source code and workflow

**Benefits:**

- No private key management required
- Identity-based signing tied to GitHub Actions
- Transparent and auditable (Rekor log)
- SLSA compliant build provenance

### 6. Publishing

**Production (main branch):**

- PyPI: [https://pypi.org/project/bundlecraft/](https://pypi.org/project/bundlecraft/)
- GHCR: [https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft](https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft)
- GitHub Release with artifacts and release notes

**Pre-release (pre-release branch):**

- TestPyPI: [https://test.pypi.org/project/bundlecraft/](https://test.pypi.org/project/bundlecraft/)
- GHCR: [https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft-test](https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft-test)
- GitHub Pre-Release with installation instructions

### 7. Post-Release Verification

- Installs package from PyPI/TestPyPI
- Runs smoke tests (`bundlecraft --version`, `bundlecraft --help`)
- Confirms package availability and functionality

**Verifying Signed Releases:**

```bash
# Verify container image signature
cosign verify ghcr.io/bundlecraft-io/bundlecraft:latest \
  --certificate-identity-regexp="https://github.com/bundlecraft-io/bundlecraft" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com

# Or use the Makefile helper
make verify-signatures

# Verify PyPI package attestations (pip >= 24.2 required)
pip install --require-attestations bundlecraft
```
