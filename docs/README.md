# BundleCraft Documentation

This folder contains the technical and conceptual documentation for the **bundlecraft** project.

Each document describes a specific layer of the system - from goals and design philosophy to implementation and maintenance.

---

## 📚 Index

1. [Overview](00-overview.md)
2. [Design Goals](01-design-goals.md)
3. [Architecture](02-architecture.md)
4. [Directory Structure](03-directory-structure.md)
5. [Configuration Design](04-config-design.md)
6. [Scripts & Components](05-scripts-and-components.md)
7. [ADR-0002: Fetch Layer](adr-0002-fetch.md)
8. [Test CA Certificate Generator](test-ca-generator.md)
9. [Troubleshooting](troubleshooting.md)
10. [Configuration Spec](CONFIG-SPEC.md)
11. [API Fetcher and Local Mock](fetcher-apis.md)
12. [Atomic Builds](atomic-builds.md) - **NEW**: Reliable, all-or-nothing build operations

---

> **Note:**
> All documents are version-controlled and treated as part of the source of truth.
> Any design or behavioral change **must** be reflected here.

Quick config notes:

- Config files support optional headers `apiVersion: bundlecraft.io/v1alpha1` and `kind: <EnvConfig|SourceConfig|DefaultsConfig>`. These are validated if present and recommended for stricter config environments.
- `metadata.labels` is supported (in addition to `metadata.tags`) for attaching machine-readable key/value pairs to configs.
- Environment configs compose sources by name; they don’t reference inner repo/fetch names from source configs to preserve separation of concerns.
