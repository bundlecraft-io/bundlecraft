# ADR-0006: Core Release & Distribution Strategy (MVP)

**Status:** Proposed - **Supersedes ADR-0001 and ADR-0003**
**Date:** October 21, 2025
**Owner:** Chris J. Pich
**Related:** SECURITY.md, README, CI/CD workflows, ADR-0007 (future enhancements)

---

## 1) Context

ADR-0001 established an OCI-only distribution model for BundleCraft, while ADR-0003 later evolved this into a multi-channel approach. This ADR consolidates both into a **pragmatic, maintainable MVP** suitable for a solo developer's first project, with advanced features deferred to ADR-0007.

As a security-focused PKI tool, we need trustworthy distribution without over-engineering or creating maintenance burden.

---

## 2) Problem Statement

We need a **simple, secure release strategy** that:

* Provides **OCI container** for CI/CD workflows (primary use case)
* Offers **PyPI package** for local development and testing
* Includes **template repository** for user onboarding
* Keeps trust materials **separate** from distributed artifacts
* Is **maintainable by one person** without complex tooling

---

## 3) Goals & Non-Goals

### Goals (MVP)

* Publish a **signed OCI image** to GHCR with basic provenance
* Publish an **engine-only PyPI package** for pipx/pip installation
* Provide a **template repository** showing best practices
* Exclude trust data from all distributed artifacts
* Use GitHub's native signing capabilities (Sigstore integration)
* Single-source versioning from git tags

### Non-Goals (Deferred to ADR-0007)

* PEX/zipapp artifacts (niche use case, adds complexity)
* Custom GitHub Action wrapper (users can call OCI directly)
* Advanced SLSA provenance levels
* Weekly CVE scanning automation
* Multi-architecture builds (start with amd64, add arm64 later if needed)
* Hash-locked dependency files (use standard pyproject.toml constraints)

---

## 4) Simplified Distribution Model (MVP)

| Channel              | Description                                            | Use Case                        | Security                      | Status |
| -------------------- | ------------------------------------------------------ | ------------------------------- | ----------------------------- | ------ |
| **OCI image (GHCR)** | Signed container image with attestation               | CI/CD pipelines, automation     | GitHub-native Sigstore/cosign | MVP    |
| **PyPI package**     | Engine-only Python package for pipx/pip installation  | Local dev, testing, exploration | PyPI Trusted Publishing       | MVP    |
| **Template Repo**    | Reference implementation showing best practices       | User onboarding                 | Documentation only            | MVP    |

**Deferred to ADR-0007 (Future):** PEX/zipapp artifacts, GitHub Action wrapper, advanced SBOM/SLSA levels, multi-arch builds, weekly CVE automation.

---

## 5) Security Principles (Simplified)

* **Trust separation:** certs/configs are always mounted or fetched, never bundled in artifacts
* **Native signing:** leverage GitHub's built-in Sigstore integration for both OCI and PyPI
* **Version from tags:** single source of truth using git tags
* **No secrets in CI:** use OIDC for PyPI Trusted Publishing and GHCR
* **Clear documentation:** explain security model and verification steps

---

## 6) Implementation Details

### 6.1 OCI Image (Primary Distribution)

**Build:**
* Simple Dockerfile with `python:3.12-slim` base
* Multi-stage build: dependencies → application → minimal runtime
* Non-root user, minimal attack surface
* Entrypoint runs BundleCraft CLI

**Release:**
* GitHub Actions build on tag push
* Push to `ghcr.io/chrisjpich/bundlecraft:vX.Y.Z` and `:latest`
* Automatic signing via GitHub's Sigstore integration (no manual cosign setup needed)
* Basic attestation with build provenance

**Usage:**

```bash
docker run --rm -v $(pwd)/config:/config ghcr.io/chrisjpich/bundlecraft:latest build --bundle production
```

### 6.2 PyPI Package (Developer Tool)

**Build:**
* Use `hatchling` with version from git tags (`hatch-vcs`)
* `MANIFEST.in` excludes: `config/`, `build_cache/`, `sources/`, `tests/`, `*.jks`, `*.pem`
* `pyproject.toml` defines entry point for CLI

**Release:**
* GitHub Actions builds wheel on tag push
* PyPI Trusted Publishing (OIDC) - no API tokens needed
* Automatic Sigstore signing via PyPI's native integration

**Usage:**

```bash
pipx install bundlecraft
bundlecraft build --bundle production
```

**Documentation note:** Package does not modify system trust stores; user provides trust data via config.

### 6.3 Template Repository

**Structure:**

```
bundlecraft-template/
├── README.md              # Getting started, security notes
├── .github/workflows/
│   └── build.yml          # Example using OCI image
├── config/
│   └── bundles/
│       └── example.yaml   # Sample config (non-sensitive)
└── scripts/
    └── run.sh             # Helper script for local Docker invocation
```

**Purpose:**
* Show best-practice directory layout
* Demonstrate OCI workflow integration
* Emphasize trust material separation in docs
* Provide working example users can clone and adapt

---

## 7) Release Process (Simplified)

### Manual Steps

1. Update version if needed (or rely on git tag)
2. Create and push tag: `git tag v1.0.0 && git push origin v1.0.0`
3. GitHub Actions automatically:
   * Builds OCI image → pushes to GHCR → signs
   * Builds Python wheel → publishes to PyPI → signs
   * Creates GitHub Release with notes

### Automated Workflow

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']

jobs:
  build-oci:
    # Build and push Docker image
    # Uses docker/build-push-action with attestations

  build-pypi:
    # Build wheel with hatch
    # Publish with PyPI Trusted Publishing
```

### Verification

**OCI:**

```bash
docker buildx imagetools inspect ghcr.io/chrisjpich/bundlecraft:v1.0.0 --format "{{json .Provenance}}"
```

**PyPI:** Sigstore signatures automatically available via PyPI's transparency log

---

## 8) What This Achieves

✅ **Security:** Signed artifacts, trust separation, no secrets in CI
✅ **Simplicity:** Two channels (OCI + PyPI), standard tooling, minimal custom code
✅ **Maintainability:** GitHub-native features, well-documented, no complex dependencies
✅ **Usability:** Container for automation, pip/pipx for developers, template for onboarding

---

## 9) Decision

BundleCraft will adopt a **pragmatic two-channel distribution** (OCI + PyPI) plus a template repository for MVP:

1. **OCI image** as primary distribution for CI/CD (signed via GitHub native Sigstore)
2. **PyPI package** for developer convenience (engine-only, Trusted Publishing)
3. **Template repo** for user onboarding and best practices

Advanced features (PEX, GitHub Action, multi-arch, weekly scans) deferred to **ADR-0007** to maintain solo-developer sustainability.

---

## 10) Next Steps

1. Create `Dockerfile` with secure multi-stage build
2. Add `MANIFEST.in` and configure `hatch-vcs` in `pyproject.toml`
3. Create `.github/workflows/release.yml` with OCI and PyPI jobs
4. Set up PyPI Trusted Publishing in PyPI settings
5. Create template repository with working example
6. Update README and SECURITY docs with usage and verification guidance

---

**End of ADR-0006 - Supersedes ADR-0001 and ADR-0003**

## 5) Security Principles

* **OCI-first:** all channels derive from the same source and commit hash as the OCI build.
* **Separation of trust data:** certs/configs are always mounted or fetched, never bundled.
* **Universal provenance:** all release artifacts reference the OCI digest in metadata.
* **Signed everything:** OCI → cosign; PyPI → Sigstore; zipapp → detached signature; GH Action → image digest pinning.
* **Continuous scanning:** OCI images and dependencies rebuilt and re-scanned weekly for CVE refresh.

---

## 6) Channel Implementations

### 6.1 OCI Image (Authoritative)

* Built via multi-arch `buildx` pipeline targeting `linux/amd64` and `linux/arm64`.
* Signed with **cosign (OIDC)**.
* SBOM and provenance generated via **syft** and **SLSA generator**.
* Pushed to **ghcr.io/<org>/bundlecraft:<semver>** and `:latest`.
* Digest pinned and attached to all downstream artifacts.

### 6.2 pipx/PyPI Package (Engine-Only)

* Built using `hatchling` with **MANIFEST.in** exclusions for trust data.
* Signed with **Sigstore** at publish time.
* Dependencies are hash-locked in `requirements.lock`.
* SBOM (CycloneDX + SPDX) attached to GitHub Release.
* Recommended install method:

  ```bash
  pipx install bundlecraft==X.Y.Z
  ```
* Usage warning: package does not install or modify trust stores; acts only as CLI engine.

### 6.3 zipapp/PEX Artifact

* Built from the same wheel as the PyPI package using `python -m zipapp` or `pex`.
* Bundles dependencies internally for offline execution.
* Published in GitHub Releases with SHA-256 checksums and detached `.asc` signature.
* Ideal for air-gapped networks or systems without Python installed.

### 6.4 GitHub Action Wrapper

* Dedicated repo: `bundlecraft/action`.
* Wraps the OCI image and exposes key commands:

  ```yaml
  - name: Build bundles
    uses: bundlecraft/action@vX.Y.Z
    with:
      bundle: internal
      env: prod
  ```
* Validates OCI signature on invocation.
* Adds digest pinning to avoid tag drift.

### 6.5 GitHub Template Repo

* Reference skeleton for orgs:

  * Directory layout (`config/`, `sources/`, `build/`)
  * Example workflow using OCI or Action.
  * README and SECURITY emphasizing trust separation.
  * Optional wrapper script for `podman` invocation.

---

## 7) Security Measures Across Channels

* **OCI:** cosign + SBOM + provenance attestations.
* **PyPI:** Sigstore-signed wheels + hash-lock + SBOM.
* **Zipapp:** detached signature + checksum.
* **Action:** runs verified OCI image only.
* **Template:** static, educational only.

Regular scans for vulnerabilities across all dependencies and base images ensure consistent posture.

---

## 8) Release Pipeline Overview

### 8.1 Common Steps

1. Tag release in GitHub (`vX.Y.Z`).
2. Build and verify OCI image.
3. Derive all secondary channels (PyPI, zipapp, Action) from same commit.
4. Publish artifacts, SBOMs, and signatures under one GitHub Release.

### 8.2 Signing Summary

| Artifact   | Signing Method                | Provenance       | Storage            |
| ---------- | ----------------------------- | ---------------- | ------------------ |
| OCI Image  | Cosign (OIDC)                 | SLSA attestation | GHCR               |
| PyPI Wheel | Sigstore                      | SBOM JSON        | PyPI + GH Releases |
| Zipapp/PEX | GPG or Sigstore detached      | SHA-256 checksum | GH Releases        |
| Action     | Inherits OCI digest signature | OCI digest ref   | GitHub Marketplace |

---

## 9) Operational Playbook

**Cutting a Release**

1. Create and push tag `vX.Y.Z`.
2. CI runs composite release workflow:

   * `release-oci`: build & sign image
   * `release-pypi`: build, sign, publish engine-only package
   * `release-zipapp`: build self-contained binary, sign
   * `release-action`: update bundlecraft/action metadata
3. Consolidate SBOMs, checksums, and digests into `RELEASE.md`.

**Verification**

```bash
cosign verify ghcr.io/org/bundlecraft@sha256:<digest>
sigstore verify identity --certificate bundlecraft-*.whl.sigstore
sha256sum -c bundlecraft.pyz.sha256
```

---

## 10) Governance & Compliance

* Aligns with PKI best practices by ensuring clear separation of trust policy from engine distribution.
* All artifacts are immutable, traceable, and non-side-effectful.
* Signed provenance satisfies internal audit and external verification.
* Versioning: semantic + reproducible across all channels.

---

## 11) Decision

**BundleCraft will adopt a multi-channel release model that supersedes ADRs #1 and #3**, consolidating their philosophies into a single secure, flexible strategy:

1. **OCI image (authoritative)** remains the primary and signed distribution.
2. **pipx/PyPI (engine-only)** channel adds developer accessibility without compromising security.
3. **zipapp/PEX** provides offline and air-gapped portability.
4. **GitHub Action** enables plug-and-play CI integration.
5. **Template Repo** continues to serve as onboarding reference.

All channels share unified signing, SBOM, and provenance controls, maintaining BundleCraft’s commitment to transparency, reproducibility, and security in PKI-sensitive environments.

---

## 12) Next Steps

1. Integrate multi-channel release workflow into CI.
2. Add Sigstore signing to PyPI and zipapp stages.
3. Implement digest pinning verification within the GitHub Action.
4. Update documentation across README, SECURITY, and RELEASE to reflect new unified model.
5. Schedule recurring dependency and CVE audits.

---

**End of ADR-000X - supersedes ADR-0001 and ADR-0003**
