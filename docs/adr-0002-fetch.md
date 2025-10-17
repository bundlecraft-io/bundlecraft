# ADR-0002: Introduce a “Fetch/Sourcing” Layer as the First Stage of the BundleCraft Pipeline

**Status:** Draft / Under Review
**Date:** October 16 2025
**Owner:** BundleCraft maintainers
**Related:** ADR-000X (Containerized Distribution), SECURITY.md, CONFIG-SPEC.md

---

## 1️⃣ Context

BundleCraft currently operates as a **three-stage pipeline**:

| Stage       | Purpose                                         | Typical Input        | Output                       |
| ----------- | ----------------------------------------------- | -------------------- | ---------------------------- |
| **build**   | Aggregate certificates, craft bundle structures | `.pem` files (local) | Canonical PEM                |
| **verify**  | Validate contents and health of the bundle      | Built PEMs           | Verified manifest            |
| **convert** | Produce alternate formats for consumption       | Verified bundle      | `.p12`, `.jks`, `.p7b`, etc. |

This model assumes all certificates already exist in the repository under `sources/`.
While this keeps builds reproducible, it limits agility:

* Public roots (Mozilla, Microsoft, Apple) evolve frequently.
* Enterprise intermediates (Keyfactor, Vault) can be maintained elsewhere.
* Cloud PKIs (AWS PCA, Azure CA, Google CAS) publish endpoints with current roots.

Manually refreshing these into `sources/` risks drift and stale trust anchors.

---

## 2️⃣ Problem Statement

We need a secure, deterministic, and policy-controlled way to **fetch certificates automatically from trusted remote sources** during a build — without compromising reproducibility, auditability, or security posture.

---

## 3️⃣ Proposal

Add a **fourth, preceding layer: `fetch`**

```
fetch  →  build  →  verify  →  convert
```

### Functional Summary

| Capability                    | Description                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| **Declarative configuration** | Define remote sources (URL, API, Vault path, collection ID) within bundle or env YAML.        |
| **Trusted origins only**      | Each source must specify an approved scheme, expected fingerprint/CA pin, or checksum policy. |
| **Caching & provenance**      | Downloaded certs are cached locally (`cache/`) with metadata (source URL, SHA256, timestamp). |
| **Reproducibility**           | Build logs include exact hashes and timestamps so the same inputs can be re-fetched later.    |
| **Offline/air-gapped**        | Optional “offline mirror” mode uses previously cached artifacts.                              |

### Example bundle config excerpt

```yaml
fetch:
  - name: mozilla_roots
    type: url
    url: https://curl.se/ca/cacert.pem
    verify:
      sha256: 0a12b3...      # optional pin
  - name: keyfactor_collection
    type: api
    provider: keyfactor
    endpoint: https://pki.example.com/api/v1/collections/trusted
    token_ref: KEYFACTOR_TOKEN
  - name: vault_internal_roots
    type: vault
    path: secret/pki/trusted_roots
    verify_tls: true
```

---

## 4️⃣ Expected Behavior

1. **Pre-build phase:**
   The `fetch` module runs automatically (or via `--fetch` flag).
   It downloads, validates, and stores certs under `sources/fetched/` (or `.cache/fetch/<hash>/…`).

2. **Build phase:**
   The `build` module treats fetched files as normal inputs alongside any repository-resident certs.

3. **Verification phase:**
   Adds origin metadata to the manifest (URL, checksum, verified = true/false).

4. **Convert phase:**
   Unchanged.

---

## 5️⃣ Benefits

| Benefit                        | Description                                        |
| ------------------------------ | -------------------------------------------------- |
| **Reduced manual maintenance** | No more manual syncing of public root bundles.     |
| **Fresher trust sets**         | Always current with authoritative sources.         |
| **Extensible sourcing**        | Works for Keyfactor, Vault, S3, GitHub, REST APIs. |
| **Auditable provenance**       | Fetch metadata stored and signed in the manifest.  |
| **Hybrid trust composition**   | Combine internal + external roots in one bundle.   |

---

## 6️⃣ Risks & Mitigations

| Risk                              | Impact               | Mitigation                                                              |
| --------------------------------- | -------------------- | ----------------------------------------------------------------------- |
| Remote source unavailable         | Build failure        | Cache fallback, retry with back-off                                     |
| Man-in-the-middle or tampering    | Compromised trust    | TLS + CA pinning + expected hash verification                           |
| Drift / non-determinism           | Reproducibility loss | Record exact source URL + SHA256 + timestamp                            |
| Overreach (fetching too much)     | Performance / size   | Allow per-bundle limits and filters                                     |
| Secret leakage (Vault/API tokens) | Credential exposure  | Support secret references only (env vars or CI secrets), never hardcode |

---

## 7️⃣ Design Considerations

### a. Architecture

```
┌───────────────────────────┐
│ Fetch Sources (trusted)   │
│  - URLs / APIs / Vault    │
└──────────────┬────────────┘
               │
               ▼
┌───────────────────────────┐
│ BundleCraft Fetch Layer   │
│  - Downloads certs        │
│  - Validates integrity    │
│  - Caches & logs metadata │
└──────────────┬────────────┘
               ▼
(build → verify → convert)
```

### b. Implementation Sketch

* `bundlecraft/fetchers/` module with subclasses: `HttpFetcher`, `VaultFetcher`, `KeyfactorFetcher`, `FileFetcher`.
* Unified interface:

  ```python
  fetch(source_cfg: dict, dest_dir: Path) -> list[Path]
  ```
* Shared validation utilities (`sha256_file`, TLS CA pinning).
* Reuse existing logging and manifest system for provenance.

### c. Security Hooks

* Optional **GPG-signed manifest** of fetched sources.
* Optional **sigstore/cosign** attestation of fetch phase.

---

## 8️⃣ Non-Goals

* Not intended for untrusted or user-supplied URLs.
* Not meant to replace enterprise trust-policy review.
* Will not mutate or filter downloaded bundles beyond certificate parsing.

---

## 9️⃣ Alternatives Considered

| Approach                                  | Notes                                                     |
| ----------------------------------------- | --------------------------------------------------------- |
| Keep only local sources                   | Simpler but static; maintenance burden                    |
| Separate “pre-fetch” external script      | Decouples logic but fragments pipeline; inconsistent logs |
| In-band Git submodules for external certs | Versioned but clunky for dynamic sources                  |

---

## 🔟 Decision

**Decision:** Proceed with designing and implementing the `fetch` layer as an *optional but officially supported* first stage in the BundleCraft pipeline.

**Rationale:**

* Strongly aligns with BundleCraft’s purpose as a **trust automation framework**, not just a bundle packager.
* Maintains existing behavior (local sources remain supported) while enabling future integrations with enterprise PKI APIs.
* Introduces manageable complexity with clear security boundaries and provenance mechanisms.
* Adds significant practical value: automatic freshness of public and internal trust stores.

---

## 11️⃣ Next Steps

1. **Prototype** `bundlecraft/fetch.py` with a generic `url` fetcher (TLS verify + hash pinning).
2. Extend to `vault` and `keyfactor` fetchers using plugin architecture.
3. Define `fetch:` schema additions in `config/bundles/*.yaml`.
4. Update manifest spec to include:

   ```json
   "sources": [{"path": "...", "origin": "...", "sha256": "..."}]
   ```
5. Add CLI flag `--fetch` and automatic pre-build hook.
6. Extend verification tests to validate provenance metadata.
7. Update documentation and diagrams (README, CONFIG-SPEC.md, pipeline overview).

---

### ✅ Summary

**BundleCraft vNext = Fetch → Build → Verify → Convert**

By introducing a **trusted fetching layer**, BundleCraft evolves from a static trust-store builder into a **dynamic trust-source orchestrator** — maintaining the same immutability and audit guarantees while embracing real-time, policy-compliant sourcing of certificates.
