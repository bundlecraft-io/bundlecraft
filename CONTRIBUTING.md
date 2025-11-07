# 🧩 Contributing to BundleCraft

A concise guide to contributing changes to BundleCraft, interacting with the code in this repository, and releasing new package versions.

______________________________________________________________________

## ⚡ Quickstart

Contributing code:

```bash
# 1. Clone the repo
git clone https://github.com/bundlecraft-io/bundlecraft.git
cd bundlecraft

# 2. Set up your dev environment
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
make setup-dev  # Installs dependencies + configures git hooks + pre-commit

# Alternative manual setup:
# pip install -e ".[dev]"
# git config core.hooksPath .githooks
# pre-commit install

# 3. Create a feature branch
git checkout -b feature/my-awesome-feature

# 4. (Optional) Generate minimal sample configs for testing
scripts/prepare_test_configs.sh

# 5. Make changes, test locally
bundlecraft build --env test-example-envconfig --verbose

# 6. Test a pypi/container build with your changes:
make test-image-build   # container, requires podman/docker
make test-pypi-build    # pypi package

# 7. Test and lint code
pytest -v
make ci-lint  # runs: ruff check bundlecraft tests

# 9. Commit and open PR to pre-release (address pre-commit findings too if any)
git add .
git commit -m "feat: describe your feature"
git push origin feature/my-awesome-feature
# Open PR on GitHub targeting pre-release branch
```

**Releasing a new version?** Once your change has been merged to the pre-release branch, you can tag it as a new alpha/beta version and deploy a new pre-release. See ## TODO ## for more details.

______________________________________________________________________

## 📚 Understanding the Codebase

Before diving into specific changes, here's what you need to know about how BundleCraft is organized.

### Repository Structure

Legend:

- [core] Included in the published Python package (wheel/sdist)
- [config] BundleCraft configuration used to build bundles (not packaged)
- [support] Helper scripts and repo infrastructure (not packaged)

```shell
bundlecraft/
├── bundlecraft/           # [core] Main Python package
│   ├── cli.py             # [core] CLI entrypoint
│   ├── builder.py         # [core] Build orchestration
│   ├── fetch.py           # [core] Fetch/staging layer
│   ├── verifier.py        # [core] Verification logic
│   ├── converter.py       # [core] Format conversion
│   ├── differ.py          # [core] Bundle comparison
│   ├── fetchers/          # [core] Remote source fetchers
│   └── helpers/           # [core] Internal utilities
├── config/                # [config] Configuration files
│   ├── defaults.yaml      # [config] Global defaults
│   ├── envs/              # [config] Environment definitions
│   └── sources/           # [config] Cert sources definitions
├── cert_sources/          # [config] Certificate sources
│   ├── internal/          # [config] Committed certificates
│   └── staged/            # [config] Fetched certificates (ephemeral)
├── dist/                  # [support] Build outputs (gitignored)
├── build_cache/           # [support] Cache used during builds (gitignored)
├── tests/                 # [support] Test suite
├── docs/                  # [support] Documentation and ADRs
├── scripts/               # [support] Helper scripts
├── personal-tests/        # [support] Local scratch/testing assets (not used by CI)
├── .github/               # [support] CI workflows and issue templates
├── .githooks/             # [support] Git hooks (e.g., pre-push)
├── Dockerfile             # [support] Container build
├── Makefile               # [support] Local build/test helpers
├── LICENSE                # [support] License
├── pyproject.toml         # [core] Project metadata / build config
├── pytest.ini             # [support] Pytest config
├── CODE_OF_CONDUCT.md     # [support] Community guidelines
├── CONTRIBUTING.md        # [support] This file
├── SECURITY.md            # [support] Security policy
└── README.md              # [support] Main documentation (used on PyPI page)
```

### Key Modules Explained

#### Core Modules (`bundlecraft/`)

- `cli.py` – Main CLI entrypoint; aggregates all subcommands
- `builder.py` – Build orchestration (fetch → convert → verify)
- `fetch.py` – Fetch/staging layer for remote sources
- `verifier.py` – Certificate verification and manifest validation
- `converter.py` – Format conversion (PEM → JKS/P12/P7B/ZIP)
- `differ.py` – Bundle comparison and diff reports

#### Fetchers (`bundlecraft/fetchers/`)

- `http.py` – HTTPS/file:// URL fetcher
- `api.py` – Generic API fetcher (Keyfactor, etc.)
- `vault.py` – HashiCorp Vault KV fetcher

#### Helpers (`bundlecraft/helpers/`)

- `utils.py` – Core utilities (filters, merging, config loading)
- `config_schema.py` – Pydantic validation schemas for all configs
- `convert_utils.py` – Format conversion helpers
- `verify_utils.py` – Verification utilities
- `atomic_build.py` – Atomic build context manager
- `sbom.py` – SBOM generation (CycloneDX format)
- `signing.py` – GPG signing utilities
- `exit_codes.py` – Exit code constants
- `json_output.py` – JSON output formatting

#### Configuration

- `config/defaults.yaml` – Global defaults for all envs/sources
- `config/envs/*.yaml` – Environment definitions (bundles, filters, verify policies)
- `config/sources/*.yaml` – Bundle definitions (sources, fetch specs)

______________________________________________________________________

## Contributing Code Changes

This section covers how to develop features or fixes and merge them into the `pre-release` branch for staging.

### Overview

1. Create a feature/bugfix branch
2. Make and test your changes locally
3. Open a PR to merge into `pre-release`
4. PR gets reviewed and merged

**Note:** Changes go to `pre-release` first, not `main`. The `main` branch only receives merges from `pre-release` during official releases.

______________________________________________________________________

### Step 1: Get the code

Fork the repo on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/bundlecraft.git
cd bundlecraft
```

Or if you have write access, clone directly:

```bash
git clone https://github.com/bundlecraft-io/bundlecraft.git
cd bundlecraft
```

### Step 2: Set up your environment

Ensure some useful system dependencies:

```bash
# Optional: jq (required for scripts/json-output-examples.sh)
sudo apt-get install jq

# Optional: misc system dependencies, not needed by bundlecraft
# But, can be useful for overall cert + keystore + crypto testing
sudo apt-get install openssl     # general cert/key operations
sudo apt-get install openjdk-21-jdk-headless     # keytool for java stores

```

Create a virtual environment and install everything you need:

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

# Install with runtime dependencies
pip install -e .

# Or install with dev/test tools
pip install -e ".[dev]"
```

This installs:

- The `bundlecraft` CLI in editable mode (your code changes take effect immediately)
- Optional fetcher dependencies (i.e. hvac for HashiCorp Vault)
- Optional development tools (black, ruff, pytest)

> **Tip:** Keep your output directory named `dist/` (not `build/`) to avoid conflicts with Python's build tool.

#### Shell Completion (Optional)

BundleCraft uses Click's shell completion. To enable tab completion for commands, subcommands, and flags during development:

```bash
# Bash - run in your current shell (or add to ~/.bashrc for persistence)
eval "$(_BUNDLECRAFT_COMPLETE=bash_source bundlecraft)"

# Zsh - run in your current shell (or add to ~/.zshrc for persistence)
eval "$(_BUNDLECRAFT_COMPLETE=zsh_source bundlecraft)"
```

**Notes:**

- Run this **after** activating your venv
- Completion works for all subcommands (`build`, `verify`, `convert`, etc.) and their flags
- For persistence, add the `eval` line to your shell's rc file (`~/.bashrc` or `~/.zshrc`)
- If completion stops working, re-run the `eval` command

### Step 3: Configure Repository (when testing builds/fetches)

> Tip: To skip manual setup for a quick smoke test, run `scripts/prepare_test_configs.sh`.
> This creates minimal example configs with inline test certs at:
>
> - `config/sources/.test-example-sourcecfg.yaml`
> - `config/envs/.test-example-envconfig.yaml`
>
> Clean up with `scripts/prepare_test_configs.sh --cleanup`.

#### Prepare Certificate Source Configurations

- Bring your own certs, or use `scripts/generate_test_cas.py` to generate some **TEST** CA certificates.
- Place PEM files in appropriate folders under `cert_sources/`
- Update `config/sources/` YAMLs to specify what certificates each source will be comprised of
- Optionally add a `fetch:` section to stage certificates from trusted remote origins (HTTPS/API/Vault, etc..)

#### Prepare Certificate Environment Configurations

- Update `config/envs/` YAMLs to specify which sources to include into which bundles
- Define where each environment/bundle is meant to be bundled
- Optionally add various filters and parameters to the final output of the trust store build.

### Step 4: Make your changes

Create or checkout a branch depending on what you're trying to do:

```bash
# Add a new feature
git checkout -b feature/my-awesome-feature

# Fix a bug or problem
git checkout -b bugfix/my-awesome-fix

# Checkout pre-release branch to tag and trigger a pre-release
git checkout pre-release

# Checkout main branch to tag and trigger a main
git checkout main
```

Now you can:

- Edit code in `bundlecraft/`
- Update docs in `docs/` or the README
- Add tests in `tests/`

### Step 5: Test core changes

Run the CLI to see your changes in action:

```bash
bundlecraft build --env test-example-envconfig --verbose
```

Run the pytest suite:

```bash
pytest -v
```

**PROTIP:** consider adding an accompanying test if any BundleCraft functionality has been added/modified ☺️

Format and lint your code (the pre-commit hook will also do this):

```bash
black .
ruff check . --fix
```

### Step 6: Local build/test shortcuts

For a quick end-to-end smoke test of the built wheel and container, the Makefile provides a few simple helpers:

```bash
# Build a local container image and smoke-test it
make build-test-image
make test-image-version  # runs 'bundlecraft --version' in the container
make test-image-build    # builds + verifies using inline test configs
make test-image-run      # run the image with your own args (i.e. BUNDLECRAFT_ARGS='build-all')

# Build a local wheel/sdist and smoke-test it in a temp venv
make build-test-pypi
make test-pypi-version   # prints installed version from the wheel
make test-pypi-build     # builds + verifies using inline test configs
make test-pypi-run       # run the package with your own args (i.e. BUNDLECRAFT_ARGS='build-all')
```

Notes:

- These targets do not publish anything; they're strictly local tests.
- The inline configs are created/cleaned by `scripts/prepare_test_configs.sh`.

### Step 8: Commit and push

```bash
git add .
git commit -m "fix: describe what you fixed"
git push origin fix-something-awesome
```

### Step 9: Open a Pull Request

Go to GitHub and open a PR from your branch to `pre-release`. In your PR description:

- Explain what changed and why
- Link any related issues
- Note how to test/verify the change

Maintainers will review, provide feedback, and merge when ready. PRs are squash-merged to keep history clean.

______________________________________________________________________

## 🧪 Testing Your Changes

### Running the CLI

Once you have bundle and environment configs, test the CLI directly:

```bash
# Full build pipeline
bundlecraft build --env test-example-envconfig

# Individual stages
bundlecraft fetch --source-config-file config/sources/.test-example-sourcecfg.yaml
bundlecraft convert --input dist/.test-inline/bundlecraft-ca-trust.pem --output-dir dist/.test-inline
bundlecraft verify --target dist/.test-inline --verify-all
bundlecraft diff --from cert_sources/staged/internal/rootCA.pem --to dist/.test-inline/bundlecraft-ca-trust.pem
```

Get help on any command:

```bash
bundlecraft --help
bundlecraft build --help
```

### Running PyTests

Run the full test suite:

```bash
pytest -v
```

Run specific tests:

```bash
pytest tests/test_builder.py -v
pytest tests/test_fetch.py::test_http_fetcher -v
```

### Code Quality Checks

Format your code with Black:

```bash
black .
```

Lint with Ruff:

```bash
ruff check .
ruff check . --fix  # Auto-fix what's possible
```

______________________________________________________________________

## 🧾 Coding Standards

Keep things simple and consistent, follow [PEP 8](https://peps.python.org/pep-0008/).

______________________________________________________________________

## 🚀 Releases

Releases are driven by tags and handled by GitHub Actions:

- Tag format for production: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`) - Tagged from `main` branch
- Tag format for pre-release: `vMAJOR.MINOR.PATCH-(alpha|beta).N` (e.g., `v1.2.3-beta.1`) - Tagged from `pre-release` branch

**Release Workflow:**

1. **Pre-releases**: Push tags to `pre-release` branch → Publishes to TestPyPI + GHCR
2. **Production**: Push tags to `main` branch → Publishes to PyPI + GHCR after approval

When you push a valid tag to GitHub, CI builds the package, publishes (after environment approval), builds/pushes the container image, and creates a GitHub Release. See `docs/CI-CD.md` for details.

### Dependency Lock File

BundleCraft uses `requirements-lock.txt` to pin exact dependency versions for production releases, ensuring deterministic and reproducible builds. This protects against supply chain attacks (see `SECURITY.md`).

**Updating the lock file (before releases):**

```bash
# Generate/update the lock file with current versions
make lock-requirements

# Or update all dependencies to their latest compatible versions
make update-lock

# Validate the lock file is current
make validate-lock
```

The lock file is automatically validated by CI. Production container builds use the lock file to ensure exact dependency versions.

**When to update:**
- Before creating a new release tag
- After modifying dependencies in `pyproject.toml`
- When applying security updates to dependencies

### Pushing a New Release / Pre-Release Git Tag

```bash
# 1. Clone the repo
git clone https://github.com/bundlecraft-io/bundlecraft.git
cd bundlecraft

# 2. Checkout the proper branch
git checkout -b pre-release     # For test/staging releases
git checkout -b main            # For official releases

# 3. Update CHANGELOG with the new upcoming version
vi CHANGELOG.md

# 4. Create a tag named after that version:
git tag v1.2.3-beta.1     # For tags in pre-release
git tag v1.2.3            # For tags in main

# 5. Push the tag to GitHub, trigger the release job
git push origin --tags
```

Once the tag has been successfully pushed to either `main` or `pre-release`, the release workflow is kicked off.

### Release Workflow

When you push a tag, the GitHub Actions release workflow (`.github/workflows/release.yaml`) automatically handles the complete release process. Here's exactly what happens:

#### 1. Branch Detection & Validation

The workflow first determines which branch the tag originated from:

- **Production releases** (`main` branch): Tags like `v1.2.3` → PyPI + GHCR
- **Pre-releases** (`pre-release` branch): Tags like `v1.2.3-beta.1` → TestPyPI + GHCR

Tag format validation ensures proper semantic versioning.

#### 2. Automated Testing & Quality Checks

Every release and pre-release runs the complete test suite:

- **Unit tests**: Full pytest suite (`pytest -v`)
- **Code quality**: Linting with ruff (`make ci-lint`)

Every **pre-release** (not main) will also run an **integration test** called [BundleCraft Fetch Test Suite](.github/workflows/test-bundlecraft-fetch.yaml) to test and validate all BundleCraft fetcher types (vault, http, s3, etc).

It runs in parallel with package building mentioned below as it meant to be *non-blocking* in case of failures. Since external dependencies can sometimes fail or experience issues during a build/release, we don't want that to block said release of the core app. We do, however, want to be clued in to any potential issues with any BundleCraft fetcher module during the pre-release testing process.

#### 3. Package Building

The workflow builds both distribution formats:

- **Wheel**: `bundlecraft-X.Y.Z-py3-none-any.whl`
- **Source distribution**: `bundlecraft-X.Y.Z.tar.gz`

#### 4. Container Image Building

For valid releases, container images are built and pushed:

- **Production**: `ghcr.io/bundlecraft-io/bundlecraft:X.Y.Z`, `ghcr.io/bundlecraft-io/bundlecraft:latest`
- **Pre-release**: `ghcr.io/bundlecraft-io/bundlecraft-test:X.Y.Z-beta.N`, `ghcr.io/bundlecraft-io/bundlecraft-test:pre-release`

#### 5. Sigstore Signing & Attestations

All BundleCraft releases are cryptographically signed using [Sigstore](https://sigstore.dev) for supply chain security:

**Container Images:**
- Signed with [cosign](https://docs.sigstore.dev/cosign/overview/) using keyless OIDC signing
- Signatures are stored in the transparency log ([Rekor](https://docs.sigstore.dev/rekor/overview/))
- Tied to GitHub's identity through OIDC tokens
- Automatically verified post-signing in the workflow

**Python Packages:**
- Signed with [Sigstore attestations](https://docs.pypi.org/attestations/) via PyPI's Trusted Publishing
- Build provenance attestations generated and stored
- Verifiable through PyPI and GitHub

**Benefits:**
- No manual GPG key management required
- Identity-based signing tied to GitHub Actions
- Transparent and auditable signing process
- Compliant with SLSA provenance standards

#### 6. Publishing Destinations

**Production Releases (main branch tags):**

- **PyPI**: [https://pypi.org/project/bundlecraft/](https://pypi.org/project/bundlecraft/)
- **GHCR**: [https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft](https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft)
- **GitHub Releases**: Full release notes with artifacts

**Pre-Releases (pre-release branch tags):**

- **TestPyPI**: [https://test.pypi.org/project/bundlecraft/](https://test.pypi.org/project/bundlecraft/)
- **GHCR**: [https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft-test](https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft-test)
- **GitHub Pre-Releases**: Marked as pre-release with installation instructions

#### 7. Post-Release Verification

After publishing, the workflow automatically verifies the release:

- Installs the package from PyPI/TestPyPI
- Runs basic smoke tests (`bundlecraft --version`, `bundlecraft --help`)
- Confirms the package is available and functional

#### 8. Release Notes Generation

GitHub releases are automatically created with:

- **Manual changelog**: Extracted from `CHANGELOG.md` if a matching version section exists
- **Commit log**: All commits since the previous release
- **Installation instructions**: Platform-specific commands for PyPI and container images
- **Artifacts**: Direct download links for wheel and source distributions

#### Available Package Locations

| Release Type | Python Package | Container Registry | GitHub Release |
|--------------|---------------|-------------------|----------------|
| **Production** | [PyPI](https://pypi.org/project/bundlecraft/) | [GHCR](https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft) | [Releases](https://github.com/bundlecraft-io/bundlecraft/releases) |
| **Pre-release** | [TestPyPI](https://test.pypi.org/project/bundlecraft/) | [GHCR-Test](https://github.com/bundlecraft-io/bundlecraft/pkgs/container/bundlecraft-test) | [Pre-releases](https://github.com/bundlecraft-io/bundlecraft/releases) |

Once the release workflow finishes successfully, your new version of BundleCraft is ready to be installed from PyPi/GCR 🎉 A GitHub release with the details of the change will also be published to this repository.

From here, see the Quickstart section in [README.md](README.md) for general instructions on using the BundleCraft package, or alternatively read on for some specific instructions in regards to using and testing with the pre-release version package.

### Testing Pre-Release Versions

#### Installing Pre-Release Packages from TestPyPI

```bash
# Install the latest pre-release version from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ bundlecraft

# Install a specific pre-release version
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ bundlecraft==1.2.3-beta.1

# Upgrade to latest pre-release (if you have an older version)
pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ bundlecraft

# Verify version
bundlecraft --version
```

> **Why TestPyPI?** Pre-releases use TestPyPI to avoid cluttering the main PyPI with beta versions, while `--extra-index-url https://pypi.org/simple/` ensures all dependencies (like `click`, `pydantic`, etc.) are still available from the main PyPI.

#### Running Pre-Release Container Images

Pre-release container images are published to GitHub Container Registry (Docker instructions used for simplicity):

```bash
# Run the latest pre-release image
docker run --rm ghcr.io/bundlecraft-io/bundlecraft:pre-release --version

# Run a specific pre-release version
docker run --rm ghcr.io/bundlecraft-io/bundlecraft:1.2.3-beta.1 --version

# Mount configs and run a build with pre-release image
docker run --rm \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/cert_sources:/app/cert_sources \
  -v $(pwd)/dist:/app/dist \
  ghcr.io/bundlecraft-io/bundlecraft:pre-release \
  build --env your-env-config --verbose

# Get shell access for debugging
docker run --rm -it \
  -v $(pwd):/workspace \
  --entrypoint /bin/bash \
  ghcr.io/bundlecraft-io/bundlecraft:pre-release
```

#### Available Pre-Release Tags

- `pre-release` - Always points to the latest pre-release version
- `1.2.3-beta.1` - Specific pre-release version tags
- `1.2.3-alpha.1` - Alpha versions for early testing

#### When to Use Pre-Release Versions

**Use pre-releases for:**

- Testing new features before production
- Verifying bug fixes work in your environment
- Contributing feedback on upcoming changes
- CI/CD pipeline testing with latest features

**Don't use pre-releases for:**

- Production environments
- Critical infrastructure
- When stability is more important than features

> **Note:** Pre-release versions are only published when tags are pushed to the `pre-release` branch. They become available on TestPyPI and GHCR within a few minutes of the tag push.

### Verifying Sigstore Signatures

All BundleCraft releases are cryptographically signed with Sigstore for supply chain security. You can verify the authenticity and provenance of any release.

#### Verifying Container Image Signatures

Install [cosign](https://docs.sigstore.dev/cosign/installation/) and verify container images:

```bash
# Install cosign (if not already installed)
# macOS
brew install cosign

# Linux
curl -LO https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
sudo install cosign-linux-amd64 /usr/local/bin/cosign

# Verify a production image
cosign verify ghcr.io/bundlecraft-io/bundlecraft:1.2.3 \
  --certificate-identity-regexp="https://github.com/bundlecraft-io/bundlecraft" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com

# Verify a pre-release image
cosign verify ghcr.io/bundlecraft-io/bundlecraft-test:1.2.3-beta.1 \
  --certificate-identity-regexp="https://github.com/bundlecraft-io/bundlecraft" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com

# Verify using digest (most secure)
cosign verify ghcr.io/bundlecraft-io/bundlecraft@sha256:... \
  --certificate-identity-regexp="https://github.com/bundlecraft-io/bundlecraft" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com
```

**What this verifies:**
- The image was built and signed by GitHub Actions in the bundlecraft-io/bundlecraft repository
- The signature is stored in the public transparency log (Rekor)
- The build identity is cryptographically tied to the GitHub OIDC token

#### Verifying Python Package Attestations

PyPI packages include Sigstore attestations that can be verified:

```bash
# Verify during installation (pip >= 24.2 required)
pip install --require-attestations bundlecraft

# Or verify an upgrade
pip install --upgrade --require-attestations bundlecraft

# View attestations on PyPI
# Attestations are available at: https://pypi.org/project/bundlecraft/#files
# Each distribution file (.whl, .tar.gz) has an associated .attestation file
```

**What this verifies:**
- The package was built in GitHub Actions with Trusted Publishing
- Build provenance links the package to specific source code and workflow
- Attestations include SLSA build provenance information

#### Understanding Keyless Signing

BundleCraft uses **keyless signing** via Sigstore, which means:

- **No long-term keys to manage**: Signatures use short-lived certificates tied to GitHub's OIDC identity
- **Transparency log**: All signatures are recorded in [Rekor](https://docs.sigstore.dev/rekor/overview/) for public audit
- **Identity-based**: Signatures prove the release came from GitHub Actions in this repository
- **Automated**: Signing happens automatically in CI/CD with no manual intervention

This provides the same security guarantees as traditional GPG signing without the operational overhead of key management.

______________________________________________________________________

## 🌐 Notes on the Fetch Layer

- Fetch is staging-only: do not introduce persistent caches; use `cert_sources/staged/<source_name>/` which is cleaned per run.
- Security controls to uphold:
  - HTTPS only for remote endpoints (URLs/APIs)
  - Optional custom CA (`verify.ca_file`), optional TLS leaf fingerprint pin (`verify.tls_fingerprint_sha256`)
  - Optional content hash pinning (`verify.sha256`) for static/public sources
- Secrets should be referenced via environment variables (e.g., `KEYFACTOR_TOKEN`, `VAULT_TOKEN`), never committed.
- Provider integrations should live under `bundlecraft/fetchers/` and optional dependencies declared in `pyproject.toml` extras.
- Update `docs/adr-0002-fetch.md` and `docs/troubleshooting.md` when behavior changes.

______________________________________________________________________

## ✅ Quick Command Reference

Handy commands for common tasks:

| Action | Command |
| -------------------- | ------------------------------------------------------------- |
| Install for dev | `pip install -e ".[dev]"` |
| Install pre-release | `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ bundlecraft` |
| Test pre-release container | `docker run --rm ghcr.io/bundlecraft-io/bundlecraft:pre-release --version` |
| Format code | `black .` |
| Lint code | `ruff check . --fix` |
| Run tests | `pytest -v` |
| Build bundle | `bundlecraft build --env test-example-envconfig --bundle internal` |
| Verify bundle | `bundlecraft verify --target dist/.test-inline --verify-all` |
| Fetch remote sources | `bundlecraft fetch --source-config-file config/cert_sources/*.yaml` |
| Generate lock file | `make lock-requirements` |
| Validate lock file | `make validate-lock` |
| Update lock file | `make update-lock` |
| Build Python package | `python -m build` |
| Validate package | `twine check dist/*` |

______________________________________________________________________

## 🤝 Pull Request Guidelines

It's a small project, so it's all quite simple:

1. **Fork or branch** from `pre-release` (always has the latest, somewhat stable changes)
1. **Test your changes** – Run `pytest`, `black`, and `ruff` locally
1. **Update docs** – If behavior changes, update relevant docs, especially [CHANGELOG.md](CHANGELOG.md)

______________________________________________________________________

> **Thank you for helping make BundleCraft better. 🎉**
