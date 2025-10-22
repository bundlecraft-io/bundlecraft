# ⚔️ Guarding Against PKI Anti-Patterns

## Overview

**BundleCraft** is designed from the ground up to avoid the common anti-patterns that have historically weakened PKI implementations and trust-store management.

It is **not** a live updater, background agent, or dynamic trust injector!

Instead, it is a **deterministic build system** that produces auditable, reproducible, and policy-driven CA bundles as part of a provisioning or CI/CD workflow.

---

## ✅ How BundleCraft Prevents Anti-Patterns

| Area | Typical Anti-Pattern | BundleCraft’s Approach |
|------|----------------------|------------------------|
| **Trust Source Provenance** | Fetching or bundling CAs from arbitrary web sources | All inputs must be explicitly declared in configuration, with provenance metadata such as fingerprints, hashes, or verified URLs. |
| **Runtime Trust Manipulation** | Modifying system trust stores in place or during runtime | BundleCraft only builds bundles; it does not update or inject trust anchors live. Integration occurs through provisioning pipelines or controlled image builds. |
| **Hidden or Implicit Roots** | Including vendor roots or OS defaults silently | All trusted certificates must be explicitly defined. There are no hidden or inherited anchors. |
| **Code–Data Coupling** | Shipping CA trust with application code | Tooling and trust data are completely decoupled. The project strictly avoids embedding certificates within source code or release binaries. |
| **Legacy Format Reliance** | Using obsolete or insecure formats (e.g., JKS) by default | Legacy formats are supported only when required and are clearly labeled as such; modern, standards-based formats are the defaults. |
| **Non-Deterministic Builds** | Build outputs varying due to timestamps or metadata | BundleCraft normalizes and produces deterministic tarballs for identical inputs, ensuring reproducibility and auditability. |
| **Uncontrolled Trust Expansion** | Including intermediates or subordinates “just to make it work” | Default philosophy is **root-only trust**. Intermediates are considered out-of-scope for trust anchors and are handled separately when required by rare legacy use cases. |

---

## ⚠️ Anti-Patterns Users Could Introduce

While BundleCraft itself enforces good practice, users could still misuse it in ways that recreate bad patterns:

- **Running BundleCraft as a recurring “trust updater” job**
  Turns it into a dynamic trust mutation agent - violating audit and reproducibility guarantees.

- **Pulling CA sources dynamically without verifying provenance**
  Re-introduces the risk of rogue or malicious trust anchors.

- **Mixing internal and public CAs in one trust store**
  Collapses security boundaries between environments.

BundleCraft assumes a **deliberate and controlled build process**, not an “auto-sync” trust distribution model.

---

## 🔒 Revocation Design Philosophy

BundleCraft intentionally **does not implement certificate revocation checking**.
This is a conscious design choice, not an omission:

- **Root CAs cannot be revoked** - they are self-signed anchors.
- **Subordinate CAs can be revoked**, but **placing them in a trust store is itself an anti-pattern**.
  The moment an intermediate certificate appears as a trust anchor, it bypasses the revocation model PKI was built upon.

Implementing revocation awareness at the trust-store layer would therefore **encode support for a misuse pattern**, not a best practice.
Revocation should be enforced by **end-entity certificate validation systems** (browsers, libraries, mTLS frameworks), not by a CA bundle build tool.

BundleCraft's role is to ensure that the trust anchors themselves are correct, verified, and deterministic - not to police revocation of certificates that should never have been trusted in the first place.

---

## 📃 Configuration Checklist: Avoiding Common Misuse Patterns

Follow these quick checks to ensure your BundleCraft configuration remains aligned with PKI best practices:

### ✅ Trust Definition

- [ ] Remote fetch sources include SHA-256 verification (`verify.sha256`) for static downloads or TLS pinning (`verify.tls_fingerprint_sha256`) for dynamic endpoints.
- [ ] Filter `root_certs_only: true` is enabled in defaults or craft configs to exclude subordinate/intermediate CAs from trust anchors.
- [ ] Filter `ca_certs_only: true` ensures only certificates with BasicConstraints CA:TRUE are included.
- [ ] Internal and external roots are maintained in **separate bundle configs** (e.g., `internal.yaml`, `mozilla.yaml`).

### 🧱 Build Integrity

- [ ] Builds are executed in controlled CI/CD or provisioning workflows - **not as periodic background jobs or cron tasks**.
- [ ] Package option (`package: true`) is enabled in craft configs when deterministic tar archives are required.
- [ ] Generated `checksums.sha256` files are validated and versioned alongside bundles.
- [ ] Build artifacts are committed to version control or signed in CI for audit trails.

### 🔐 Security and Policy

- [ ] Legacy formats (JKS, etc.) appear in `output_formats` only when required by consuming systems - never as universal defaults.
- [ ] PEM subject comments (`pem.include_subject_comments: true`) are enabled for human readability and audit (on by default).
- [ ] Verification policies (`verify.fail_on_expired: true`, `verify.warn_days_before_expiry: 30`) are configured to catch expiring/expired certificates early.
- [ ] Sensitive credentials (API tokens, Vault tokens, keystore passwords) use environment variable references (`token_ref`, `TRUST_JKS_PASSWORD`) - **never inline values**.
- [ ] Filters ensure only valid, non-expired CA certificates enter bundles (`not_expired_only: true`, `unique_by_fingerprint: true` in defaults).

### 🧭 Governance

- [ ] Every bundle config change (new sources, modified fetch URLs) is peer-reviewed via pull request.
- [ ] CI workflows validate fetch source integrity (SHA-256 matches, TLS pins) before accepting downloaded content.
- [ ] Build diffs are reviewed between releases to ensure no unapproved trust anchors or expired certificates are introduced.
- [ ] Craft configs specify explicit target compositions (`targets.<name>.includes`) to prevent unintended bundle merging.

These checks collectively help maintain **deterministic trust**, **configuration transparency**, and **policy consistency** - the core principles of BundleCraft's security model.
