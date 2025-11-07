# Security Policy

## Overview

**BundleCraft** is a framework and build automation toolkit for securely fetching, producing, and verifying PKI trust bundles.
It provides deterministic, auditable mechanisms to stage certificate inputs from trusted remote origins (or local files) and generate trust artifacts (PEM, P7B, JKS, P12, etc.).

BundleCraft does not distribute, embed, or endorse any certificate authority (CA) certificates.
All trust inputs are user-configured and staged via the Fetch layer or provided locally, with trust controls (CA pinning, TLS fingerprint pinning, optional `sha256` content pins) fully under operator control.

The security model of BundleCraft focuses on the *integrity, reproducibility, and transparency* of trust store builds - not the issuance, endorsement, or global distribution of CA material.

______________________________________________________________________

## Guiding Principles

1. **Code, not trust** - BundleCraft builds trust stores but never defines what is trusted.
1. **Local authority** - Users retain full control and accountability for certificate sources.
1. **Reproducibility** - Builds are deterministic and traceable to their input files and configurations, including fetch provenance (`provenance.fetch.json`).
1. **Separation of concerns** - Trust material and application code are isolated to prevent unintended trust propagation.
1. **Transparency** - All generated artifacts include manifests, checksums, and optional signatures for verification.

______________________________________________________________________

## Threat Model

### 1. Code Integrity

**Risk:** Unauthorized code modification (e.g., compromised repository or release pipeline).
**Controls:**

- GPG-signed release artifacts (optional but available).
- GPG-signed Git tags recommended for version releases.
- Immutable CI/CD release workflows.
- Checksums generated per build (`checksums.sha256`).
- Optional user-side signature verification with published keys.

### 2. Supply Chain Attacks

**Risk:** Malicious dependency or injected helper module.
**Controls:**

- Minimum version constraints for dependencies in `pyproject.toml`; lock files recommended for production deployments.
- **Production releases use exact dependency versions** from `requirements-lock.txt` to prevent unexpected updates. See [`docs/DEPENDENCY-LOCK.md`](docs/DEPENDENCY-LOCK.md) for lock file management.
- No dynamic runtime dependency fetching.
- Dependency vulnerability scanning via automated tools (recommended: Dependabot, pip-audit).

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

______________________________________________________________________

## Out of Scope

BundleCraft does **not**:

- Distribute or include CA certificates within the source code, packages, or releases.
- Act as a certificate repository, distribution channel, or root program.
- Perform or automate certificate issuance, revocation, or validation against CRLs/OCSP.
- Provide policy enforcement or approval workflows for certificate trust.
- Replace official OS or browser trust stores.

The project’s scope ends at **secure trust store generation** and **artifact verification**.

______________________________________________________________________

## Reporting a Vulnerability

We welcome responsible disclosure of any security issues found in BundleCraft.

**To report a vulnerability:**

1. Email the maintainers at: **<security@bundlecraft.io>**
1. Include:
   - A clear description of the issue and potential impact.
   - Steps to reproduce (if applicable).
   - Any mitigation or workaround suggestions.

______________________________________________________________________

## Responsible Disclosure Policy

- Do **not** publicly disclose vulnerabilities until a fix has been confirmed and published.
- Do **not** test against production CI/CD or shared repositories without authorization.
- Coordinated disclosure timelines are supported (e.g., via CERT/CC or GitHub Security Advisories).

______________________________________________________________________

## Secure Development Practices

Developers and contributors are expected to:

- Sign commits with verified GPG keys (encouraged).
- Follow dependency scanning and linting rules defined in CI workflows.
- Avoid introducing runtime network calls or package downloads outside the explicit Fetch layer.
- Treat all external configuration and source data as untrusted input.
- Keep development environments patched and isolated.

______________________________________________________________________

## Cryptographic Practices

- Uses the Python `cryptography` library with FIPS-compliant primitives (when available).
- All timestamps use timezone-aware UTC.
- SHA256 is used for integrity verification and content addressing.
- SHA1 is used only for JKS alias generation and legacy certificate fingerprint display (not for security verification).
- MD5 is prohibited.
- No private keys are handled, stored, or transmitted by BundleCraft.

______________________________________________________________________

## Security Review and Audit

BundleCraft’s codebase is periodically reviewed for:

- Hardcoded credentials or secrets.
- Unsafe file handling or path traversal.
- Dependency vulnerabilities (via Dependabot or equivalent).
- Build reproducibility and integrity validation.

Formal third-party audits may be commissioned before major version releases.

______________________________________________________________________

## Contact

- **Primary Contact:** <security@bundlecraft.io>
- **PGP Key:** [`docs/public-gpg-key.asc`](docs/public-gpg-key.asc)
- **Project Website:** [https://github.com/bundlecraft](https://github.com/bundlecraft)

### Verifying Signed Releases

```bash
# Import the GPG key
curl -sL https://raw.githubusercontent.com/bundlecraft-io/bundlecraft/main/docs/public-gpg-key.asc | gpg --import

# Verify a signed checksum file
gpg --verify dist/checksums.sha256.asc dist/checksums.sha256
```

For key fingerprint verification and additional keyserver locations, see [`docs/public-gpg-key.asc`](docs/public-gpg-key.asc).

## Thanks

To the security, devops, and open source communities. 🙏🏽

______________________________________________________________________

**Last Updated:** October 2025
