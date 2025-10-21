# ADR-0003: Distribute BundleCraft via multiple channels — OCI-first, with optional pipx/PyPI, zipapp, and a first-class GitHub Action

Status: Deferred (amended by ADR-0003, ADR-0006)
Date: October 18, 2025
Owner: BundleCraft maintainers
Related: ADR-0001, README, SECURITY.md, RELEASE.md, CI/CD workflows

---

## 1) Context update

ADR-0001 recommended distributing BundleCraft primarily as an OCI-compliant container image and a template repository, explicitly avoiding PyPI. As the project matured (craft configs, CI filtering, clearer separation of bundle vs craft responsibilities), we revisited distribution to balance security, developer UX, and portability.

The goal: keep trust-sensitive workflows safe and reproducible while making local adoption and CI integration simple.

---

## 2) Problem restated

We need a distribution strategy for the BundleCraft engine (the Python CLI and config framework) that:

- Preserves a strong supply-chain posture (signing, SBOM, provenance, digest pinning)
- Works across CI systems and developer laptops without bespoke setup
- Avoids any implication that BundleCraft “installs CA certificates” on hosts
- Keeps organization-specific configs and certs outside the engine artifact

---

## 3) Options considered (revisited)

- OCI image (GHCR) — immutable, signed, attested; inputs mounted at runtime
- PyPI package — convenient installs; possible via pipx for isolation
- Single-file artifacts — zipapp/PEX for air-gapped or no-container environments
- Package managers — Homebrew/Nix wrappers (optional, community-friendly)
- First-class GitHub Action — simple CI integration that wraps the engine
- Template repo — onboarding and reference patterns

---

## 4) Evaluation highlights

- Security and reproducibility are best with OCI images (signable, attestable, digest-pin-able).
- Developer convenience improves with a pipx-installable CLI, provided we constrain scope and secure publishing/signing.
- Single-file artifacts (zipapp/PEX) help when containers are disallowed or Python isn’t available.
- A GitHub Action directly wrapping the image simplifies CI adoption.

PyPI itself is not inherently insecure, but it requires additional process controls (signing, hashes, locked deps) to meet our bar.

---

## 5) Recommended distribution strategy

We adopt a multi-channel approach, ranked by recommendation:

1) Primary: OCI image on GHCR

    - Signed with cosign; SBOM and SLSA-style provenance attached as OCI attestations
    - Multi-arch (linux/amd64, linux/arm64)
    - Inputs/outputs mounted at runtime; image contains engine only (no certs/configs)

2) Secondary: pipx-installed CLI via PyPI (optional)

    - Publish a minimal, engine-only package designed for pipx (isolated venv)
    - Strong controls: Sigstore signing of wheels/sdist; pinned, minimal dependencies; reproducible build with hash-locked requirements; publish SBOM in releases
    - Clear docs: “engine only — does not install system trust; provide your own config/certs”
    - Recommended usage: pipx install bundlecraft==X.Y.Z (pin exact version)

3) Secondary: Single-file artifact (zipapp or PEX) in GitHub Releases

    - Self-contained executable with vendored dependencies for offline/air-gapped usage
    - Publish checksums, signatures, and SBOM alongside

4) Optional convenience wrappers

    - GitHub Action: bundlecraft/action that wraps the OCI image
    - Homebrew/Nix shells (community-supported) that either call the image or install the pipx package

Template repository remains part of onboarding: directory layout, example crafts/bundles, and a CI workflow calling the OCI image or Action.

---

## 6) Guardrails for the PyPI channel

If we offer a PyPI package, we will:

- Treat it as an “engine-only” distribution — no embedded certificates, no example trust, no side-effectful system modifications
- Prefer pipx for isolation and version pinning; discourage plain pip installs into shared environments
- Sign distributions (Sigstore), attach SBOMs, and publish SLSA provenance in GitHub Releases
- Lock dependencies and enforce hashes; avoid optional extras by default
- Provide clear documentation that all certificate inputs come from user repositories/mounts and that the CLI never alters host trust stores

Rationale: This gives developer convenience while preserving the core security posture and composability of BundleCraft.

---

## 7) Security measures across all channels

- Cosign signatures and provenance for OCI images; SBOMs as OCI attestations
- Signed wheels/sdist (Sigstore) for PyPI; SBOM published under GitHub Releases
- Hash-locked dependencies, pinned base images, minimal attack surface
- Continuous scanning of images; regular rebuilds for CVE churn
- No embedded CA trust; all certs/configs remain external inputs

---

## 8) Migration and compatibility

Existing usage (Python directly, template repo, OCI image) remains valid. The additional channels are additive. Docs will present “OCI-first”, then pipx/PyPI, then zipapp/PEX as alternatives.

---

## 9) Decision

Adopt a multi-channel distribution model:

- Primary: OCI image on GHCR (signed, SBOM, provenance)
- Secondary: pipx-friendly PyPI package (engine-only; signed; locked)
- Secondary: single-file zipapp/PEX release
- Optional: GitHub Action wrapper; Homebrew/Nix wrappers

This supersedes ADR-0001’s “no PyPI” stance by allowing a tightly controlled, pipx-first PyPI channel for developer convenience without compromising trust posture.

---

## 10) Next steps

1. Add a container build-and-release workflow with cosign, syft (SBOM), provenance
2. Prepare packaging metadata for a minimal engine-only PyPI package; integrate Sigstore signing; document pipx usage
3. Add a zipapp/PEX build step to Releases; publish checksums and signatures
4. Create bundlecraft/action repository that wraps the OCI image for CI
5. Update README/SECURITY/RELEASE with channel guidance and digest-pinning examples
