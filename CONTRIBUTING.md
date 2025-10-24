# 🧩 Contributing to BundleCraft

Thanks for your interest in BundleCraft! This guide walks you through the entire contribution process: from cloning the repo to getting your changes merged.

______________________________________________________________________

## 🚀 Quick Start: Your First Contribution

### Step 1: Get the code

Fork the repo on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/bundlecraft.git
cd bundlecraft
```

Or if you have write access, clone directly:

```bash
git clone https://github.com/bundlecaft-io/bundlecraft.git
cd bundlecraft
```

### Step 2: Set up your environment

Ensure some useful system dependencies:

```bash
# Required for conversions and verification
sudo apt-get install openssl openjdk-17-jre-headless  # (for keytool)

# Optional: jq (required for scripts/json-output-examples.sh)
sudo apt-get install jq
```

Create a virtual environment and install everything you need:

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

# Install with runtime dependencies
pip install -e .

# If needed, install with remote fetch dependencies
pip install -e ".[fetchers]"

# Or install with dev/test tools
pip install -e ".[dev]"
```

This installs:

- The `bundlecraft` CLI in editable mode (your code changes take effect immediately)
- Optional fetcher dependencies (i.e. hvac for HashiCorp Vault)
- Optional development tools (black, ruff, pytest)

> **Tip:** Keep your output directory named `dist/` (not `build/`) to avoid conflicts with Python's build tool.

### Step 3: Configure Repository

#### Prepare Certificate Source Configurations

- Bring your own certs, or use `scripts/generate_test_cas.py` to generate some **TEST** CA certificates.
- Place PEM files in appropriate folders under `cert_cert_sources/`
- Update `config/sources/` YAMLs to specify what certificates each source will be comprised of
- Optionally add a `fetch:` section to stage certificates from trusted remote origins (HTTPS/API/Vault, etc..)

#### Prepare Certificate Environment Configurations

- Update `config/envs/` YAMLs to specify which sources to include into which bundles
- Define where each environment/bundle is meant be bundle
- Optionally add various filters and parameters to the final output of the trust store build.

### Step 4: Make your changes

Create a branch for your work:

```bash
git checkout -b fix-something-cool
```

Now you can:

- Edit code in `bundlecraft/`
- Update docs in `docs/` or the README
- Add tests in `tests/`

### Step 5: Test your changes

Run the CLI to see your changes in action:

```bash
bundlecraft build --env dev --verbose
```

Run the test suite:

```bash
pytest -v
```

Format and lint your code:

```bash
black .
ruff check . --fix
```

### Step 6: Commit and push

```bash
git add .
git commit -m "fix: describe what you fixed"
git push origin fix-something-awesome
```

### Step 7: Open a Pull Request

Go to GitHub and open a PR from your branch to `main`. In your PR description:

- Explain what changed and why
- Link any related issues
- Note how to test/verify the change

Maintainers will review, provide feedback, and merge when ready. PRs are squash-merged to keep history clean.

______________________________________________________________________

## 📚 Understanding the Codebase

Before diving into specific changes, here's what you need to know about how BundleCraft is organized.

### Repository Structure

```shell
bundlecraft/
├── bundlecraft/           # Main Python package
│   ├── cli.py             # CLI entrypoint
│   ├── builder.py         # Build orchestration
│   ├── fetch.py           # Fetch/staging layer
│   ├── verifier.py        # Verification logic
│   ├── converter.py       # Format conversion
│   ├── differ.py          # Bundle comparison
│   ├── fetchers/          # Remote source fetchers
│   └── helpers/           # Internal utilities
├── config/                # Configuration files
│   ├── defaults.yaml      # Global defaults
│   ├── envs/              # Environment definitions
│   └── sources/           # Cert sources definitions
├── cert_sources/          # Certificate sources
│   ├── internal/          # Committed certificates
│   └── staged/            # Fetched certificates (ephemeral)
├── dist/                  # Build outputs (gitignored)
├── tests/                 # Test suite
├── docs/                  # Documentation and ADRs
├── scripts/               # Helper scripts
├── .github/               # CI workflows and issue templates
├── pyproject.toml         # Project metadata
├── CODE_OF_CONDUCT.md     # Community guidelines
├── CONTRIBUTING.md        # This file
├── SECURITY.md            # Security policy
└── README.md              # Main documentation
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
- `convert_utils.py` – Format conversion helpers (OpenSSL, keytool wrappers)
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

## 🧪 Testing Your Changes

### Running the CLI

Once you have bundle and environment configs, test the CLI directly:

```bash
# Full build pipeline
bundlecraft build --env dev

# Individual stages
bundlecraft fetch --source-config-file config/sources/internal.yaml
bundlecraft convert --input dist/dev/internal/bundlecraft-ca-trust.pem --output-dir dist/dev/internal
bundlecraft verify --target dist/dev/internal --verify-all
bundlecraft diff --from sources/staged/internal/rootCA.pem --to dist/dev/internal/bundlecraft-ca-trust.pem
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

We keep things simple and consistent:

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use **Black** for formatting (88-char line length)
- Use **Ruff** for linting
- Write clear Click commands with consistent option names
- Keep logging human-readable; support `--json` for machine parsing
- Add tests for new features
- Update docs when behavior changes

### Adding Tests

- Place tests in `tests/`
- Use `click.testing.CliRunner` for CLI tests
- Include small, non-sensitive PEM fixtures for functional tests
- Test happy paths and error cases

______________________________________________________________________

## 🔐 Security Guidelines

**Never commit:**

- Private keys
- Internal CA certificates (unless they're test fixtures)
- Secrets, tokens, or credentials

**Always:**

- Use environment variables for secrets (`VAULT_TOKEN`, `KEYFACTOR_TOKEN`)
- Reference secrets by name in configs, never inline them
- Mark test fixtures clearly in comments

**When working on fetch:**

- Enforce HTTPS for remote endpoints (URLs/APIs)
- Support optional CA pinning (`verify.ca_file`)
- Support optional TLS fingerprint pinning (`verify.tls_fingerprint_sha256`)
- Support optional content hash pinning (`verify.sha256`)
- No persistent caches; staging is cleaned per run (`cert_sources/staged/<source_name>/`)
- Update `docs/adr-0002-fetch.md` and `docs/troubleshooting.md` for behavior changes

______________________________________________________________________

## 🚀 Release Process

This section covers the complete release process for BundleCraft, from development to PyPI publication.

### Development Workflow

#### 1. Clone and Setup (First Time)

```bash
# Clone the repository
git clone https://github.com/bundlecraft-io/bundlecraft.git
cd bundlecraft

# Install with all dependencies
make install-all
# OR manually: pip install -e ".[dev,fetchers]"

# Verify installation
bundlecraft --version
make test
```

#### 2. Daily Development

```bash
# Create a feature branch
git checkout -b feature/my-awesome-feature

# Make your changes to code in bundlecraft/
vim bundlecraft/builder.py

# Changes are immediately active (editable install)
bundlecraft build --env dev

# Run tests
make test

# Format and lint
make format
make lint-fix

# Run full QA pipeline
make qa

# Commit your changes
git add .
git commit -m "feat: add awesome feature"
git push origin feature/my-awesome-feature
```

#### 3. Testing Changes

**Using `pip install -e .` (Editable Mode) - For Development:**

- Use this 99% of the time during development
- Code changes are immediately reflected
- No reinstall needed
- Fast iteration

```bash
# Install once
make install-dev

# Edit, test, repeat - no reinstall needed!
vim bundlecraft/cli.py
bundlecraft --help  # Sees your changes immediately
```

**Using `python -m build` (Package Build) - For Release Testing:**

- Use before creating releases
- Tests what end users will actually get
- Verifies packaging is correct

```bash
# Build the package
make build

# Verify it's correct
make verify-package

# Test installation in isolated environment
python -m venv /tmp/test-env
/tmp/test-env/bin/pip install dist/*.whl
/tmp/test-env/bin/bundlecraft --version
```

### Package Building and Distribution

#### Understanding the Build Artifacts

When you run `make build`, you create two types of distributions:

- **Wheel (`.whl`)** - Binary distribution

  - Fast to install
  - Platform-independent (pure Python)
  - What most users install via `pip install bundlecraft`

- **Source Distribution (`.tar.gz`)** - Source code

  - Contains complete source code
  - Users can inspect/audit the code
  - Can rebuild on any platform
  - Required for PyPI best practices
  - Allows custom builds with specific Python versions

#### Versioning with Git Tags

BundleCraft uses **automatic versioning** from git tags via `hatch-vcs`:

```bash
# Check current version (from last tag + commits)
make version
# Output: Version: 0.1.2.dev1+g6efd343a2.d20251024

# When you're ready to release:
git tag v0.2.0

# Now version becomes: 0.2.0 (clean release)
make build
```

**Version Format Explained:**

- On a tag: `0.2.0` (clean release version)
- After a tag: `0.2.0.dev1+g<hash>.d<date>` (development version)
- No tags: `0.0.0.dev0+g<hash>` (initial development)

**Semantic Versioning:**

- `v0.1.0` → `v0.1.1` - Patch (bug fixes)
- `v0.1.0` → `v0.2.0` - Minor (new features, backward compatible)
- `v0.1.0` → `v1.0.0` - Major (breaking changes)

### Creating a Release

#### Manual Release Process

```bash
# 1. Ensure main branch is clean and tests pass
git checkout main
git pull origin main
make qa  # Run format, lint, test

# 2. Create and push the version tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
git push origin main

# 3. Build distributions
make build

# 4. Verify package quality
make verify-package
# Should show: "PASSED" for both .whl and .tar.gz

# 5. Test on Test PyPI (recommended first time)
make release-test
# Test install: pip install -i https://test.pypi.org/simple/ bundlecraft

# 6. Release to production PyPI
make release
# WARNING: This is irreversible! Can't delete/re-upload same version.
```

#### Automated Release via GitHub Actions

**Trigger:** Pushing a version tag (`v*`) to GitHub automatically:

1. Runs the full test suite
2. Builds wheel and source distributions
3. Publishes to PyPI (via Trusted Publishing)
4. Builds and pushes Docker image to GHCR
5. Creates GitHub Release with artifacts

**Setup Requirements:**

```bash
# Push a version tag to trigger release
git tag v0.2.0
git push origin v0.2.0

# GitHub Actions will:
# ✅ Run tests
# ✅ Build package
# ✅ Publish to PyPI
# ✅ Create GitHub Release
```

**To enable automated PyPI publishing:**

- Go to [PyPI Trusted Publishers](https://pypi.org/manage/account/publishing/)
- Add GitHub as trusted publisher:

  - Repository: `bundlecraft-io/bundlecraft`
  - Workflow: `release.yml`
  - Environment: `release` (optional but recommended)

### Pre-Release Checklist

Before creating a release, ensure:

```bash
# ✅ All tests pass
make test

# ✅ Code is formatted and linted
make format
make lint

# ✅ Version bumped appropriately
# Decide: patch (0.1.1), minor (0.2.0), or major (1.0.0)

# ✅ CHANGELOG/docs updated (if applicable)

# ✅ No uncommitted changes
git status

# ✅ On main branch
git checkout main
git pull

# ✅ Package builds successfully
make build

# ✅ Package passes validation
make verify-package
```

### Post-Release Verification

```bash
# Wait 2-5 minutes for PyPI to process

# Test installation in clean environment
python -m venv /tmp/verify-release
source /tmp/verify-release/bin/activate
pip install bundlecraft
bundlecraft --version  # Should show your new version
deactivate

# Verify on PyPI
# Visit: https://pypi.org/project/bundlecraft/
```

### Using the Makefile

The included `Makefile` provides convenient shortcuts:

```bash
# Show all available commands
make help

# Development
make install-dev        # Install for development
make format             # Format code with black
make lint               # Lint with ruff
make test               # Run tests
make qa                 # Format, lint, and test

# Building
make build              # Build wheel + sdist
make verify-package     # Verify with twine

# Releasing
make release-test       # Upload to Test PyPI
make release            # Upload to PyPI (production!)

# Versioning
make version            # Show current version
make tag-version VERSION=0.2.0  # Create version tag

# Cleaning
make clean              # Remove build artifacts
```

See `docs/adr-0006-corerelease.md` for the full distribution strategy.

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
| Format code | `black .` |
| Lint code | `ruff check . --fix` |
| Run tests | `pytest -v` |
| Build bundle | `bundlecraft build --env dev --bundle internal` |
| Verify bundle | `bundlecraft verify --target dist/dev/internal --verify-all` |
| Fetch remote sources | `bundlecraft fetch --source-config-file config/cert_sources/*.yaml` |
| Build Python package | `python -m build` |
| Validate package | `twine check dist/*` |

______________________________________________________________________

## 🤝 Pull Request Guidelines

We keep it simple for small projects:

1. **Fork or branch** from `main`
1. **Test your changes** – Run `pytest`, `black`, and `ruff` locally
1. **Update docs** – If behavior changes, update relevant docs
1. **Write a clear description**:
   - What changed and why
   - How to test/verify
   - Link related issues or ADRs
1. **Expect feedback** – Reviews happen quickly; we're here to help
1. **Squash-merge** – Maintainers will squash commits to keep history clean

**Commit signing is encouraged but not required.**

______________________________________________________________________

> **Thank you for helping make BundleCraft better. 🎉**
