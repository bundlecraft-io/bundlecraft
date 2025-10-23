# BundleCraft Diff - Certificate Bundle Comparison

The `bundlecraft diff` command compares two certificate bundles to identify changes between builds, releases, or environments. It's essential for:

- **Release Auditing** - Track which certificates were added or removed between versions
- **Change Validation** - Verify expected certificate updates before deployment
- **Trust Store Evolution** - Maintain historical records of trust policy changes
- **Compliance Reporting** - Document certificate changes for security audits

______________________________________________________________________

## 🎯 Quick Start

### Basic Usage

```bash
# Compare two bundle directories (human-readable output)
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal

# Generate JSON diff report
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal --output-format json

# Save diff to file
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal -o diff-report.txt
```

### Example Output (Human-Readable)

```text
=========================
🔐 BundleCraft Differ
=========================

FROM: dist/prod/v1/internal
  Env: production
  Bundle: internal
  Timestamp: 2025-10-15T14:30:00Z
  Certificates: 42

TO: dist/prod/v2/internal
  Env: production
  Bundle: internal
  Timestamp: 2025-10-23T10:15:00Z
  Certificates: 43

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------
  Added:     2
  Removed:   1
  Unchanged: 41
  Total Changes: 3

--------------------------------------------------------------------------------
ADDED CERTIFICATES (2)
--------------------------------------------------------------------------------
  Subject: CN=New Corporate Root CA 2025,O=Example Corp,C=US
    Fingerprint: a1b2c3d4e5f6...
    Issuer: CN=New Corporate Root CA 2025,O=Example Corp,C=US
    Valid: 2025-01-01T00:00:00+00:00 to 2045-01-01T00:00:00+00:00

  Subject: CN=Partner Trust Authority,O=Partner Org,C=GB
    Fingerprint: f6e5d4c3b2a1...
    Issuer: CN=Partner Trust Authority,O=Partner Org,C=GB
    Valid: 2025-03-15T00:00:00+00:00 to 2035-03-15T00:00:00+00:00

--------------------------------------------------------------------------------
REMOVED CERTIFICATES (1)
--------------------------------------------------------------------------------
  Subject: CN=Deprecated Root CA,O=Old Corp,C=US
    Fingerprint: 9876543210ab...
    Issuer: CN=Deprecated Root CA,O=Old Corp,C=US
    Valid: 2015-01-01T00:00:00+00:00 to 2025-01-01T00:00:00+00:00

================================================================================
```

______________________________________________________________________

## 📋 Command Reference

### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--from` | Yes | Path to the first (old) bundle directory |
| `--to` | Yes | Path to the second (new) bundle directory |
| `--output-format` | No | Output format: `human` (default) or `json` |
| `--output`, `-o` | No | Write output to file instead of stdout |

### Exit Codes

- `0` - Success (whether changes detected or not)
- `1` - General error (invalid paths, parsing failures, etc.)

______________________________________________________________________

## 🔍 How It Works

### Certificate Identification

The differ uses **SHA256 fingerprints** computed from the DER-encoded certificate to uniquely identify certificates. This ensures:

- **Reliable Comparison** - Same certificate = same fingerprint, regardless of PEM formatting
- **Change Detection** - Any modification to certificate data produces a different fingerprint
- **Deduplication** - Identical certificates (even with different comments) are recognized as the same

### Comparison Algorithm

1. **Load Certificates** - Parse PEM bundles from both directories
2. **Extract Metadata** - Read `manifest.json` if available for context
3. **Compute Sets** - Determine added, removed, and unchanged certificate sets
4. **Generate Report** - Format results as human-readable or JSON

### What Gets Compared

✅ **Included:**

- Certificate fingerprints (SHA256 of DER)
- Subject DN
- Issuer DN
- Serial number
- Validity period (not_before, not_after)

❌ **Not Compared:**

- PEM formatting differences (whitespace, line wrapping)
- Certificate order in bundle
- Comments or annotations in PEM
- File metadata (timestamps, permissions)

______________________________________________________________________

## 📊 Output Formats

### Human-Readable Format

Designed for terminal viewing and manual review:

- Clear section headers with visual separators
- Summary statistics upfront
- Full certificate details for added/removed certs
- Color-coded output (when terminal supports it)

Best for:

- Quick manual inspection
- Release notes generation (copy/paste sections)
- Developer/operator review

### JSON Format

Structured data for programmatic processing:

```json
{
  "from": {
    "path": "dist/prod/v1/internal",
    "manifest": {
      "env": "production",
      "bundle": "internal",
      "timestamp_utc": "2025-10-15T14:30:00Z"
    },
    "certificate_count": 42
  },
  "to": {
    "path": "dist/prod/v2/internal",
    "manifest": {
      "env": "production",
      "bundle": "internal",
      "timestamp_utc": "2025-10-23T10:15:00Z"
    },
    "certificate_count": 43
  },
  "diff": {
    "added": [
      {
        "fingerprint": "a1b2c3d4e5f6...",
        "subject": "CN=New Corporate Root CA 2025,O=Example Corp,C=US",
        "issuer": "CN=New Corporate Root CA 2025,O=Example Corp,C=US",
        "serial": "0x1a2b3c",
        "not_before": "2025-01-01T00:00:00+00:00",
        "not_after": "2045-01-01T00:00:00+00:00"
      }
    ],
    "removed": [
      {
        "fingerprint": "9876543210ab...",
        "subject": "CN=Deprecated Root CA,O=Old Corp,C=US",
        "issuer": "CN=Deprecated Root CA,O=Old Corp,C=US",
        "serial": "0x9f8e7d",
        "not_before": "2015-01-01T00:00:00+00:00",
        "not_after": "2025-01-01T00:00:00+00:00"
      }
    ],
    "unchanged": [...],
    "summary": {
      "added_count": 2,
      "removed_count": 1,
      "unchanged_count": 41,
      "total_changes": 3
    }
  }
}
```

Best for:

- CI/CD integration
- Automated testing (assert expected changes)
- Metrics collection
- Custom reporting tools

______________________________________________________________________

## 🔄 CI/CD Integration

### Use Cases

#### 1. **Pull Request Diff Comments**

Automatically comment on PRs with certificate changes:

```yaml
name: PR Certificate Diff
on:
  pull_request:
    paths:
      - 'cert_sources/**'
      - 'config/**'

jobs:
  diff-bundles:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for comparing with main

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install BundleCraft
        run: pip install -e .

      - name: Build current branch bundles
        run: |
          bundlecraft build --env production --bundle internal

      - name: Checkout main branch for baseline
        run: |
          git fetch origin main
          git checkout origin/main -- dist/

      - name: Compare bundles
        id: diff
        run: |
          bundlecraft diff \
            --from dist/production/internal \
            --to dist-current/production/internal \
            --output diff-report.txt

      - name: Comment PR with diff
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const diff = fs.readFileSync('diff-report.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## 🔐 Certificate Bundle Changes\n\n```\n' + diff + '\n```'
            });
```

#### 2. **Release Notes (Integrated in bundlecraft.yaml)**

Certificate diffs are generated and embedded directly into the release notes by the main `bundlecraft.yaml` workflow. No separate workflow is required.

What you get automatically in each release:

- Summary table of added/removed/unchanged certificates per bundle
- Collapsible details for added and removed certificates (subject, fingerprint, validity)
- Overall totals across all bundles
- First-release detection (no comparison when no prior release exists)

See the release stage details in: `docs/CI-CD.md` (Publish Release section).

#### 3. **Automated Change Validation**

Fail builds if unexpected changes occur:

```yaml
- name: Validate certificate changes
  run: |
    bundlecraft diff \
      --from baseline/production/internal \
      --to current/production/internal \
      --output-format json > diff.json

    # Parse JSON and validate
    python -c "
    import json, sys
    diff = json.load(open('diff.json'))
    added = diff['diff']['summary']['added_count']
    removed = diff['diff']['summary']['removed_count']

    # Fail if unexpected changes
    if removed > 0:
        print(f'ERROR: {removed} certificates removed!')
        sys.exit(1)
    if added > 5:
        print(f'WARNING: {added} certificates added (review required)')
        sys.exit(1)
    print(f'✓ Changes validated: +{added} -{removed}')
    "
```

#### 4. **Cross-Environment Comparison**

Compare different environments to ensure consistency:

```bash
# Ensure production has all dev certificates (superset check)
bundlecraft diff \
  --from dist/dev/internal \
  --to dist/prod/internal \
  --output-format json | \
  jq '.diff.removed[] | "Missing in prod: " + .subject'
```

______________________________________________________________________

## 💡 Advanced Usage

### Comparing Across Branches

```bash
# Compare current branch with main
git stash
bundlecraft build --env prod --bundle internal
mv dist dist-current

git checkout main
bundlecraft build --env prod --bundle internal

bundlecraft diff --from dist/prod/internal --to dist-current/prod/internal

git checkout -
git stash pop
```

### Multi-Bundle Comparison

Compare all bundles between releases:

```bash
#!/bin/bash
OLD_RELEASE="bundlecraft/v1"
NEW_RELEASE="bundlecraft/v2"

for bundle in $(ls "$NEW_RELEASE"); do
  echo "=== Comparing bundle: $bundle ==="
  bundlecraft diff \
    --from "$OLD_RELEASE/$bundle" \
    --to "$NEW_RELEASE/$bundle" \
    --output "diff-${bundle}.txt"
done
```

______________________________________________________________________

## 🔐 Security Considerations

### Fingerprint Verification

Always verify that expected certificates are present:

```bash
# After comparing, check specific fingerprints
bundlecraft diff --from old/ --to new/ --output-format json | \
  jq -r '.diff.added[].fingerprint' | \
  grep -q 'a1b2c3d4e5f6...' && echo "✓ Expected cert added" || exit 1
```

### Audit Trail

Maintain historical diff reports:

```bash
# Save diffs with timestamps
DATE=$(date +%Y%m%d-%H%M%S)
bundlecraft diff --from v1/ --to v2/ -o "audit/diff-${DATE}.txt"

# Commit to audit repository
git add audit/
git commit -m "Audit: Certificate changes ${DATE}"
```

### Change Approval Workflow

Require review for certificate changes:

```yaml
# .github/workflows/cert-review.yaml
- name: Check for certificate changes
  run: |
    bundlecraft diff --from baseline/ --to current/ --output-format json > diff.json

    if [ "$(jq '.diff.summary.total_changes' diff.json)" -gt 0 ]; then
      echo "requires_review=true" >> $GITHUB_OUTPUT
      gh pr edit ${{ github.event.pull_request.number }} \
        --add-label "security-review-required"
    fi
```

______________________________________________________________________

## 🛠️ Troubleshooting

### No PEM File Found

**Error:** Diff produces empty results or errors about missing files

**Solution:** Ensure both directories contain `bundlecraft-ca-trust.pem`:

```bash
ls -la dist/prod/v1/internal/bundlecraft-ca-trust.pem
ls -la dist/prod/v2/internal/bundlecraft-ca-trust.pem
```

### Unexpected Changes Detected

**Error:** Diff shows changes when you expected none

**Debug Steps:**

1. Compare file hashes directly:

   ```bash
   sha256sum dist/*/internal/bundlecraft-ca-trust.pem
   ```

2. Check build reproducibility:

   ```bash
   # Rebuild same config twice
   bundlecraft build --env prod --bundle internal
   mv dist/prod/internal dist-build1
   bundlecraft build --env prod --bundle internal
   bundlecraft diff --from dist-build1 --to dist/prod/internal
   # Should show "NO CHANGES DETECTED"
   ```

3. Inspect certificate details:

   ```bash
   bundlecraft diff --from old/ --to new/ --output-format json | \
     jq '.diff.added[] | {subject, not_before, not_after}'
   ```

### JSON Parsing Issues

**Error:** Cannot parse JSON output in scripts

**Solution:** Ensure proper JSON formatting:

```bash
# Use jq to validate and pretty-print
bundlecraft diff --from old/ --to new/ --output-format json | jq .

# Common jq queries
bundlecraft diff --from old/ --to new/ --output-format json | jq '.diff.summary'
bundlecraft diff --from old/ --to new/ --output-format json | jq '.diff.added | length'
```

______________________________________________________________________

## 📚 Related Documentation

- **[CONFIG-SPEC.md](CONFIG-SPEC.md)** - Bundle and environment configuration
- **[CI-CD.md](CI-CD.md)** - GitHub Actions workflows for BundleCraft
- **[JSON-OUTPUT.md](JSON-OUTPUT.md)** - JSON schemas for all commands
- **[Signing and SBOM](SIGNING-AND-SBOM.md)** - Release artifact signing
- **[Exit Codes](exit-codes.md)** - CI/CD exit code reference

______________________________________________________________________
