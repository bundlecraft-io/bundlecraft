# 🧩 Contributing to BundleCraft

A concise guide to contributing changes to BundleCraft and releasing new package versions.

**Quick Navigation:**

- ⚡ Quickstart — Get started in 60 seconds
- Part 1: Contributing Code Changes — Merge features/fixes into pre-release
- Releases — Tag-driven release overview
- Understanding the Codebase — Architecture and structure
- Testing Your Changes — How to test locally
- Release Security — Four-layer release security

______________________________________________________________________


## ⚡ Quickstart

**Contributing code? Get started in 60 seconds:**

```bash
# 1. Clone the repo
git clone https://github.com/bundlecraft-io/bundlecraft.git
cd bundlecraft

# 2. Enable git hooks (prevents pushing tags without changelog entries)
git config core.hooksPath .githooks

# 3. Set up your environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -e ".[dev]"

# 4. Create a feature branch
git checkout -b feature/my-awesome-feature

# 5. Make changes, test locally
bundlecraft build --env test-example-envconfig --verbose
pytest -v
black . && ruff check . --fix

# 6. Commit and open PR to pre-release
git add .
git commit -m "feat: describe your feature"
git push origin feature/my-awesome-feature
# Open PR on GitHub targeting pre-release branch
```

Optional: prepare example testing configs and certs (no setup needed):

```bash
# Generate minimal example configs (inline test certs)
scripts/prepare_test_configs.sh

# Then run a quick build using the generated env name
bundlecraft build --env test-example-envconfig --verbose

# Clean up generated configs and artifacts when done
scripts/prepare_test_configs.sh --cleanup
```

Note: The script writes files to `config/sources/.test-example-sourcecfg.yaml` and
`config/envs/.test-example-envconfig.yaml`. It uses inline test certificates and is for
local testing only. Set `BUNDLECRAFT_WORKSPACE=/path/to/repo` to override the target workspace.

**Releasing a version? See the Releases section below for the full process.**

______________________________________________________________________

## Part 1: Contributing Code Changes

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
# Required for conversions and verification
sudo apt-get install openssl

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

### Step 5: Test core changes (non release branches)

Run the CLI to see your changes in action:

```bash
bundlecraft build --env test-example-envconfig --verbose
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

### Step 6: Local build/test shortcuts (optional)

For a quick end-to-end smoke test of the built wheel and container, the Makefile provides a few simple helpers:

```bash
# Build a local container image and smoke-test it
make build-test-image
make test-image-version     # runs 'bundlecraft --version' in the container
make test-image-build       # builds + verifies using inline test configs

# Build a local wheel/sdist and smoke-test it in a temp venv
make build-test-pypi
make test-pypi-version      # prints installed version from the wheel
make test-pypi-build        # builds + verifies using inline test configs
```

Notes:

- These targets do not publish anything; they're strictly local tests.
- The inline configs are created/cleaned by `scripts/prepare_test_configs.sh`.


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
- `convert_utils.py` – Format conversion helpers (OpenSSL and pyjks for JKS)
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

We keep things simple and consistent:

- Follow [PEP 8](https://peps.python.org/pep-0008/)

## 🚀 Releases (short and sweet)

Releases are driven by tags and handled by GitHub Actions:

- Tag format for production: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`)
- Tag format for pre-release: `vMAJOR.MINOR.PATCH-(alpha|beta).N` (e.g., `v1.2.3-beta.1`)

When you push a valid tag to GitHub, CI builds the package, publishes (after environment approval), builds/pushes the container image, and creates a GitHub Release. See `docs/CI-CD.md` for details.


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
| Build bundle | `bundlecraft build --env test-example-envconfig --bundle internal` |
| Verify bundle | `bundlecraft verify --target dist/.test-inline --verify-all` |
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
