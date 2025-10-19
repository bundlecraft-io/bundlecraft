# ADR-005: Expand BundleCraft Output Formats (with BCFKS as a priority)

- **Status:** Proposed
- **Date:** October 18, 2025
- **Owners:** BundleCraft maintainers

---

## Context

BundleCraft builds and ships trust stores for multi-env PKI. We currently output a handful of formats (PEM bundle, PKCS#7, PKCS#12, JKS). Users want broader compatibility across platforms, JVMs, browsers, and OS tooling—without sacrificing repeatability, portability, and security.

Initial scope: prioritize file-based trust stores (single-file artifacts). Directory-based trust stores (e.g., hash directories) and platform stores (e.g., NSS, Keychain) are valuable but will follow later phases.

Constraint (for “Now” scope): Add formats that (a) produce a single artifact (not a directory) and (b) can be reliably created directly from Python libraries. Formats requiring external CLIs or Java providers move to “Phase 2+,” unless the value is substantial and cannot be met via Python-only (e.g., BCFKS via keytool/BC provider).

---

## Decision

1. **Phase 1 (Now):** Expand/standardize **single-file** outputs that can be produced **entirely in Python**. Tighten our implementations around `cryptography` and friends to avoid shell/Java dependencies where feasible.
2. **Phase 2 (Near-term):** Add **BCFKS** (top priority) and other high-value keystores that require **non-Python providers** (e.g., Bouncy Castle / keytool). Provide these via a clean, optional “adapter” layer so core Python-only users remain dependency-light.
3. **Phase 3 (Later):** Consider **directory-style trust stores** (e.g., OpenSSL hash layout) and platform stores (NSS/Keychain), plus PQC/hybrid artifacts once libraries stabilize.

This staged approach keeps core pipelines deterministic and portable while opening paths to enterprise keystore coverage.

---

## Why this matters

- **Enterprise coverage:** Java shops (Keyfactor, EJBCA, Venafi) increasingly prefer **BCFKS** for FIPS-friendly keystores.
- **Ops ergonomics:** Ops teams often need multiple shapes of the same trust material to feed JVMs, proxies, agents, and SDKs.
- **Security:** Modern formats (e.g., BCFKS, hardened PKCS#7) reduce legacy pitfalls and ease future PQC transitions.

---

## Supported / Deferred Formats (Deep Table)

> Legend: Decision = Now / Phase 2 / Phase 3 / Not planned. “Python-native?” reflects whether we can build it without invoking Java/CLIs.

| Category              | Format                                  | Typical Ext(s)        | Contents                                | Single Artifact? | Python-native? | Primary Libraries / Tooling                                | Decision               | Purpose & BundleCraft Alignment                                                                                                        |
| --------------------- | --------------------------------------- | --------------------- | --------------------------------------- | ---------------: | -------------: | ---------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **PEM Family**        | PEM bundle (CA bundle)                  | `.pem`, `.crt`, `.ca-bundle` | Multiple X.509 certs concatenated       |                ✅ |              ✅ | `cryptography` (read/write X.509), simple concat           | **Now**                | Universal trust bundle for Unix-like stacks, curl, OpenSSL. Core to BundleCraft and easy to verify.                                   |
|                       | PEM (single cert)                       | `.pem`, `.cer`        | One X.509 cert                          |                ✅ |              ✅ | `cryptography`                                             | **Now**                | Per-cert distribution/debug; useful for systems that ingest individual anchors.                                                        |
|                       | DER (single cert, binary)               | `.der`, `.cer`        | One X.509 cert (binary)                 |                ✅ |              ✅ | `cryptography`                                             | **Input only**         | Accepted as input. Not offered as output (single-cert limitation; use P7B for multi-cert binary).                                       |
| **PKCS / CMS**        | PKCS#7 (degenerate “chain only”)        | `.p7b`, `.p7c`        | Cert chain; no private keys             |                ✅ |              ✅ | `cryptography` PKCS7 serialization (degenerate SignedData) | **Now**                | Widely accepted by Windows/Java tooling for trust chains.                                                                              |
|                       | CMS (RFC 5652)                          | `.cms`                | General CMS container                   |                ✅ |             ⚠️ | `cryptography` (CMS/PKCS7 overlap)                         | **Phase 2**            | Broader CMS support beyond p7b; add once PKCS#7 path is fully stable and interop-tested.                                               |
|                       | PKCS#12 (also Java storetype=PKCS12)    | `.p12`, `.pfx`        | Certs + (optionally) private key        |                ✅ |              ✅ | `cryptography` `serialize_key_and_certificates`            | **Now**                | Common cross-platform keystore. Can serve as a Java TrustStore with `-storetype PKCS12`. Trust-only variant when feasible.            |
| **Java Keystores**    | BCFKS (Bouncy Castle FIPS KeyStore)     | `.bcfks`              | Keystore (certs/keys)                   |                ✅ |              ❌ | Java `keytool` + BC(FIPS/non-FIPS) providers               | **Phase 2 (Priority)** | Enterprise priority; FIPS-friendly. Implement via conversion utilities in `convert_utils`; record provider versions in manifest.        |
|                       | JKS                                     | `.jks`                | Keystore (legacy)                       |                ✅ |              ❌ | Java `keytool`                                             | **Supported (Current)**| Legacy but still prevalent. Already implemented in conversion utilities.                                                               |
|                       | JCEKS                                   | `.jceks`              | Keystore incl. secret keys              |                ✅ |              ❌ | Java `keytool`                                             | **Phase 2**            | Niche legacy. Implement in conversion utilities if demanded.                                                                            |
|                       | BKS (non-FIPS BC keystore)              | `.bks`                | Keystore                                |                ✅ |              ❌ | Java `keytool` + BC                                        | **Phase 2**            | Older BC format; implement in conversion utilities based on demand.                                                                    |
| **Microsoft**         | SST (Serialized Store via PKCS#7)       | `.sst`                | Serialized cert store (Windows)         |                ✅ |             ⚠️ | Represent as `.p7b` (alias)                                | **Not planned**        | Too niche and Windows-dependent for building; users can rename `.p7b` to `.sst` if needed.                                             |
|                       | SPC                                     | `.spc`                | Authenticode cert container             |                ✅ |             ⚠️ | SignTool/Win APIs                                          | **Not planned**        | Code-signing specific; not a general trust store.                                                                                      |
|                       | P7R                                     | `.p7r`                | “Cert response” file                    |                ✅ |             ⚠️ | Windows tooling                                            | **Not planned**        | Rare/limited value for trust distribution.                                                                                             |
| **Mozilla / NSS**     | cert9.db (SQLite)                       | `cert9.db`            | NSS trust DB                            |                ✅ |              ❌ | `certutil` (NSS)                                           | **Phase 3**            | High value for browsers; requires platform tools/stateful DB. Consider via containerized adapter and export guidance.                  |
| **Apple**             | Keychain                                | `.keychain(-db)`      | Apple keychain                          |                ✅ |              ❌ | `security` tool / APIs                                     | **Not planned**        | Platform-proprietary; document import guidance rather than produce artifacts.                                                           |
| **OpenSSL / Unix**    | Hash directory (c_rehash style)         | `<hash>.0` files      | Dir of per-cert hashed symlinks         |                ❌ |              ✅ | `openssl` hashing or `cryptography` + hash logic           | **Phase 3**            | Directory-shaped; if provided, ship as an archive (e.g., `ca-hashdir.tar.gz`) to preserve single-artifact UX.                          |
| **OpenSSL**           | Trusted PEM (aux data)                  | `.pem` (with trust)   | PEM with OpenSSL auxiliary trust        |                ✅ |             ⚠️ | `openssl` CLI (best-effort), limited Python support        | **Not planned**        | Non-portable trust attributes; low demand; avoid format-specific semantics in artifacts.                                               |
| **Keys/Components**   | PKCS#8 (private key)                    | `.p8`, `.pk8`, `.key` | Private key container                   |                ✅ |              ✅ | `cryptography`                                             | **Phase 2**            | Not a trust store; support where key-bearing pipelines are needed; not a trust-only output.                                            |
| **PQC/Emerging**      | X.509 Hybrid / Composite                | (PEM/DER)             | Classical+PQC hybrids                   |                ✅ |             ⚠️ | Early BC/OpenSSL forks/libs                                | **Phase 3**            | Track PQC rollout; add after verification/interop stabilize; coordinate with ADR-0004.                                                 |
|                       | COSE/CBOR certs (IoT)                   | `.cose`, `.cbor`      | COSE-x509 or COSE certs                 |                ✅ |             ⚠️ | `cbor2` + COSE libs                                        | **Phase 3**            | IoT-focused; defer until libraries and profiles stabilize.                                                                              |

**Notes on PKCS#12 (trust-only):** Although PKCS#12 is commonly used for key+certs, we’ll support **certificate-bag-only** outputs when a private key is not present. We’ll document client expectations (some stacks expect at least one key bag).

---

## Implementation Plan

### Phase 1 (Now) — Python-native and JKS support

- **PEM (bundle and single):**

  - Write bundles by concatenating `cryptography.x509.Certificate.public_bytes(PEM)`.
  - Validate parse-ability and non-duplication; preserve order (root last).
- **PKCS#7 (`.p7b`):**

  - Use `cryptography` PKCS7 degenerate SignedData (no signer, certs only).
  - Verify that Windows/Java consumers accept produced objects (interop tests).
- **PKCS#12 (`.p12`):**

  - For trust-only: build cert-bag-only where supported; otherwise warn and fall back to `.p7b`.
  - For key-bearing artifacts: `serialize_key_and_certificates()` with friendlyName and MAC integrity options.
- **JKS (`.jks`):**

  - Already supported via `bundlecraft.helpers.convert_utils`; uses Java `keytool` with deterministic flags.
- **Verification:**

  - Add format-specific verifiers (open/parse, count, subject/AKI/SKI chain linkage, MAC presence for P12).
- **Input handling:**

  - Accept DER-encoded certificates as inputs; convert to internal representation for processing.

### Phase 2 — Extended Java keystores and optional formats

- **Extend `bundlecraft.helpers.convert_utils`** for additional Java keystores:

  - First target: **BCFKS** (priority) using `keytool` + BC provider.
  - Then: **JCEKS** and **BKS** if demanded.
  - Enforce deterministic flags (cipher, KDF, iteration counts, keystore type).
  - Record tool versions, provider versions, and command parameters in manifest for auditability.
- **Dependencies:**

  - Java `keytool` (required for Java keystores).
  - Bouncy Castle provider jars (`bcfips` or `bcprov`) for BCFKS/BKS.
  - Validate availability before attempting conversion; emit clear error if missing.
- **Configuration:**

  - `outputs:` can include `bcfks`, `jceks`, `bks`, etc. If dependencies missing, emit **actionable warning** and skip.
- **Testing:**

  - Golden test vectors (keystores + expected listing via `keytool -list -rfc`), MAC verification, and round-trip import into a scratch JVM.
- **Optional CMS (`.cms`)**:

  - Expand PKCS7/CMS support if/when `cryptography` coverage is sufficient and interop is validated.

### Phase 3 — Directory & platform stores, PQC

- **Hash directories:** implement maker/verifier (but ships as an **archive** option to keep “single artifact” UX: e.g., `ca-trust-hashdir.tar.gz`).
- **NSS cert9.db:** driver using `certutil` in a containerized test harness.
- **PQC/Hybrid:** introduce feature flags once libraries stabilize.

---

## CLI / Config Additions

**Config (`manifest.json`):**

```json
{
  "outputs": ["pem", "p7b", "p12", "jks", "bcfks"],
  "java_config": {
    "keytool_path": "keytool",
    "providers": {
      "bcfips": "/opt/bc/bc-fips-*.jar",
      "bcprov": "/opt/bc/bcprov-*.jar"
    }
  }
}
```

**CLI (examples):**

```bash
# Python-native set
bundlecraft build --outputs pem,p7b,p12

# Include Java keystores (JKS already supported, BCFKS in Phase 2)
bundlecraft build --outputs pem,p7b,p12,jks,bcfks
```

**BCFKS (conversion) notes:**

- Implement in `bundlecraft.helpers.convert_utils` alongside existing JKS conversion logic.
- Prefer **BC FIPS** provider in regulated contexts; fall back to **BC non-FIPS** if requested.
- Pin algorithms: AES-GCM, PBKDF2-HMAC-SHA-512 with high iteration counts; record parameters in the manifest for auditability.
- Dependencies: Java `keytool`, BC provider jars (`bcfips`, `bcprov`). Capture tool/jar versions and hashes in `manifest.json`.

---

## Security Considerations

- **Password handling:** forbid empty passwords for keystores that support encryption/MAC. Support `--passfile` and environment variable plumbing, never echo to logs.
- **Determinism:** normalize certificate ordering (leaf→…→root or CA→…→root depending on format norms) and line endings to make hashes stable.
- **Verification artifacts:** keep or embed checksums (e.g., `checksums.sha256`) for all outputs; sign release bundles with existing GPG path (optional).
- **Java keystores (JKS/BCFKS):** capture tool versions, provider jar hashes, and full command lines (minus secrets) in `manifest.json` for audit trails.

---

## Backward Compatibility

- No breaking changes to existing outputs.
- New outputs are opt-in via `outputs` list.
- If an adapter is missing, the build **continues** and logs a clear, single-line skipped-output reason.

---

## Rollout & Testing

- **Golden vectors:** for each format, store a minimal 2-cert chain and a larger mixed chain; verify parse, counts, and expected DN/SKI/AKI across libraries.
- **Interop:** CI matrix (Linux/Windows/macOS) opening artifacts with platform tools: `keytool`, `certutil (Windows)`, `openssl`, and Python `cryptography`.
- **Property tests:** fuzz order and duplicate certs; ensure dedupe and stable output.

---

## Alternatives Considered

- **Only keytool-based outputs:** rejected for Phase 1 due to portability and dependency weight.
- **Exclude JKS/JCEKS entirely:** rejected; too much legacy demand. JKS already supported; JCEKS/BKS deferred to Phase 2.
- **Add hash directories now:** rejected due to "single artifact" constraint; revisit with archive packaging.
- **Create adapter layer:** rejected in favor of extending existing `convert_utils` module to keep conversion logic centralized.

---

## Open Questions

1. **PKCS#12 trust-only:** Which clients strictly require a key bag? We may conditionally include a dummy “null” bag only if standards-compliant.
2. **BCFKS MAC/encryption parameter profile:** Define a BundleCraft default (algorithm, iteration counts) and document rationale.
3. **PQC timing:** Which libraries (BC/openssl/pyca) will we bless for first-class hybrid X.509 once NIST profiles and interop stabilize?

---

## Summary

- **Approve Phase 1** to ship **PEM, PKCS#7, PKCS#12, JKS** as outputs with strong verification (JKS already supported).
- **Plan Phase 2** conversion utilities for **BCFKS** (top priority) plus **JCEKS/BKS** in `bundlecraft.helpers.convert_utils`.
- **Defer Phase 3** platform stores (NSS/Keychain) and directory formats (hash layout) and **PQC** flavors until maturity.
- **Drop SST support** as too niche and Windows-dependent; users can rename `.p7b` files if needed.
