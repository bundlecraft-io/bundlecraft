# ADR-0004: Preparing BundleCraft for Post-Quantum Cryptography (PQC)

Status: Proposed
Date: 2025-10-18
Owner: Chris J. Pich
Related: ADR-0001 (Containers), ADR-0003 (Distribution), README, SECURITY.md

---

## Context

NIST is standardizing post-quantum signature algorithms (e.g., Dilithium, Falcon, SPHINCS+). For years, PKI will span classical-only, hybrid, and PQC-preferred deployments. Client support will vary, and not all trust store formats will handle PQC equally.

BundleCraft builds, verifies, and converts CA trust bundles from configuration-defined sources into reproducible, auditable artifacts. This ADR answers: what must BundleCraft do to help PKI administration before, during, and after PQC - within its scope as a trust bundle toolkit?

---

## Problem statement

The PQC transition requires BundleCraft to:

- Be algorithm-aware: detect and represent PQC and classical algorithms (and parameters) per certificate.
- Handle hybrid/cross-cert chains: parse and reason about chains bridging classical and PQC trust.
- Enforce policy: allow orgs to require/forbid/warn on algorithms and security levels.
- Clarify verification limits: common tools may not validate PQC without extensions; reporting must be clear.
- Address format considerations: runtimes and keystore formats vary in PQC support; admins need guidance when choosing formats.

Out of scope: issuance/renewal, automated AIA discovery, rotation/monitoring systems, or client runtime modifications.

---

## Decision (high level)

BundleCraft will become PQC-aware by enhancing existing operations:

1) Build: accept PQC-containing inputs; add policy-driven filtering and metadata enrichment.

2) Verify: detect PQC algorithms; attempt validation when possible; report capability gaps; enforce algorithm policies.

3) Convert: keep existing formats and document PQC-related considerations so admins can choose appropriate formats. Format choice matters for PQC readiness; adding new formats is covered by separate ADRs.

---

## Scope and non-goals

In scope:

- Algorithm metadata in manifests: key/signature algorithms, OIDs, sizes/params, hybrid/cross-cert indicators.
- Hybrid/cross-cert awareness: parse classical+PQC chains; surface relationships in manifests.
- Policy enforcement: config rules to require/forbid/warn; fail builds on violations.
- Verification enhancements: detect PQC signatures and validate when libraries support it; otherwise report limitations and remediation options.
- Format considerations: document which current formats are suitable or limited for PQC (no new formats in this ADR).

Not in scope:

- Acting as a CA/RA.
- Automated intermediate discovery or rotation/monitoring.
- Introducing new output formats.

---

## Detailed design

### 1) Enhanced metadata and manifests

Extend manifest schema to include:

- subject, issuer, serial, validity, fingerprint_sha256
- key_algorithm, key_size or params (curve or PQC parameter set)
- signature_algorithm, signature_algorithm_oid
- is_ca, is_self_issued
- is_hybrid (if applicable), cross_certified_with (references)

Maintain configurable OID-to-name mappings for classical and PQC algorithms.

Example (json):

```json
{
  "subject": "CN=Example Root CA",
  "issuer": "CN=Example Root CA",
  "serial": "0x1234",
  "not_before": "2025-01-01T00:00:00Z",
  "not_after": "2035-01-01T00:00:00Z",
  "fingerprint_sha256": "abc123...",
  "key_algorithm": "RSA",
  "key_size": 4096,
  "signature_algorithm": "SHA256withRSA",
  "signature_algorithm_oid": "1.2.840.113549.1.1.11",
  "is_ca": true,
  "is_hybrid": false
}
```

### 2) Policy-driven build

Config (env level):

```yaml
algorithm_policy:
  require_any: [RSA, ECDSA, Dilithium2]
  forbid: [RSA-1024, MD5withRSA]
  warn_on: [Dilithium3]
  allow_hybrid: true
  allow_cross_cert: true
  min_security_level: classical-128  # examples: classical-128, pq-128, pq-192
```

Build behavior:

- Evaluate each certificate against policy; filter or fail on violations.
- Emit warnings for warn_on.
- Record applied policy outcomes in the manifest.

### 3) Verification enhancements

- Detect PQC algorithms/parameters and include in output.
- Attempt validation via available libraries/providers when configured (e.g., OpenSSL with oqsprovider, pyca/cryptography extensions, Java providers). When unavailable, report “detected but not validated” with guidance.
- Enforce algorithm_policy during verify and fail on violations.

Example output:

```text
✓ RSA-4096 signature validated (OpenSSL)
✓ ECDSA-P256 signature validated (OpenSSL)
! Dilithium2 signature detected but not validated (current toolchain lacks PQC support)
  → Use a PQC-capable toolchain or select a format compatible with your runtime.
```

### 4) Format considerations (informational)

Document PQC-relevant behavior of existing supported formats so admins can pick the right target for their platforms. Some formats and runtimes are classical-only today; others may gain PQC support over time. This ADR does not introduce new formats; it states that format selection is a key part of PQC readiness and that guidance will be included in manifests and docs.

---

## Rollout (phased)

Phase 0: Foundations

- Add algorithm fields to manifest; implement OID/parameter detection.
- Basic PQC lint: detect PQC signatures and report (no validation required).
- Document format considerations and current limitations at a high level.

Phase 1: Policy enforcement

- Add algorithm_policy schema; enforce during build and verify.
- Improve verification messaging and manifest reporting.

Phase 2: Optional validation integrations

- Provide optional hooks/instructions to enable PQC-capable validation with supported libraries/providers.
- Expand guidance as ecosystem support matures.

Exit criteria for ADR acceptance: Phase 1 complete (policy enforcement) and documentation updated with format considerations and migration guidance.

---

## Risks and mitigations

- Evolving standards: keep mappings configurable; document versions and allow overrides.
- Library availability: make PQC validation optional; keep classical-only path slim.
- Policy complexity: provide preset policies (classical-only, hybrid-ready, pqc-preferred) and examples.
- Misinterpretation of verify: clearly distinguish “not validated” from “invalid”.

---

## How this helps PKI admins

- Algorithm visibility and inventory for every bundle.
- Policy compliance at build/verify time, not production time.
- Clear guidance when runtime/tooling can’t validate PQC yet.
- Format selection awareness to align bundles with platform capabilities.
- Reproducible artifacts and manifests for audits and change control.
