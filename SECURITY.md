# Security Policy

## Overview

**BundleCraft** is a framework and build automation toolkit for securely fetching, producing, and verifying PKI trust bundles.
It provides deterministic, auditable mechanisms to stage certificate inputs from trusted remote origins (or local files) and generate trust artifacts (PEM, P7B, JKS, P12, etc.).

BundleCraft **does not** distribute, embed, or endorse any certificate authority (CA) certificates.
All trust inputs are user-configured and staged via the Fetch layer or provided locally, with trust controls (CA pinning, TLS fingerprint pinning, optional `sha256` content pins) fully under operator control.

The security model of BundleCraft focuses on the *integrity, reproducibility, and transparency* of trust store builds - not the issuance, endorsement, or global distribution of CA material.

---

## Guiding Principles

1. **Code, not trust** - BundleCraft builds trust stores but never defines what is trusted.
2. **Local authority** - Users retain full control and accountability for certificate sources.
3. **Reproducibility** - Builds are deterministic and traceable to their input files and configurations, including fetch provenance (`provenance.fetch.json`).
4. **Separation of concerns** - Trust material and application code are isolated to prevent unintended trust propagation.
5. **Transparency** - All generated artifacts include manifests, checksums, and optional signatures for verification.

---

## Threat Model

### 1. Code Integrity
**Risk:** Unauthorized code modification (e.g., compromised repository or release pipeline).
**Controls:**
- GPG-signed Git tags and release artifacts.
- Immutable CI/CD release workflows.
- Checksums generated per build (`checksums.sha256`).
- Optional user-side signature verification with published keys.

### 2. Supply Chain Attacks
**Risk:** Malicious dependency or injected helper module.
**Controls:**
- Pinning of dependencies in `pyproject.toml`.
- No dynamic runtime dependency fetching.
- Security scanning of dependencies before each release.

### 3. Input Tampering
**Risk:** A compromised or unverified certificate source.
**Controls:**
- Declarative Fetch configuration for secure HTTPS/API/Vault sourcing (no implicit downloads).
- TLS CA verification, optional TLS leaf fingerprint pinning, and optional `sha256` content pinning.
- SHA256-based deduplication and canonicalization of all input PEMs.
- Build fails or warns on expired or malformed certificates.
- Manifest (`manifest.json`) includes full source list and hashes.
 - Staging-only model: fetched artifacts are ephemeral and cleaned per run; no persistent cache.

### 4. Build Environment Compromise
**Risk:** Build runs in an untrusted environment or manipulated workspace.
**Controls:**
- Supports fully offline build mode (no network calls) and explicit fetch step with provenance recording.
- Environment paths and temp directories explicitly defined.
- All writes are scoped under the build root (`dist/`).

### 5. Artifact Integrity
**Risk:** Tampering of produced trust bundles after build.
**Controls:**
- SHA256 checksum file (`checksums.sha256`).
- Optional GPG signing of bundles during CI/CD.
- End-users can re-run `bundlecraft verify` for local verification.

---

## Out of Scope

BundleCraft does **not**:
- Distribute or include CA certificates within the source code, packages, or releases.
- Act as a certificate repository, distribution channel, or root program.
- Perform or automate certificate issuance, revocation, or validation against CRLs/OCSP.
- Provide policy enforcement or approval workflows for certificate trust.
- Replace official OS or browser trust stores.

The project’s scope ends at **secure trust store generation** and **artifact verification**.

---

## Reporting a Vulnerability

We welcome responsible disclosure of any security issues found in BundleCraft.

**To report a vulnerability:**
1. Email the maintainers at: **security@bundlecraft.io** (or your designated address).
2. Include:
   - A clear description of the issue and potential impact.
   - Steps to reproduce (if applicable).
   - Any mitigation or workaround suggestions.

We aim to acknowledge all reports within **5 business days** and provide a fix or update within **30 days**, depending on severity.

---

## Responsible Disclosure Policy

- Do **not** publicly disclose vulnerabilities until a fix has been confirmed and published.
- Do **not** test against production CI/CD or shared repositories without authorization.
- Coordinated disclosure timelines are supported (e.g., via CERT/CC or GitHub Security Advisories).

---

## Secure Development Practices

Developers and contributors are expected to:

- Sign commits with verified GPG keys.
- Follow dependency scanning and linting rules defined in CI workflows.
- Avoid introducing runtime network calls or package downloads.
- Treat all external configuration and source data as untrusted input.
- Keep development environments patched and isolated.

---

## Cryptographic Practices

- Uses the Python `cryptography` library with FIPS-compliant primitives (when available).
- All timestamps use timezone-aware UTC.
- SHA256 is used for integrity verification; SHA1 and MD5 are strictly prohibited.
- No private keys are handled, stored, or transmitted by BundleCraft.

---

## Security Review and Audit

BundleCraft’s codebase is periodically reviewed for:
- Hardcoded credentials or secrets.
- Unsafe file handling or path traversal.
- Dependency vulnerabilities (via Dependabot or equivalent).
- Build reproducibility and integrity validation.

Formal third-party audits may be commissioned before major version releases.

---

## Contact

- **Primary Contact:** `security@bundlecraft.io`
- **PGP Key:** (to be published)
- **Project Website:** [https://github.com/bundlecraft](https://github.com/bundlecraft)

---

**Last Updated:** October 2025
