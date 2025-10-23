# BundleCraft Docs

This folder contains technical and conceptual documentation for the **BundleCraft** project.

Each document describes a specific layer of the system - from design philosophy and architecture to implementation details and operational guidance.

______________________________________________________________________

## 📚 Core Documentation

### Configuration & Usage

- **[Configuration Specification](CONFIG-SPEC.md)** - Complete schema and usage guide for source configs, environment configs, and defaults
- **[JSON Output Schemas](JSON-OUTPUT.md)** - Machine-readable output formats for all CLI commands (--json flag)
- **[Exit Codes](exit-codes.md)** - Standardized exit codes for CI/CD integration and error handling
- **[Signing and SBOM](SIGNING-AND-SBOM.md)** - GPG signing of releases and automatic CycloneDX SBOM generation

### Design & Philosophy

- **[Anti-Patterns](ANTI-PATTERNS.md)** - How BundleCraft prevents common PKI and trust-store management mistakes
- **[Atomic Builds](atomic-builds.md)** - Reliable, all-or-nothing build operations with rollback on failure

### Architecture Decision Records (ADRs)

- **[ADR-0001: Container Distribution](adr-0001-containers.md)** - Deferred: OCI-compliant container distribution strategy
- **[ADR-0002: Fetch Layer](adr-0002-fetch.md)** - Design and implementation of the certificate fetch stage
- **[ADR-0003: Multi-Channel Distribution](adr-0003-distribution.md)** - Deferred: OCI-first with optional PyPI and GitHub Action
- **[ADR-0004: Post-Quantum Cryptography](adr-0004-pqc.md)** - Proposed: Preparing for PQC algorithms and hybrid chains
- **[ADR-0005: Output Formats Expansion](adr-0005-outputformats.md)** - Proposed: BCFKS and additional keystore format support
- **[ADR-0006: Core Release Strategy](adr-0006-corerelease.md)** - Proposed: MVP distribution via OCI + PyPI + Template (supersedes ADR-0001/0003)
- **[ADR-0007: Future Enhancements](adr-0007-future-enhancements.md)** - Proposed: Post-MVP features (PEX/zipapp, GitHub Action, etc.)

### Development & Testing

- **[CI/CD Workflows](CI-CD.md)** - GitHub Actions workflows for testing, building, and releasing trust bundles
- **[Test CA Generator](test-ca-generator.md)** - Tool for generating test certificates for development and CI
- **[Troubleshooting](troubleshooting.md)** - Common issues, debugging tips, and solutions

### Other

- **[public-gpg-key.asc](public-gpg-key.asc)** - Public GPG key for verifying signed releases

______________________________________________________________________
