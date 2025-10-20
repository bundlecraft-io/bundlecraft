# Troubleshooting BundleCraft Fetch/Build/Verify

This guide covers common issues, root causes, and quick fixes when using the Fetch → Build → Verify → Convert pipeline.

---

## Fetch issues

- Insecure HTTP rejected
  - Symptom: Error: Insecure HTTP is not allowed / API fetch requires HTTPS endpoint
  - Fix: Use https:// URLs (or file:// for local). For APIs, configure verify.ca_file and optionally verify.tls_fingerprint_sha256.

- SHA256 mismatch
  - Symptom: SHA256 mismatch for <name>: expected X, got Y
  - Cause: Source content changed or expected pin incorrect.
  - Fix: Re-validate the source from the authoritative location; if expected, update verify.sha256. Otherwise investigate integrity concerns.

- TLS fingerprint mismatch
  - Symptom: TLS fingerprint mismatch for host:port
  - Cause: Server leaf cert rotated or you pinned the wrong fingerprint.
  - Fix: Retrieve the new SHA256 of the leaf certificate and update verify.tls_fingerprint_sha256 after validation.

- Custom CA required
  - Symptom: SSL certificate verify failed
  - Fix: Provide verify.ca_file pointing to a PEM bundle containing the issuing CA for the server.

- Vault: hvac not installed
  - Symptom: "Vault fetcher requires 'hvac' package"
  - Fix: Install extras: `pip install -e .[fetchers]`.

- Vault: missing token or addr
  - Symptom: "Vault token not found in environment variable" or "Vault address is required"
  - Fix: Set VAULT_TOKEN (or token_ref env), and VAULT_ADDR (or set addr in config). Optionally set namespace.

- Offline mode with fetch entries
  - Symptom: "Offline mode is enabled but fetch entries are present."
  - Fix: Pre-stage artifacts with bundlecraft fetch in a connected environment, commit/package them, then run build with --offline.

---

## Build issues

- Empty or missing outputs
  - Check inputs in `sources/` and `sources/staged/<craft>/`
  - Ensure include paths in the bundle config are correct.

- Unexpected duplicates or missing certs
  - Ensure filters (e.g., unique_by_fingerprint) are set appropriately in defaults or craft config.

- Packaging problems
  - Verify OpenSSL and keytool are installed for P7B/JKS/P12 conversions.

---

## Verify issues

- Expired certificates
  - Either remove/replace expired certs or relax fail_on_expired (not recommended for production).

- Count mismatches
  - Ensure all outputs were generated from the same canonical PEM and no post-processing occurred.

---

## Best practices

- Always HTTPS for remote sources; never http
- Pin content via verify.sha256 where feasible (e.g., Mozilla public bundle)
- Use verify.ca_file and optionally verify.tls_fingerprint_sha256 for API/services
- Keep tokens in env vars (KEYFACTOR_TOKEN, VAULT_TOKEN), not YAML
- Treat sources/fetched as ephemeral; do not rely on it as a cache
- Treat sources/staged as ephemeral; do not rely on it as a cache
- Embed provenance: keep provenance.fetch.json with builds for audit trails

---

## Mozilla and other public providers

- Mozilla CA bundle is published at <https://curl.se/ca/cacert.pem>
- Recommended: pin verify.sha256 to the published hash you validate through a trusted channel
- Consider aggregating public + internal roots by staging Mozilla bundle via fetch and layering internal CAs via local sources

---

## Getting help

- Run with --help on each subcommand
- Check docs in docs/ and bundlecraft/README.md
- Open an issue with logs, config snippets (redact secrets), and your environment details
