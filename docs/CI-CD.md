# BundleCraft CI/CD Workflows

BundleCraft includes four GitHub Actions workflows for automated testing, building, and releasing.

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

See [docs/SIGNING-AND-SBOM.md](SIGNING-AND-SBOM.md) for complete verification instructions.

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

Discover which environment/bundle combinations to build using the built-in CLI discovery:

- Use `bundlecraft build-all --print-plan` to list environments to build
- Scans `config/envs/*.yaml` by default; scope with `--envs-path` to target subfolders or globs
- Add `--recursive` to discover configs in nested subdirectories (e.g., `config/envs/**/*.yaml`)
- Emit JSON with `--json` for easy matrix generation
- Validate selection and provide summary before building

Examples:

```bash
# Discover all envs under config/envs/
bundlecraft build-all --print-plan --json

# Discover only envs under config/envs/teamA/
bundlecraft build-all --envs-path teamA --print-plan --json

# Discover envs matching a glob
bundlecraft build-all --envs-path "teamA/*.yaml" --print-plan --json

# Recursively discover all envs in subdirectories
bundlecraft build-all --recursive --print-plan --json

# Combine recursive with scoping
bundlecraft build-all --envs-path teamA --recursive --print-plan --json
```

The JSON document contains a simple list of environments and their resolved paths, suitable for transforming into a GitHub Actions matrix.

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

Creates GitHub Release with signed artifacts and certificate diff:

- Generates timestamped release tag (`bundlecraft-truststore-v<YYYY.MM.DD-HHMM>`)
- **Compares with previous release to generate certificate diff report**
- **Includes detailed summary of added/removed certificates in release notes**
- Optionally signs artifacts with GPG (if `GPG_PRIVATE_KEY` secret is configured)
- Attaches all tarballs, checksums, and signatures
- Includes trust matrix (certificate inventory by environment/bundle)
- Includes certificate diff report (CERT_DIFF.md)
- Provides verification instructions in release notes
- Supports both signed and unsigned releases

**Certificate Diff in Release:**

The release automatically includes a detailed comparison with the previous release showing:

- Summary table of changes per bundle (added/removed/unchanged counts)
- Collapsible sections with full certificate details for added certificates
- Collapsible sections with full certificate details for removed certificates
- Overall totals across all bundles
- First release detection (no comparison if this is the first release)

**Example Release Notes Section:**

```markdown
## 📊 Certificate Changes Summary

Compared to previous release: `bundlecraft-truststore-v2025.10.20-1500`

| Environment | Bundle | Added | Removed | Unchanged |
|------------|--------|-------|---------|-----------|
| `production` | `internal` | 2 | 1 | 41 |
| `production` | `mozilla` | 0 | 0 | 142 |

**Overall:** 2 certificates added, 1 certificates removed across all bundles.

## 📋 Detailed Changes by Bundle

### 📦 production/internal

**Changes:** 2 added, 1 removed, 41 unchanged

<details>
<summary>➕ Added Certificates (2)</summary>

[Certificate details...]
</details>

<details>
<summary>➖ Removed Certificates (1)</summary>

[Certificate details...]
</details>
```

**Workflow inputs:**

- `envs_path` (optional): Path or glob to limit discovery (e.g., `teamA`, `teamA/*.yaml`)
- Optionally process the plan JSON to further filter or shard builds at the workflow level

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

## 🔍 Certificate Bundle Diff on PR

**Workflow:** `.github/workflows/pr-cert-diff.yaml`

**Purpose:** Automatically compare certificate bundles between PR branch and base branch, posting detailed diff reports as PR comments.

**Trigger:**

- Automatic on pull requests to `main` or `develop` branches
- Only when certificate sources or configs are modified

**What it does:**

1. Builds bundles from both PR branch and base branch
1. Compares bundles using `bundlecraft diff`
1. Generates human-readable and JSON diff reports
1. Posts formatted comment to PR with certificate changes
1. Uploads full diff reports as workflow artifacts

**Features:**

- **Smart detection** - Automatically identifies which environments/bundles to compare
- **Change summary** - Shows added, removed, and unchanged certificate counts
- **Detailed reports** - Collapsible sections with full certificate details
- **Artifact upload** - Complete diff reports available for download
- **Update existing comments** - Edits previous bot comments instead of creating new ones
- **Optional validation** - Can be configured to fail builds on unexpected changes

**PR Comment Example:**

```markdown
## 🔐 Certificate Bundle Changes

This PR modifies certificate bundles. Review the changes below:

### 📦 Environment: `production` / Bundle: `internal`

**Summary:**
- ➕ Added: 2
- ➖ Removed: 1
- ↔️ Unchanged: 41

<details>
<summary>➕ Added Certificates (2)</summary>

Subject: CN=New Corporate Root CA 2025,O=Example Corp,C=US
Fingerprint: a1b2c3d4e5f6...
Valid: 2025-01-01T00:00:00+00:00 to 2045-01-01T00:00:00+00:00
</details>

⚠️ **Action Required:** Review the certificate changes above before merging.
```

**Configuration options:**

- Customize validation rules (e.g., max certificates removed)
- Filter specific environments to compare
- Adjust artifact retention period

**Use cases:**

- Pre-merge review of certificate changes
- Automated change documentation
- Compliance and audit trail for trust policy modifications
- Prevent accidental certificate removals

______________________________________________________________________

## Best Practices

### For Development

1. Run **PyTest Suite** automatically on all branches via push/PR
1. Use **Certificate Bundle Diff on PR** to review certificate changes before merging
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
