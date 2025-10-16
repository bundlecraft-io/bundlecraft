# 02-architecture.md

# Architecture Overview

The system follows a **three-layer model**, defining how trust stores are sourced, built into ready-to-consume packages, and finally distributed to their destinations.

---

## Layer Diagram

```text
+---------------------------------------------+
| Layer 3: Trust Distribution (publishing)    |
|  -> Publishes built trust bundles           |
|  -> Pushes to file shares, Git, S3, etc.    |
|  -> Optional packaging (tar, container)     |
+---------------------------------------------+
| Layer 2: Trust Build (artifact production)  |
|  -> Reads config and sources                |
|  -> Verifies, merges, and converts formats  |
|  -> Outputs complete bundles (PEM, JKS, …)  |
+---------------------------------------------+
| Layer 1: Trust Source (inputs)              |
|  -> Raw certs, metadata, and source configs |
+---------------------------------------------+
```

## Layer Roles
### Layer 1 — Trust Source


* Serves as the source of truth for all trust anchors.
* Stores raw CA certificates and metadata files.
* Maintained under version control.
* Structured by logical trust domain (internal, external, OS trust, etc.).
* Can include trusted external roots or system trust anchors

### Layer 2 — Trust Build

* Combines environment and bundle configurations.
* Loads and validates all referenced certificates.
* Merges certificates into canonical PEM form.
* Converts to multiple formats (PEM, JKS, PKCS#7, DER, etc.).
* Generates manifests, checksums, and optional tar packages.
* Produces fully ready-to-consume artifacts in `/dist/{env}/{bundle}/`.

### Layer 3 — Trust Distribution

* Publishes built artifacts to target systems or repositories.
* Supports multiple distribution mechanisms
* Performs no transformation—publishing only.

## Data Flow Summary

This modular approach ensures that configuration, build logic, and publication are cleanly separated for clarity and maintainability.

## Data Flow Summary

```text
┌────────────────────────────────┐
│        sources/ directory       │
│ (raw certificates and metadata) │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│     builder.py       │
│  - Reads YAML/JSON configs     │
│  - Collects & validates certs  │
│  - Merges and converts formats │
│  - Writes manifests & checksums│
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│     dist/{env}/{bundle}/      │
│   ├── ca-trust.pem             │
│   ├── ca-trust.jks             │
│   ├── ca-trust.p7b             │
│   ├── manifest.json            │
│   └── package.tar.gz (opt)     │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│     Distribution mechanisms    │
│   (Artifactory, Git, S3, etc.) │
└────────────────────────────────┘
```

This design ensures that build artifacts are self-contained and immutable, making them safe for reuse, packaging, or publication in any distribution channel.