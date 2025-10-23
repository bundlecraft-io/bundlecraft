# ADR-0006: Core Release & Distribution Strategy (MVP)

**Status:** Proposed - **Supersedes ADR-0001 and ADR-0003**
**Date:** October 23, 2025
**Owner:** Chris J. Pich
**Related:** SECURITY.md, README, CI/CD workflows, ADR-0007 (future enhancements)

______________________________________________________________________

## 1) Context

ADR-0001 established an OCI-only distribution model for BundleCraft, while ADR-0003 later evolved this into a multi-channel approach. This ADR consolidates both into a **pragmatic, maintainable MVP** suitable for a solo developer's first project, with advanced features deferred to ADR-0007.

As a security-focused PKI tool, we need trustworthy distribution without over-engineering or creating maintenance burden. This requires **separating the core engine from user-facing configurations** through a multi-repository architecture.

______________________________________________________________________

## 2) Problem Statement

We need a **simple, secure release strategy** that:

- Provides **OCI container** for CI/CD workflows (primary use case)
- Offers **PyPI package** for local development and testing
- Includes **starter template** for user onboarding
- Provides **example repository** for learning and reference
- Keeps trust materials **separate** from distributed artifacts
- Maintains clear boundaries between engine and user configurations
- Is **maintainable by one person** without complex tooling

______________________________________________________________________

## 3) Goals & Non-Goals

### Goals (MVP)

- Publish a **signed OCI image** to GHCR with basic provenance
- Publish an **engine-only PyPI package** for pipx/pip installation
- Provide a **starter template repository** (bundlecraft-starter) for immediate use
- Provide an **example repository** (bundlecraft-example) for learning and reference
- Exclude trust data from all distributed artifacts
- Use GitHub's native signing capabilities (Sigstore integration)
- Single-source versioning from git tags
- Maintain clear separation: engine (bundlecraft) vs. user configs (starter/example)

### Non-Goals (Deferred to ADR-0007)

- PEX/zipapp artifacts (niche use case, adds complexity)
- Custom GitHub Action wrapper (users can call OCI directly)
- Advanced SLSA provenance levels
- Weekly CVE scanning automation
- Multi-architecture builds (start with amd64, add arm64 later if needed)
- Hash-locked dependency files (use standard pyproject.toml constraints)

______________________________________________________________________

## 4) Repository Architecture

BundleCraft is distributed as **three separate repositories** with distinct purposes:

| Repository | Purpose | Contents | Update Frequency |
| ------------------------- | --------------------------------------------------- | ---------------------------------- | -------------------------------- |
| **bundlecraft** | Core engine, library, CLI | Python package, OCI image | Versioned releases (semver) |
| **bundlecraft-starter** | Minimal starter template (GitHub Template) | Configs, directory structure | Updated with core releases |
| **bundlecraft-example** | Full reference implementation with dummy data | Complete working example | Always based on latest starter |

### Design Principles

- **Trust separation:** Certificates/configs never bundled in engine artifacts
- **Clear boundaries:** Engine handles logic; starter/example provide structure
- **Progressive disclosure:** Starter is minimal; example shows all features
- **Starter as foundation:** Example always builds upon latest starter template

______________________________________________________________________

## 5) Distribution Channels

| Channel | Description | Use Case | Security | Status |
| -------------------- | ------------------------------------------------------ | ------------------------------- | ----------------------------- | ------ |
| **OCI image (GHCR)** | Signed container image with attestation | CI/CD pipelines, automation | GitHub-native Sigstore/cosign | MVP |
| **PyPI package** | Engine-only Python package for pipx/pip installation | Local dev, testing, exploration | PyPI Trusted Publishing | MVP |
| **Starter Template** | GitHub template repo with minimal config structure | User onboarding, quick start | Documentation only | MVP |
| **Example Repo** | Full reference implementation with dummy certs | Learning, reference, playground | Documentation only | MVP |

**Deferred to ADR-0007 (Future):** PEX/zipapp artifacts, GitHub Action wrapper, advanced SBOM/SLSA levels, multi-arch builds, weekly CVE automation.

______________________________________________________________________

## 6) Security Principles

- **Trust separation:** certs/configs are always mounted or fetched, never bundled in artifacts
- **Native signing:** leverage GitHub's built-in Sigstore integration for both OCI and PyPI
- **Version from tags:** single source of truth using git tags
- **No secrets in CI:** use OIDC for PyPI Trusted Publishing and GHCR
- **Clear documentation:** explain security model and verification steps
- **Engine isolation:** core package contains zero user data or configuration examples

______________________________________________________________________

## 7) Repository Details

### 7.1 bundlecraft (Core Engine)

**Purpose:** The engine/library/CLI that builds, verifies, and converts trust bundles. Distributed via OCI and PyPI.

**Repository Structure:**

```text
bundlecraft/
├── bundlecraft/           # Core Python package
│   ├── __init__.py
│   ├── builder.py
│   ├── cli.py
│   ├── converter.py
│   ├── differ.py
│   ├── fetch.py
│   ├── verifier.py
│   ├── fetchers/
│   └── helpers/
├── tests/                 # Comprehensive test suite
├── docs/                  # ADRs, API docs, architecture
├── scripts/               # Dev tools (not distributed)
├── .github/workflows/
│   ├── test.yaml         # Run pytest on PRs
│   ├── release-oci.yaml  # Build & push Docker image on tags
│   └── release-pypi.yaml # Build & publish to PyPI on tags
├── Dockerfile            # Multi-stage OCI build
├── pyproject.toml        # Package metadata, dependencies
├── MANIFEST.in           # Exclude user configs from PyPI package
├── pytest.ini
├── README.md             # Installation, usage, links to starter/example
├── LICENSE
├── SECURITY.md
├── CODE_OF_CONDUCT.md
└── CONTRIBUTING.md
```

**Key Exclusions (from distributed artifacts):**

- `config/` - User configurations (moved to starter/example)
- `cert_sources/` - Certificate files (moved to starter/example)
- `build_cache/` - Build outputs (example-specific)
- `tests/` - Not included in PyPI package
- `*.jks`, `*.p12`, `*.pem` - No certificate files

**Build Configuration:**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"  # Version from git tags

[tool.hatch.build.targets.wheel]
packages = ["bundlecraft"]

[tool.hatch.build.targets.sdist]
exclude = [
  "/tests",
  "/scripts",
  "/config",
  "/cert_sources",
  "/build_cache",
  "/.github",
  "/personal-tests",
]
```

**README Focus:**

- Installation: `pipx install bundlecraft` or Docker usage
- Quick start pointing to bundlecraft-starter
- CLI reference and API documentation
- Prominent links to starter and example repos
- Security model explanation

**OCI Image Build:**

```dockerfile
# Multi-stage Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY bundlecraft/ ./bundlecraft/
RUN pip install --no-cache-dir build && \
    python -m build --wheel

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl default-jre-headless && \
    rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 bundlecraft
USER bundlecraft
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
ENTRYPOINT ["bundlecraft"]
```

**Release Workflow:**

```yaml
# .github/workflows/release.yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release-oci:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ghcr.io/bundlecraft-io/bundlecraft:${{ github.ref_name }}
            ghcr.io/bundlecraft-io/bundlecraft:latest
          provenance: true
          sbom: true

  release-pypi:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Needed for hatch-vcs
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          # PyPI Trusted Publishing (no token needed)
```

______________________________________________________________________

### 7.2 bundlecraft-starter (GitHub Template Repository)

**Purpose:** Minimal, ready-to-clone starting point for users to create their own trust bundle repository.

**Repository Structure:**

```text
bundlecraft-starter/
├── README.md                    # Quick start, customization guide
├── CUSTOMIZE.md                 # Detailed setup instructions
├── .gitignore                   # Exclude secrets, build outputs
├── .github/
│   └── workflows/
│       ├── build.yaml          # Build bundles using OCI image
│       └── verify.yaml         # Verify existing bundles
├── config/
│   ├── defaults.yaml           # Sensible defaults
│   ├── envs/
│   │   ├── dev.yaml           # Development environment config
│   │   └── prod.yaml          # Production environment config
│   └── sources/
│       ├── mozilla.yaml       # Mozilla CA bundle (working example)
│       └── internal.yaml.example  # Template for internal CAs
├── cert_sources/
│   ├── internal/              # Empty directory with README
│   │   └── README.md         # "Place your internal CAs here"
│   ├── staged/               # Empty with README
│   └── fetched/              # Created by fetch operations
├── scripts/
│   └── run-local.sh          # Helper: Run bundlecraft via Docker
└── LICENSE.example           # User should update this
```

**Key Features:**

- ✅ **GitHub Template enabled** - Users click "Use this template"
- ✅ **No real certificates** - Only directory structure with READMEs
- ✅ **Working examples** - `mozilla.yaml` demonstrates functional fetch
- ✅ **Documented workflows** - GitHub Actions show OCI integration
- ✅ **Security emphasis** - `.gitignore` and docs warn about secrets
- ✅ **Placeholder markers** - `[YOUR-ORG]` placeholders to replace

**README.md Content:**

```markdown
# [YOUR-ORG] Trust Bundle Repository

> 🎯 Created from [bundlecraft-starter](https://github.com/bundlecraft-io/bundlecraft-starter)

## Quick Start

1. **Use this template** or clone
2. **Add your certificates** to `cert_sources/internal/`
3. **Configure bundles** in `config/sources/` and `config/envs/`
4. **Run build:**
   ```bash
   ./scripts/run-local.sh build --env dev --bundle mozilla-only
   ``

## Customize for Your Organization

See [CUSTOMIZE.md](CUSTOMIZE.md):
- [ ] Replace `[YOUR-ORG]` placeholders
- [ ] Add internal CA certificates
- [ ] Configure environments and bundles
- [ ] Set up secrets (passwords, GPG keys)
- [ ] Review and update workflows

## Security Notes

⚠️ **Never commit:**
- Private keys or passwords
- Production certificates (fetch remotely instead)
- GPG signing keys

## Learn More

- 📚 [BundleCraft Core](https://github.com/bundlecraft-io/bundlecraft)
- 🎮 [Full Example](https://github.com/bundlecraft-io/bundlecraft-example)
```

**GitHub Actions Workflow:**

```yaml
# .github/workflows/build.yaml
name: Build Trust Bundles

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Mozilla bundle
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/config:/config \
            -v ${{ github.workspace }}/cert_sources:/cert_sources \
            -v ${{ github.workspace }}/dist:/dist \
            ghcr.io/bundlecraft-io/bundlecraft:latest \
            build --env dev --bundle mozilla-only

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: trust-bundles
          path: dist/
```

**Update Strategy:**

- Updated when core bundlecraft releases new versions
- Configuration schema changes reflected immediately
- Keep minimal - resist feature creep

______________________________________________________________________

### 7.3 bundlecraft-example (Reference Implementation)

**Purpose:** Fully functional, batteries-included example with dummy certificates. Always based on latest bundlecraft-starter.

**Repository Structure:**

```text
bundlecraft-example/
├── README.md                    # "This is a demo - explore freely!"
├── .gitignore                   # Less restrictive (includes dummy certs)
├── .github/
│   └── workflows/
│       ├── build-all.yaml      # Builds ALL bundle types
│       ├── verify.yaml         # Comprehensive verification
│       └── scheduled.yaml      # Weekly builds (automation demo)
├── config/
│   ├── defaults.yaml           # From starter
│   ├── envs/
│   │   ├── development.yaml   # Full config showing all options
│   │   ├── staging.yaml       # Environment layering example
│   │   └── production.yaml    # Production-like setup
│   └── sources/
│       ├── mozilla.yaml        # Public CA bundle
│       ├── internal-dev.yaml  # Points to dummy certs
│       ├── internal-prod.yaml # Production-like config
│       └── vault.yaml.example # Vault integration (non-functional)
├── cert_sources/
│   ├── internal/
│   │   ├── README.md          # "These are DUMMY test certificates"
│   │   ├── test-root-ca.pem   # Clearly labeled dummy cert
│   │   └── test-issuing-ca.pem
│   ├── staged/                # Pre-staged examples
│   └── fetched/               # Populated on first build
├── build_cache/               # Pre-built examples (optional)
│   └── development/
│       └── internal-dev/
│           ├── ca-bundle.pem
│           ├── ca-bundle.jks
│           ├── manifest.json
│           └── checksums.sha256
├── scripts/
│   ├── generate-dummy-certs.sh  # Generate test CAs
│   ├── run-all-builds.sh       # Build every bundle
│   └── clean-all.sh            # Reset to fresh state
├── docs/
│   └── SCENARIOS.md            # Common use cases walkthrough
└── LICENSE
```

**Key Features:**

- ✅ **Based on starter** - Inherits structure from bundlecraft-starter
- ✅ **Dummy certificates** - Generated test CAs with clear warnings
- ✅ **Complete configurations** - Every feature demonstrated
- ✅ **Pre-built outputs** - Sample build artifacts for reference
- ✅ **Multiple scenarios** - Dev, staging, prod examples
- ✅ **Immediately runnable** - `git clone && ./scripts/run-all-builds.sh`

**README.md Content:**

```markdown
# BundleCraft Example - Full Reference Implementation

> 🎮 **Playground repository** - All certificates are dummy test CAs.
> Clone it, modify it, break it, learn from it!

> 📋 **Based on [bundlecraft-starter](https://github.com/bundlecraft-io/bundlecraft-starter)**

## What This Demonstrates

✅ Complete BundleCraft setup with all features
✅ Multi-environment configuration (dev, staging, production)
✅ Multiple bundle types (internal, mozilla, combined)
✅ Certificate fetching from remote sources
✅ Build verification and signing workflows
✅ GitHub Actions automation

## Quick Start

```bash
git clone https://github.com/bundlecraft-io/bundlecraft-example.git
cd bundlecraft-example

# Build all bundles
./scripts/run-all-builds.sh

# Or build specific bundle
docker run --rm \
  -v $(pwd)/config:/config \
  -v $(pwd)/cert_sources:/cert_sources \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  build --env development --bundle internal-dev
``

## ⚠️ Dummy Certificates Warning

All certificates in `cert_sources/internal/` are **test certificates** generated by:
```bash
./scripts/generate-dummy-certs.sh
``

**DO NOT use these in production.** They are for learning only.

## Explore Different Scenarios

See [docs/SCENARIOS.md](docs/SCENARIOS.md):
- Adding a new internal CA
- Fetching from remote sources
- Setting up expiry warnings
- Configuring multiple environments
- Using different output formats
- Setting up signing and verification

## Create Your Own Repository

When ready for production:
1. ✅ Use [bundlecraft-starter](https://github.com/bundlecraft-io/bundlecraft-starter) template
2. ❌ Don't copy this example (contains dummy certs)
3. 📖 Follow starter's CUSTOMIZE.md guide

## Learn More

- 🔧 [BundleCraft Core](https://github.com/bundlecraft-io/bundlecraft)
- 🚀 [Starter Template](https://github.com/bundlecraft-io/bundlecraft-starter)
```

**Dummy Certificate Generator:**

```bash
# scripts/generate-dummy-certs.sh
#!/bin/bash
set -e

DEST="cert_sources/internal"
mkdir -p "$DEST"

echo "⚠️  Generating DUMMY certificates for demo purposes only"
echo "    These certificates should NEVER be used in production!"

# Generate test root CA
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /tmp/dummy-root-key.pem \
  -out "$DEST/test-root-ca.pem" \
  -subj "/C=US/O=BundleCraft Example/CN=Test Root CA (DO NOT TRUST)"

echo "✅ Generated: $DEST/test-root-ca.pem"
echo "   Subject: Test Root CA (DO NOT TRUST)"
echo ""
echo "   ⚠️  This is a DUMMY certificate for demonstration only!"

# Add warning comment to file
sed -i '1i# WARNING: DUMMY CERTIFICATE FOR DEMO PURPOSES ONLY - DO NOT USE IN PRODUCTION' "$DEST/test-root-ca.pem"

rm -f /tmp/dummy-root-key.pem
```

**Update Strategy:**

- Regenerated from bundlecraft-starter whenever starter updates
- Dummy certificates regenerated with each starter sync
- New features from core immediately reflected in examples
- Maintains relationship: `example = starter + dummy_data + full_configs`

______________________________________________________________________

## 8) Release Process

### 8.1 bundlecraft (Core Engine)

**Trigger:** Git tag push (e.g., `v1.0.0`)

**Automated Steps:**

1. **Tag and push:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **GitHub Actions automatically:**
   - Runs full test suite
   - Builds OCI image with multi-stage Dockerfile
   - Pushes to `ghcr.io/bundlecraft-io/bundlecraft:v1.0.0` and `:latest`
   - Signs image with GitHub's Sigstore integration
   - Generates SBOM and provenance attestation
   - Builds Python wheel with hatch-vcs (version from tag)
   - Publishes to PyPI via Trusted Publishing (OIDC)
   - Creates GitHub Release with auto-generated notes

**Verification:**

```bash
# Verify OCI image provenance
docker buildx imagetools inspect \
  ghcr.io/bundlecraft-io/bundlecraft:v1.0.0 \
  --format "{{json .Provenance}}"

# Verify PyPI package
pip download --no-deps bundlecraft==1.0.0
# Sigstore signatures available via PyPI's transparency log
```

### 8.2 bundlecraft-starter (Template)

**Trigger:** Manual update after core releases or config schema changes

**Manual Steps:**

1. Review changes in core bundlecraft
2. Update `config/defaults.yaml` if schema changed
3. Update example workflows to reference new version
4. Update README with any new features
5. Tag with date: `git tag 2025.10.23`
6. No CI/CD needed (not distributed as artifact)

### 8.3 bundlecraft-example (Reference)

**Trigger:** After bundlecraft-starter updates

**Process:**

1. Pull latest bundlecraft-starter changes
2. Regenerate dummy certificates if needed
3. Update all example configurations
4. Run builds to generate fresh `build_cache/` examples
5. Update docs/SCENARIOS.md with new features
6. Tag with date: `git tag 2025.10.23`
7. No CI/CD needed (not distributed as artifact)

**Relationship:** `example = starter + dummy_certs + full_configs + pre_built_outputs`

______________________________________________________________________

## 9) Migration Strategy

### Phase 1: Prepare Core Repository (bundlecraft)

- [x] Identify files to remain vs. move to starter/example
- [ ] Create `Dockerfile` for OCI distribution
- [ ] Update `pyproject.toml`:
  - Switch to hatchling + hatch-vcs
  - Configure proper exclusions
- [ ] Create `.github/workflows/release.yaml` for OCI and PyPI
- [ ] Move `config/`, `cert_sources/` to temporary staging directory
- [ ] Update README:
  - Focus on installation and API usage
  - Add prominent links to starter and example repos
- [ ] Set up PyPI Trusted Publishing in PyPI project settings
- [ ] Tag as `v0.2.0` once ready for first official release

### Phase 2: Create Starter Template

- [ ] Create new repository: `bundlecraft-starter`
- [ ] Enable "Template repository" in GitHub settings
- [ ] Copy minimal config structure from core repo staging
- [ ] Remove all real certificates
- [ ] Add placeholder READMEs in empty directories
- [ ] Create example GitHub Actions workflows
- [ ] Write comprehensive CUSTOMIZE.md guide
- [ ] Add security warnings to .gitignore and README
- [ ] Ensure `mozilla.yaml` works as functional example
- [ ] Tag as `2025.10.23` (date-based versioning)

### Phase 3: Create Example Repository

- [ ] Clone bundlecraft-starter as foundation
- [ ] Add `scripts/generate-dummy-certs.sh`
- [ ] Generate initial dummy certificates
- [ ] Add full configuration examples (all environments)
- [ ] Build example outputs for `build_cache/`
- [ ] Write comprehensive docs/SCENARIOS.md
- [ ] Add automation scripts (run-all-builds.sh, clean-all.sh)
- [ ] Add scheduled workflow (weekly builds)
- [ ] Tag as `2025.10.23` (mirrors starter version)

### Phase 4: Documentation & Cross-Linking

- [ ] Update bundlecraft README with links to starter/example
- [ ] Update this ADR with actual repo URLs
- [ ] Create "Getting Started" guide in bundlecraft docs
- [ ] Add cross-repo navigation to all README files
- [ ] Update SECURITY.md to reference starter's security practices
- [ ] Announce split on any relevant channels

______________________________________________________________________

## 10) What This Achieves

✅ **Clear separation of concerns:** Engine vs. user configurations
✅ **Security:** Signed artifacts, trust separation, no secrets in CI
✅ **Simplicity:** Two distribution channels (OCI + PyPI), standard tooling
✅ **Maintainability:** GitHub-native features, well-documented
✅ **Usability:** Container for automation, pip/pipx for developers
✅ **Progressive learning:** Minimal starter → comprehensive example
✅ **Quick onboarding:** Template repo = instant start for new users
✅ **Reference implementation:** Example shows all features in action

______________________________________________________________________

## 11) Decision

BundleCraft will adopt a **three-repository architecture**:

1. **bundlecraft** - Core engine distributed via OCI (GHCR) and PyPI
   - Signed artifacts via GitHub's native Sigstore integration
   - Engine-only package with zero user configs
   - Versioned releases using semantic versioning

2. **bundlecraft-starter** - Minimal GitHub Template repository
   - Provides essential structure and working examples
   - Users click "Use this template" for instant setup
   - Updated when core releases or schema changes

3. **bundlecraft-example** - Full reference implementation
   - Always based on latest bundlecraft-starter
   - Contains dummy certificates and complete configurations
   - Demonstrates all features and common scenarios

This architecture maintains solo-developer sustainability while providing clear paths for users at different experience levels.

Advanced distribution features (PEX, GitHub Action, multi-arch, weekly scans) remain deferred to **ADR-0007**.

______________________________________________________________________

## 12) Next Steps

### Immediate (Core Repository)

1. Create `Dockerfile` with secure multi-stage build
2. Update `pyproject.toml` to use hatchling + hatch-vcs
3. Create `.github/workflows/release.yaml` for automated releases
4. Set up PyPI Trusted Publishing

### Near-term (Starter & Example)

5. Create bundlecraft-starter repository with minimal structure
6. Create bundlecraft-example based on starter with full examples
7. Update all documentation with cross-repo links

### Documentation

8. Update main README with repository architecture overview
9. Update SECURITY.md with references to starter practices
10. Create "Getting Started" guide linking to appropriate repos

______________________________________________________________________
