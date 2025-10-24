# 🧩 Contributing to BundleCraft

Thanks for your interest in BundleCraft! This guide walks you through the entire contribution process: from cloning the repo to getting your changes merged.

**Quick Navigation:**

- [Quick Start](#-quick-start-your-first-contribution) - Get up and running in 5 minutes
- [Understanding the Codebase](#-understanding-the-codebase) - Architecture and structure
- [Testing Your Changes](#-testing-your-changes) - How to test locally
- [Release Process](#-release-process) - Building and releasing to PyPI
  - [Testing Releases Locally](#testing-releases-locally) - Local testing before release
  - [Release Security](#release-security) - Security setup and best practices
- [Pull Request Guidelines](#-pull-request-guidelines) - How to submit PRs

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

# 5. Test the package locally (recommended)
make test-install
# Creates isolated venv, installs, tests, cleans up automatically

# 6. Optional: Test on Test PyPI (for major releases)
# See "Testing Releases Locally" section below for setup
make release-test          # Upload to Test PyPI
make release-test-install  # Install and test

# 7. Push tag to trigger automated release (recommended)
git tag v0.2.0
git push origin v0.2.0
# GitHub Actions will build, wait for approval, then publish

# 8. Manual PyPI release (only if GitHub Actions unavailable)
make release
# ⚠️  This bypasses environment approvals!
```

#### Automated Release via GitHub Actions (Recommended)

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

### Testing Releases Locally

Since the automated release workflow requires environment approval (human review), you need to test package builds locally before pushing a release tag.

#### Quick Test (Recommended for All Releases)

```bash
# Test that package builds and installs correctly
make test-install

# What it does:
# ✅ Builds wheel and sdist
# ✅ Creates temporary isolated venv
# ✅ Installs from built wheel
# ✅ Runs version check
# ✅ Auto-cleans up
```

#### Interactive Testing (For Manual Exploration)

```bash
# Create persistent test environment
make test-install-interactive

# Use it
source /tmp/test-bundlecraft/bin/activate
bundlecraft --version
bundlecraft build --help
# ... test whatever you need ...
deactivate

# Clean up when done
rm -rf /tmp/test-bundlecraft
```

#### Test PyPI Testing (For Major Releases)

Test the complete upload/download cycle without affecting production:

**One-time setup:**

1. Create account at <https://test.pypi.org/account/register/>
2. Generate API token at <https://test.pypi.org/manage/account/token/>
3. Configure credentials:

```bash
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TOKEN-HERE
EOF

chmod 600 ~/.pypirc
```

**Upload and test:**

```bash
# Upload to Test PyPI
make release-test

# Install from Test PyPI
make release-test-install

# Or manually
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            bundlecraft

# Verify it works
bundlecraft --version
```

**Note:** `--extra-index-url` is needed because dependencies (click, cryptography, etc.) aren't on Test PyPI.

#### Docker Testing (For Cross-Version Compatibility)

```bash
# Build first
make build

# Test on Python 3.9 (minimum supported)
docker run --rm -v $(pwd)/dist:/dist python:3.9-slim bash -c \
  "pip install /dist/bundlecraft-*.whl && bundlecraft --version"

# Test on Python 3.11
docker run --rm -v $(pwd)/dist:/dist python:3.11-slim bash -c \
  "pip install /dist/bundlecraft-*.whl && bundlecraft --version"

# Test on Python 3.12
docker run --rm -v $(pwd)/dist:/dist python:3.12-slim bash -c \
  "pip install /dist/bundlecraft-*.whl && bundlecraft --version"
```

#### Testing Strategy by Release Type

**Patch Releases (v0.1.1 → v0.1.2):**

```bash
make test-install  # Quick smoke test sufficient
```

**Minor Releases (v0.1.0 → v0.2.0):**

```bash
make test-install          # Smoke test
make release-test          # Test PyPI
make release-test-install  # Verify install
```

**Major Releases (v0.x.x → v1.0.0):**

```bash
make test-install                  # Smoke test
make release-test                  # Test PyPI
make release-test-install          # Verify install
# Docker tests across Python versions
# Extensive manual testing
```

#### Common Testing Issues

**Problem:** "make test-install" fails with "Could not find version"

```bash
# Solution: Ensure package is built
make build
ls -lh dist/  # Should see .whl and .tar.gz
```

**Problem:** Test PyPI upload fails with 403 Forbidden

```bash
# Solution: Check token in ~/.pypirc or regenerate token
# Visit: https://test.pypi.org/manage/account/token/
```

**Problem:** Can't find package on Test PyPI after upload

```bash
# Solution: Wait 2-3 minutes for indexing, then try again
```

**Problem:** Version already exists on Test PyPI

```bash
# Solution: Test PyPI doesn't allow re-uploads
# Either: commit a change to bump dev version
# Or: Use a test suffix in pyproject.toml temporarily
```

### Release Security

BundleCraft uses a **four-layer security model** for PyPI releases:

```text
Developer → Tag Push → Branch Protection → Environment Approval → Trusted Publishing → PyPI
             (v0.2.0)   (Tests must pass)  (Human review)        (OIDC signature)    (Live)
```

#### Security Layers Explained

##### Layer 1: Branch Protection

- Prevents direct commits to `main`
- Requires PR approval before merge
- Requires tests to pass before merge
- Ensures code review happens

##### Layer 2: Tag Protection

- Only maintainers can create `v*` tags
- Prevents unauthorized releases
- Tags trigger the release workflow

##### Layer 3: Environment Approval

- Human review required before PyPI publish
- Reviewer checks version, tests, artifacts
- Can cancel during review
- 5-minute wait timer (optional grace period)

##### Layer 4: Trusted Publishing (OIDC)

- No API tokens needed
- GitHub signs workflow identity
- PyPI verifies signature
- Can't be used outside specific workflow
- Can't be stolen or leaked

#### Initial Security Setup

##### 1. Branch Protection (Settings → Branches → Add rule for `main`)

```yaml
✅ Require pull request before merging
   └─ Require approvals: 1
   └─ Dismiss stale approvals when new commits pushed

✅ Require status checks to pass before merging
   └─ Require branches to be up to date
   Required checks:
      - test / Run Tests
      - test / Run linting

✅ Require conversation resolution before merging

✅ Do not allow bypassing the above settings

✅ Restrict who can push to matching branches
   └─ Only: Administrators, Maintainers
```

##### 2. Tag Protection (Settings → Tags → Add rule)

```yaml
Pattern: v*
Who can create: Maintainers only
```

##### 3. Environment Protection (Settings → Environments → Create `release`)

```yaml
Environment name: release

Protection rules:
✅ Required reviewers: 1-2 trusted maintainers
   Example: @maintainer1, @maintainer2

✅ Wait timer: 5 minutes (optional - gives grace period to cancel)

✅ Deployment branches and tags
   Pattern: refs/tags/v*
   (Only version tags can deploy)
```

##### 4. PyPI Trusted Publishing (<https://pypi.org/manage/account/publishing/>)

```yaml
Add a new publisher:
  PyPI Project Name: bundlecraft
  Owner: bundlecraft-io
  Repository: bundlecraft
  Workflow: release.yaml
  Environment: release
```

After first release, the "pending" publisher becomes active.

#### How Environment Approval Works

```bash
# 1. You push a tag
git tag v0.2.0
git push origin v0.2.0

# 2. GitHub Actions starts:
#    ✅ Runs tests
#    ✅ Builds wheel and sdist
#    ✅ Pauses at publish-pypi job

# 3. GitHub notifies required reviewers

# 4. Reviewer checks:
#    - Version number correct? (v0.2.0)
#    - Tests passed?
#    - Build artifacts look good?
#    - Changelog updated?
#    - Ready for users?

# 5. Reviewer clicks "Approve and deploy" in GitHub UI

# 6. Publish proceeds to PyPI

# 7. Verify on PyPI:
#    https://pypi.org/project/bundlecraft/
```

#### How Trusted Publishing Works

```text
GitHub Actions Workflow
         ↓
Request OIDC token from GitHub
         ↓
GitHub signs token with identity:
  - Repository: bundlecraft-io/bundlecraft
  - Workflow: release.yaml
  - Environment: release
  - Tag: refs/tags/v0.2.0
         ↓
Send package + OIDC token to PyPI
         ↓
PyPI verifies signature matches trusted publisher
         ↓
✅ Publish succeeds (valid signature)
❌ Publish fails (invalid/unauthorized)
```

**Security benefits:**

- No API tokens to leak
- No token rotation needed
- Only works from specific workflow
- Only works from specific repository
- Only works from environment-protected jobs

#### Workflow Security Features

The `.github/workflows/release.yaml` includes:

**Minimal Permissions:**

```yaml
permissions:
  contents: write  # Only for GitHub releases
  id-token: write  # Only for PyPI OIDC
```

**Tag Validation:**

```yaml
# Ensures only semantic versions are released
if [[ ! "$GITHUB_REF" =~ ^refs/tags/v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
  exit 1
fi
```

**Test Requirements:**

```yaml
publish-pypi:
  needs: [test, build]  # Can't publish without passing tests
```

**Artifact Verification:**

```yaml
- name: Verify package
  run: twine check dist/*
```

#### Emergency Procedures

**To cancel a release:**

1. **Before approval:** Don't approve the deployment (it will timeout)
2. **During wait timer:** Click "Cancel deployment" in Actions UI
3. **After PyPI publish:** ⚠️ Can't unpublish! Release patch version with fix

**If malicious tag is pushed:**

```bash
# 1. Delete the tag immediately
git tag -d v0.2.0              # Local
git push origin :refs/tags/v0.2.0  # Remote

# 2. Workflow will fail (no approval)

# 3. Check audit logs
# Settings → Security → Audit log
# Filter: action:tag.create

# 4. Review tag protection settings
# Ensure only maintainers can create v* tags
```

#### Security Checklist

**Before first release:**

- [ ] Branch protection enabled on `main`
- [ ] Tag protection enabled for `v*`
- [ ] Environment `release` created
- [ ] Required reviewers configured (1-2 maintainers)
- [ ] Deployment branches set to `refs/tags/v*`
- [ ] PyPI Trusted Publisher configured
- [ ] Workflow references `environment: release`
- [ ] Test with a test tag to verify setup

**After each release:**

- [ ] Package appears on PyPI
- [ ] Installation works: `pip install bundlecraft==X.Y.Z`
- [ ] GitHub Release created
- [ ] Audit logs show no unexpected activity

#### Security Best Practices

**DO:**

- ✅ Always release from `main` branch
- ✅ Use semantic versioning (v1.0.0, v1.2.3)
- ✅ Review diff before approving deployment
- ✅ Test on Test PyPI for major releases
- ✅ Document breaking changes
- ✅ Keep reviewer list current

**DON'T:**

- ❌ Share API tokens (not needed!)
- ❌ Bypass branch protection
- ❌ Create release tags from feature branches
- ❌ Approve without reviewing
- ❌ Use non-semantic versions

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
