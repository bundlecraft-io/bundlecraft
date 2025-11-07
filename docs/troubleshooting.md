# Troubleshooting BundleCraft Fetch/Build/Verify

This guide covers common issues, root causes, and quick fixes when using the Fetch → Build → Verify → Convert pipeline.

______________________________________________________________________

## Fetch issues

- Insecure HTTP rejected

  - Symptom: Error: Insecure HTTP is not allowed / API fetch requires HTTPS endpoint
  - Fix: Use https:// URLs (or file:// for local). For APIs, configure verify.ca_file and optionally verify.tls_fingerprint_sha256.

- SHA256 mismatch

  - Symptom: SHA256 mismatch for `<name>`: expected X, got Y
  - Cause: Source content changed or expected pin incorrect.
  - Fix: Re-validate the source from the authoritative location; if expected, update verify.sha256. Otherwise investigate integrity concerns.

- TLS fingerprint mismatch

  - Symptom: TLS fingerprint mismatch for host:port
  - Cause: Server leaf cert rotated or you pinned the wrong fingerprint.
  - Fix: Retrieve the new SHA256 of the leaf certificate and update verify.tls_fingerprint_sha256 after validation.

- Custom CA required

  - Symptom: SSL certificate verify failed
  - Fix: Provide verify.ca_file pointing to a PEM bundle containing the issuing CA for the server.

- Vault: missing token or addr

  - Symptom: "Vault token not found in environment variable" or "Vault address is required"
  - Fix: Set VAULT_TOKEN (or token_ref env), and VAULT_ADDR (or set addr in config). Optionally set namespace.

- Offline build with fetch entries

  - Symptom: Network access is unavailable or disallowed, and your config includes `fetch:` entries.
  - Fix: Pre-stage artifacts with `bundlecraft fetch` in a connected environment, commit/package them, then run build with `--skip-fetch`.

______________________________________________________________________

## Build issues

- Empty or missing outputs

  - Check inputs in `cert_sources/` and `cert_sources/staged/<source_name>/`
  - Ensure include paths in the source config are correct.

- Unexpected duplicates or missing certs

  - Ensure filters (e.g., unique_by_fingerprint) are set appropriately in defaults or environment config.

- Packaging problems

  - Verify OpenSSL is installed for P7B and P12 conversions.

______________________________________________________________________

## YAML schema/validation failures

When a config file doesn't meet the schema, BundleCraft shows a Pydantic error with the exact location and reason. Here's how to read and fix them quickly.

### What the error looks like

```text
[ERROR] Fetch failed: Config validation failed for /path/to/config/cert_sources/test-bundle.yaml:
1 validation error for BundleConfig
fetch.0.url
  Value error, Only HTTPS URLs are allowed for security. Use https:// or file:// schemes.
```

### How to navigate and resolve

- Identify the file

  - The path after "for" is the config with the problem.

- Identify the section and field

  - The line like `fetch.0.url` means: in the `fetch` list, the first element (index 0), field `url`.
  - Other examples:
    - `repo.1.include.0` → repo[1] include list, first item
    - `bundles` → the whole bundles structure is invalid or empty
    - `metadata.policy_version` → wrong type/value under metadata

- Apply the fix (common cases)

  - Insecure HTTP URL

    - Symptom: `Only HTTPS URLs are allowed for security`
    - Fix: Use `https://` (or `file://` for local), exception for `http://localhost`.

  - Missing required field for fetch type

    - Symptom: `'url' is required for fetch type 'url'` (or `'endpoint' ...`, `'mount' and 'path' ...`)
    - Fix: Provide the required fields for the specified `type`.

  - Duplicate or reserved names

    - Symptom: `Duplicate repo names found: X` or `'<name>' is a reserved name`
    - Fix: Make names unique and avoid reserved: `include`, `exclude`, `fetch`, `repo`.

  - Empty/invalid bundles in env

    - Symptom: `Env must have at least one bundle defined` or
      `At least one of 'include_sources' must be provided`
    - Fix: Add at least one include_sources list to each bundle.

  - Inline include mappings

    - Symptom: `Include dict must have either 'inline' or 'path' key`
    - Fix: Use a string path, `{ path: ... }`, or `{ inline: <PEM>, name?: <file> }`.

  - Numeric metadata fields

    - Symptom: `metadata.policy_version: Input should be a valid string`
    - Fix: Allowed now; numeric values are auto-converted to strings by the schema.

### Migration tips

- Prefer the `repo:` structure for includes; the legacy top-level `include`/`exclude` still works but is discouraged.
- Vault configs use `mount`, not `mount_point`.
- API endpoints must be HTTPS (`endpoint:`), like URL fetchers.
- Keep `bundle_name`/`description` (bundle) and `name`/`description` (env) non-empty.

______________________________________________________________________

## Verify issues

- Expired certificates

  - Either remove/replace expired certs or relax fail_on_expired (not recommended for production).

- Count mismatches

  - Ensure all outputs were generated from the same canonical PEM and no post-processing occurred.

______________________________________________________________________

## Best practices

- Always HTTPS for remote sources; never http
- Pin content via verify.sha256 where feasible (e.g., Mozilla public bundle)
- Use verify.ca_file and optionally verify.tls_fingerprint_sha256 for API/services
- Keep tokens in env vars (KEYFACTOR_TOKEN, VAULT_TOKEN), not YAML
- Treat cert_sources/fetched as ephemeral; do not rely on it as a cache
- Treat cert_sources/staged as ephemeral; do not rely on it as a cache
- Embed provenance: keep provenance.fetch.json with builds for audit trails

______________________________________________________________________

## Mozilla and other public providers

- Mozilla CA bundle is published at <https://curl.se/ca/cacert.pem>
- Recommended: pin verify.sha256 to the published hash you validate through a trusted channel
- Consider aggregating public + internal roots by staging Mozilla bundle via fetch and layering internal CAs via local sources

______________________________________________________________________

## Getting help

- Run with --help on each subcommand
- Check docs in docs/ and bundlecraft/README.md
- Open an issue with logs, config snippets (redact secrets), and your environment details

______________________________________________________________________

## Pytest failures: quick navigation

When a test fails, start by re-running just that test with more context.

- Show one test's full traceback and logs:

```bash
python3 -m pytest tests/test_fetch.py::TestFetch::test_fetch_no_section -vv -s
```

- Hide tracebacks for a cleaner summary (good for scanning):

```bash
python3 -m pytest -q --tb=line
```

- Re-run only previously failed tests:

```bash
python3 -m pytest --lf -q
```

- Stop on first failure to iterate faster:

```bash
python3 -m pytest -x -q
```

- Print local variables in tracebacks:

```bash
python3 -m pytest -vv --showlocals
```

Tip: For YAML/schema errors, see the section above: "YAML schema/validation failures".

______________________________________________________________________

## pre-commit failures: common hooks and fixes

This repo typically uses hooks like formatting, linting, and basic markdown checks. If a commit is blocked:

- See what failed and why:

```bash
pre-commit run --all-files
```

- Auto-fix (most hooks will rewrite files):

```bash
pre-commit run --all-files --hook-stage manual
```

Common issues:

- Import sort / formatting (Python)

  - Symptom: "Import block is un-sorted or un-formatted"
  - Fix: Let the hook auto-fix, or run your formatter (e.g., ruff/black/isort) locally.

- Markdown lint

  - Symptom: Duplicate headings, missing language identifiers, bare URLs, or blanks around lists.
  - Fix: Adjust headings, add language after `fences (e.g.,`bash), wrap bare URLs in \<...>, ensure blank lines around lists/headers.

- Trailing whitespace / EOF newline

  - Fix: Let hooks auto-fix or configure your editor to trim trailing spaces and add final newline.

Bypass (not recommended): use `--no-verify` on `git commit` if you're in a pinch. Prefer fixing to keep CI green.
