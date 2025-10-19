# ADR-0001: Distribute BundleCraft as an OCI-compliant container image (plus template repo); do **not** publish a PyPI package

**Status:** Accepted (amended by ADR-0003)
**Date:** October 16, 2025
**Owner:** BundleCraft maintainers
**Related:** SECURITY.md, RELEASE.md, CI/CD workflows, README

---

## 1) Context

BundleCraft is a framework/utility for building, verifying, and packaging **CA trust bundles** from organization-specific sources and policies. Historically we have distributed the code as a Git repo to be cloned and run in CI. We’re evaluating a **major change** to how BundleCraft is offered, maintained, and used:

* Ship BundleCraft as a **containerized CLI** (OCI-compliant image) that teams run locally and in CI by mounting their own `config/`, `sources/`, and `build/` dirs.
* Provide a **GitHub template repository** to jump-start projects (directory layout, sample configs, a working CI workflow that runs the image).
* Explicitly **avoid** distribution via public or private PyPI.

We treat “Docker” as shorthand in legacy conversations only. Our solution should use **modern OCI language and tooling** (e.g., `podman`, `containerd`, `buildx/BuildKit`, GHCR), not rely on Docker-specific assumptions.

---

## 2) Problem Statement

We need a distribution model that:

* Is **secure** for trust-sensitive workflows (no implied trust of third-party package registries for code that touches CA roots).
* Is **reproducible and portable** across developers and CI systems.
* Minimizes **dependency drift** and “works on my machine” issues.
* Supports **signing, SBOMs, and provenance** for supply-chain integrity.
* Stays **agnostic** to runtimes (Podman, containerd) and registries (GHCR, ECR, ACR, Artifactory).
* Keeps **configs and certificates** out of the distribution artifact; they are inputs supplied at runtime.

---

## 3) Goals & Non-Goals

### Goals

* Provide a single, immutable, reproducible **engine** users can run anywhere.
* Support **attested releases**: image signatures, SBOMs, and provenance.
* Keep operational UX simple for both **local and CI** use.
* Permit **air-gapped**/restricted environments (image mirroring/tar export).

### Non-Goals

* We will **not** publish a pip-installable library or CLI to PyPI.
* We will **not** embed sample or real **CA certs** in the image.
* We will **not** depend on a specific container brand/desktop app.

---

## 4) Options Considered

### Option A — GitHub Template Repo only (status quo+)

Users clone a repo with scripts, run Python directly, and wire it in CI.

* **Pros:** Simple, transparent; no runtime requirements beyond Python.
* **Cons:** Dependency drift; local Python setup pain; reduced reproducibility; harder to enforce SBOM/provenance; CI runners vary.

### Option B — PyPI CLI package

Publish BundleCraft as a Python package with a console entrypoint.

* **Pros:** Familiar install (`pip install`), easy updates.
* **Cons (critical):** Supply-chain risk (registry trust); stale/rogue package risk; misaligned with environment-specific trust policies; dependency pinning harder; reproducing builds across orgs is less deterministic.

### Option C — OCI-compliant container image

Ship a slim, non-root, read-only image that exposes a CLI; users mount inputs/outputs.

* **Pros:** Reproducible, portable, runner-agnostic (Podman/containerd); no host Python; easy to **sign**, attach **SBOM**, and generate **provenance**; easy to pin by **digest**; perfect for CI.
* **Cons:** Requires a container runtime; image build/release pipeline to maintain; attention to image size and CVE churn.

### Option D — Hybrid: OCI image **+** Template Repo (Recommended)

Publish the engine as an OCI image; provide a template repo that uses the image in CI and documents local invocation. No PyPI.

* **Pros:** Combines reproducibility of Option C with developer onboarding of Option A; keeps certs/configs in user repos; enables organization-specific policy without forking engine code.
* **Cons:** Two artifacts to maintain (image + template); light coordination needed between docs and image versions.

---

## 5) Evaluation Criteria

| Criterion                                                  | A: Template | B: PyPI | C: OCI Image |                   D: Hybrid |
| ---------------------------------------------------------- | ----------: | ------: | -----------: | --------------------------: |
| **Security posture** (no external trust, signing, SBOM)    |           △ |       ✕ |        **◎** |                       **◎** |
| **Reproducibility** (pin by digest, locked deps)           |           △ |       △ |        **◎** |                       **◎** |
| **Supply-chain integrity** (sigstore/cosign, provenance)   |           △ |       △ |        **◎** |                       **◎** |
| **Developer UX (local)**                                   |           ○ |   **◎** |            ○ | **◎** (via simple wrappers) |
| **CI/CD UX**                                               |           ○ |       ○ |        **◎** |                       **◎** |
| **Policy alignment** (org-specific trust inputs)           |           ○ |       △ |        **◎** |                       **◎** |
| **Operational portability** (Podman, containerd, GHCR/ECR) |           ○ |       △ |        **◎** |                       **◎** |
| **Maintenance cost**                                       |       **◎** |       ○ |            ○ |                           ○ |

Legend: **◎ excellent**, ○ good, △ mixed, ✕ poor

**Notes:**

* PyPI is rejected primarily on **security & policy** grounds for trust tooling.
* OCI images best support **signing, SBOMs, provenance**, and **digest pinning**.

---

## 6) Modern Tooling & Practices (no “Docker-only” assumptions)

* **Build:** BuildKit (`docker buildx`) or `podman build` targeting **OCI** format; multi-arch (amd64/arm64).
* **Runtime:** `podman run` or any **containerd**-backed runtime; `docker run` remains compatible for teams that have it.
* **Registry:** GHCR by default; support mirrors to ECR/ACR/Artifactory.
* **Signing:** `cosign sign` (keyless with OIDC or key-based).
* **SBOM:** `syft` to generate **CycloneDX**/**SPDX**; attach as artifacts and OCI attestations.
* **Scanning:** `grype` (build-time gates) and/or registry scanners.
* **Provenance:** SLSA-style provenance attestations tied to CI (e.g., GitHub OIDC).
* **Image Hardening:** non-root user, read-only filesystem, `no-new-privileges`, minimal base (python:*-slim or distroless + PEX/zipapp), pinned deps, automatic rebuilds for CVE refresh.

---

## 7) High-Level Design

**Distribution unit:** `ghcr.io/<org>/bundlecraft:<semver>` (also `:latest`)
**Invocation pattern:**

```bash
podman run --rm \
  -v $PWD/config:/app/config:ro \
  -v $PWD/sources:/app/sources:ro \
  -v $PWD/build:/app/build:rw \
  ghcr.io/<org>/bundlecraft:v1.0.0 \
  --env prod --bundle internal
```

**Key properties:**

* **Inputs mounted** (`config/`, `sources/`) are org-owned; the image contains only the **engine**.
* **Outputs** (`build/`) are written to the host volume for release/upload.
* **No embedded CAs** in the image.
* **SemVer** versioning; consumers may **pin by digest** for immutability.

---

## 8) Security Considerations

* Avoid PyPI supply-chain risks for trust tooling.
* Sign every image; publish **SBOM** and **provenance** with each release.
* Run as **non-root** with **read-only** FS; limit syscalls/capabilities where feasible.
* Keep base images minimal and updated; alert on CVEs; rebuild regularly.
* Provide **checksums** for produced artifacts and (optional) detached **GPG signatures** for release bundles.

---

## 9) Migration Plan

1. **Refactor** the current CLI entrypoint for container use (no code change required beyond clean entrypoint).
2. **Create Dockerfile (OCI)** with BuildKit optimizations; add CI job to build multi-arch images.
3. **Add signing** (cosign), **SBOM** (syft), **scan** (grype), **provenance** attestation steps to the release workflow.
4. **Publish** images to GHCR; document mirroring to other registries.
5. **Provide a template repo** that:

   * Demonstrates the directory layout (`config/`, `sources/`, `build/`)
   * Includes a CI workflow that pulls the image and runs a sample build
   * Shows how to verify the image signature and SBOM
6. **Docs:** Update README/SECURITY/RELEASE to reflect image-based usage; add `podman` examples first, mention `docker` only as compatible.

---

## 10) Backward Compatibility

* Existing users running the Python script directly can continue to do so.
* We will **not** publish to PyPI; any previous instructions to `pip install` will be removed.
* Provide a thin **shell wrapper** (`bin/bundlecraft`) that forwards to `podman run …` to keep a CLI feel.

---

## 11) Risks & Mitigations

| Risk                               | Impact            | Mitigation                                                                                    |
| ---------------------------------- | ----------------- | --------------------------------------------------------------------------------------------- |
| Teams lack a container runtime     | Adoption friction | Document `podman` install; provide tarball export + `podman load`; support air-gapped mirrors |
| Image CVE churn                    | Security noise    | Minimal base; weekly rebuild; automated scans; pin deps; rapid patch releases                 |
| Registry outages                   | Build failures    | Allow mirrors; publish digests; support offline image loading                                 |
| Perception of “Docker requirement” | Confusion         | Use **OCI** terminology; examples use `podman`; note docker is optional/compatible            |
| Larger artifact size vs pip        | Bandwidth         | Slim base, multi-stage builds, cache layers; optional distroless + zipapp                     |

---

## 12) Testing Strategy

* **Unit/integration tests** run inside the image during CI.
* **Golden tests** for config→artifact determinism (byte-stable outputs where feasible).
* **CVE gating**: fail CI on criticals unless explicitly waived.
* **Signature verification** and **attestation validation** as separate CI steps.
* **Cross-platform** validation (linux/amd64, linux/arm64).

---

## 13) Operational Playbook (summary)

* **Build:** `buildx bake` or `podman build` (multi-arch).
* **Tagging:** `vX.Y.Z`, `latest`; publish **digest**.
* **Sign:** `cosign sign …` (keyless preferred with OIDC).
* **SBOM:** `syft packages image:… -o cyclonedx-json` → attach & attest.
* **Scan:** `grype image:…` (fail on policy).
* **Provenance:** generate & attach (SLSA-style).
* **Docs:** Show `podman run` and `podman load` examples first.

---

## 14) Alternatives Revisited (brief)

* **Internal PyPI (code-only)**: still creates a centralized code distribution channel that can be confused with “safe defaults” for trust; weaker reproducibility; less native signing/attestation; rejected.
* **Binary releases** (static executables): possible but increases build complexity across platforms and loses many OCI benefits (layering, standard CI patterns).

---

## 15) Decision

**We will proceed with Option D (Hybrid):**

* **Primary distribution:** **OCI-compliant container image** published to **GHCR**, signed with **cosign**, with **SBOM** and **provenance** attached.
* **Adoption accelerator:** A **GitHub template repository** that mounts org-specific `config/` and `sources/` and runs the image in CI.
* **Explicit non-decision:** **Do not** publish BundleCraft to PyPI.

**Rationale:** This path offers the strongest **security posture**, **reproducibility**, **supply-chain integrity**, and **portability** while keeping configs/certificates under each organization’s control. It aligns with modern **OCI tooling** and avoids Docker-specific assumptions, satisfying both security and developer-experience needs.

---

## 16) Immediate Next Steps

1. Add `Dockerfile` (OCI) with non-root, read-only, slim base; wire up BuildKit.
2. Implement GH Actions workflow to build multi-arch, sign, generate SBOM, attach provenance, and publish to GHCR.
3. Draft the template repo (sample config, sample workflow, usage docs).
4. Update README/SECURITY/RELEASE with `podman`-first instructions and digest pinning examples.
5. Announce deprecation of any earlier “install locally” guidance in favor of the containerized engine.
