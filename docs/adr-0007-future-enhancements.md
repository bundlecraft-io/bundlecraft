# ADR-0007: Future Distribution Enhancements (Post-MVP)

**Status:** Proposed
**Date:** October 21, 2025
**Owner:** Chris J. Pich
**Related:** ADR-0006 (MVP), SECURITY.md

______________________________________________________________________

## 1) Context

ADR-0006 established a pragmatic MVP distribution strategy (OCI + PyPI + Template) suitable for initial release and solo-developer maintenance. This ADR documents **future enhancements** to be considered once the MVP is stable and user feedback is gathered.

______________________________________________________________________

## 2) Deferred Features

The following features were intentionally excluded from MVP to maintain simplicity and focus:

### 2.1 PEX/Zipapp Self-Contained Artifacts

**What:** Single-file Python executable bundling all dependencies

**Why deferred:**

- Niche use case (air-gapped/offline environments)
- Adds build complexity (PEX tooling, dependency resolution)
- Maintenance burden for another distribution channel
- OCI containers can be saved/loaded for offline use (`docker save`)

**Trigger for implementation:**

- Multiple user requests for air-gapped deployment
- Evidence that OCI offline workflows are insufficient

### 2.2 GitHub Action Wrapper

**What:** Custom GitHub Action that wraps the OCI image

**Why deferred:**

- Users can already call the OCI image directly in workflows
- Adds another repository to maintain (bundlecraft/action)
- Wrapper provides minimal value over direct container invocation
- Action marketplace has discovery challenges

**Trigger for implementation:**

- Significant friction in user workflows calling OCI directly
- Community requests for simplified GitHub-native integration

### 2.3 Multi-Architecture Builds

**What:** Build both `linux/amd64` and `linux/arm64` images

**Why deferred:**

- Most CI/CD runs on amd64 (primary use case)
- Multi-arch builds add significant CI time and complexity
- Cross-compilation can introduce subtle bugs
- arm64 users can build locally if needed

**Trigger for implementation:**

- Measurable arm64 usage (GitHub Runners, AWS Graviton, Apple Silicon servers)
- User requests with specific arm64 requirements

### 2.4 Advanced SBOM and SLSA Provenance

**What:** Detailed SBOMs (CycloneDX/SPDX), SLSA Level 3+ provenance

**Why deferred:**

- GitHub's native attestations provide basic provenance for MVP
- Full SBOM tooling (syft, etc.) adds CI complexity
- SLSA Level 3 requires significant infrastructure
- Diminishing returns for current user base

**Trigger for implementation:**

- Enterprise compliance requirements
- Supply chain transparency regulations
- User requests for detailed dependency tracking

### 2.5 Hash-Locked Dependency Files

**What:** `requirements.lock` with cryptographic hashes for all dependencies

**Why deferred:**

- `pyproject.toml` constraints provide sufficient reproducibility for MVP
- Hash locking adds regeneration overhead (on every dep update)
- Pip-tools or Poetry adds another tool dependency
- Can use Dependabot for dependency tracking initially

**Trigger for implementation:**

- Evidence of supply chain attacks on dependencies
- Reproducibility issues in production builds
- User demands for deterministic builds

### 2.6 Weekly CVE Scanning and Automated Rebuilds

**What:** Scheduled workflow to rebuild images and scan for vulnerabilities

**Why deferred:**

- Manual rebuilds on demand are sufficient for MVP
- Automated scanning generates noise without response process
- Requires dependency update strategy and testing
- Better handled reactively with Dependabot alerts initially

**Trigger for implementation:**

- Active user base requiring security SLAs
- Historical CVE impact on BundleCraft dependencies
- Resources available for security response process

### 2.7 Digest Pinning and Cross-Channel Verification

**What:** All channels reference canonical OCI digest; automated verification

**Why deferred:**

- Single-commit releases provide traceability for MVP
- Complex digest propagation across channels
- Verification tooling adds user friction
- GitHub's built-in signing provides sufficient trust

**Trigger for implementation:**

- Evidence of supply chain attacks
- Compliance requirements for attestation
- Multi-repository complexity increases drift risk

______________________________________________________________________

## 3) Evaluation Criteria

Before implementing any deferred feature, evaluate:

1. **User demand:** Are users actively requesting this?
1. **Maintenance cost:** Can it be maintained by solo dev?
1. **Security benefit:** Does it meaningfully improve security posture?
1. **Complexity ratio:** Is the value worth the added complexity?
1. **Alternative solutions:** Can existing features solve the problem?

______________________________________________________________________

## 4) Decision

These features are **explicitly deferred** to post-MVP. They should be revisited when:

- MVP is stable and adopted
- User feedback identifies clear gaps
- Maintenance capacity increases
- Security landscape changes require them

This ADR serves as a backlog and reminder that **simplicity is a feature** for a solo-developer project.

______________________________________________________________________

## 5) Next Steps (When Ready)

For each feature:

1. Gather user feedback and usage data
1. Prototype in a feature branch
1. Assess maintenance burden
1. Document implementation in dedicated ADR if complex
1. Implement incrementally with rollback plan
