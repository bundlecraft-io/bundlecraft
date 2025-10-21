# ADR-0006: Introduce the Core Multi-Channel BundleCraft Release & Distribution Layer

**Status:** Proposed - **Supersedes ADR-0001 and ADR-0003**
**Date:** October 21, 2025
**Owner:** Chris J. Pich
**Related:** SECURITY.md, RELEASE.md, README, CI/CD workflows

---

## 1) Context

ADR-0001 established an OCI-only distribution model for BundleCraft, while ADR-0003 later evolved this into a multi-channel approach that prioritized **OCI-first** but allowed tightly controlled alternatives like **pipx/PyPI**, **zipapp/PEX**, and a **GitHub Action wrapper**.

This new ADR consolidates and supersedes both, integrating best PKI practices and current project philosophies to define a unified release and distribution model for BundleCraft as it enters public adoption.

---

## 2) Problem Statement

We need a comprehensive release and distribution strategy that:

* Preserves **trust and reproducibility** for security-sensitive PKI workflows.
* Supports **developer onboarding** and **local experimentation** without compromising integrity.
* Delivers the engine in multiple secure formats (OCI, pipx, zipapp, GitHub Action).
* Keeps all organization-specific configs and CA materials outside the distributed artifacts.

---

## 3) Goals & Non-Goals

### Goals

* Offer a **multi-channel distribution** model that remains OCI-first but inclusive of developer-friendly and offline channels.
* Ensure all distribution artifacts are **signed, attestable, and SBOM-tracked**.
* Support **pipx**, **zipapp**, and **OCI** as equal citizens in terms of CLI behavior.
* Maintain single-source versioning and release provenance across channels.

### Non-Goals

* Embedding any CA or trust material within the distributed artifacts.
* Publishing unverified or unsigned releases.
* Treating PyPI or zipapps as authoritative for trust-chain purposes.

---

## 4) Unified Distribution Model

| Channel              | Description                                                  | Use Case                            | Signing / Attestation                         | Trust Level       |
| -------------------- | ------------------------------------------------------------ | ----------------------------------- | --------------------------------------------- | ----------------- |
| **OCI image (GHCR)** | Canonical, signed, reproducible container image              | Enterprise CI/CD, secure automation | cosign (OIDC), syft SBOM, SLSA provenance     | **Authoritative** |
| **pipx/PyPI**        | Engine-only package, signed via Sigstore; installed via pipx | Developers, local experiments       | Sigstore-signed wheel, SBOM in GitHub release | Moderate          |
| **zipapp/PEX**       | Self-contained Python artifact, no container runtime needed  | Air-gapped or restricted hosts      | Detached signature + checksum                 | Moderate          |
| **GitHub Action**    | Wrapper around OCI image for CI pipelines                    | Simplified GitHub CI integration    | Uses signed OCI base image                    | High              |
| **Template Repo**    | Reference implementation for orgs                            | Onboarding and documentation        | N/A                                           | Informational     |

---

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
