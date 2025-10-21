# Test CA Certificate Generator

⚠️ **TESTING ONLY - DO NOT USE FOR PRODUCTION** ⚠️

## Overview

The `scripts/generate_test_cas.py` tool generates self-signed root CAs and subordinate certificate chains exclusively for BundleCraft testing. It implements automatic private key disposal to prevent misuse and align with BundleCraft's trust-only principles.

## Purpose

BundleCraft is a **certificate trust management** system-it processes and distributes public trust anchors, never private keys. However, development and testing require test certificate chains.

This tool bridges that gap by:
- Generating test certificates on-demand
- **Immediately destroying all private key material** after certificate generation
- Preventing key export through intentional design constraints
- Providing flexible hierarchy generation for testing scenarios

## Security Model

### Key Principles

1. **Zero Persistence**: Private keys are NEVER written to disk
2. **Immediate Disposal**: Keys are zeroed in memory after certificate generation
3. **No Export**: No API or flag allows private key export
4. **Clear Intent**: Interactive warnings and "TESTING ONLY" messaging throughout

### Why No Private Key Export?

This aligns with BundleCraft's core principle: we manage **trust**, not **keys**. By preventing key export:
- Users cannot accidentally use test CAs for real systems
- Tool cannot be repurposed as a general CA infrastructure
- Development stays focused on trust bundle workflows

### Memory Clearing

Private keys are disposed via:
1. Export key to PEM bytes (to get memory reference)
2. Zero all bytes in a mutable bytearray
3. Delete all references
4. Python garbage collection

This is best-effort for Python (not cryptographically guaranteed) but significantly better than leaving keys in memory.

## Usage

### Single Root CA

```bash
python scripts/generate_test_cas.py --name my-test-root --no-warning
```

Output: `generated-test-cas/root/my-test-root.pem`

### Root with Subordinate Chain

```bash
python scripts/generate_test_cas.py \
  --name dev-root \
  --depth 2 \
  --env dev \
  --boundary internal \
  --no-warning
```

Output:
- `generated-test-cas/dev/internal/root/dev-root.pem`
- `generated-test-cas/dev/internal/tier1/dev-root-sub1.pem`
- `generated-test-cas/dev/internal/tier2/dev-root-sub2.pem`

### Batch Generation

Create `hierarchies.json`:

```json
[
  {
    "root_name": "test-root-a",
    "depth": 1,
    "env": "test",
    "boundary": "internal"
  },
  {
    "root_name": "test-root-b",
    "depth": 2,
    "env": "test",
    "boundary": "dmz",
    "key_size": 4096,
    "validity_days": 730
  }
]
```

Run:

```bash
python scripts/generate_test_cas.py --config hierarchies.json --no-warning
```

### Custom Settings

```bash
python scripts/generate_test_cas.py \
  --name prod-test \
  --key-size 4096 \
  --validity 730 \
  --output-dir /tmp/test-cas \
  --no-warning
```

## CLI Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--name` | Root CA common name | *(required unless --config)* |
| `--depth` | Number of subordinate tiers (0-10) | 0 (root only) |
| `--env` | Environment label (dev/qa/prod) | None |
| `--boundary` | Network boundary (internal/dmz/external) | None |
| `--key-size` | RSA key size in bits | 2048 |
| `--validity` | Certificate validity in days | 365 |
| `--output-dir` | Root output directory | `./generated-test-cas` |
| `--config` | JSON config file for batch mode | None |
| `--no-warning` | Skip security confirmation (for automation) | False |

## Output Structure

### With env/boundary labels

```
generated-test-cas/
└── <env>/
    └── <boundary>/
        ├── root/
        │   └── <name>.pem
        ├── tier1/
        │   └── <name>-sub1.pem
        └── tier2/
            └── <name>-sub2.pem
```

### Without labels (simple root)

```
generated-test-cas/
└── root/
    └── <name>.pem
```

## Integration with BundleCraft

### Use in Bundle Configs

```yaml
# config/bundles/test-bundle.yaml
bundle_name: test-internal
description: Test bundle with generated CAs
repo:
  - name: generated
    include:
      # Path entries (string or {path: ...})
      - generated-test-cas/dev/internal/root/dev-root.pem
      - { path: generated-test-cas/dev/internal/tier1/dev-root-sub1.pem }
      # Inline entry example (optional)
      # - name: ci-inline.pem
      #   inline: |
      #     -----BEGIN CERTIFICATE-----
      #     ...
      #     -----END CERTIFICATE-----
```

Build:

```bash
bundlecraft build --craft dev --bundle test-internal
```

### Use in CI/CD

Generate test chains in CI for fetch/verify testing:

```yaml
- name: Generate test CAs
  run: |
    python scripts/generate_test_cas.py \
      --name ci-test-root \
      --depth 2 \
      --output-dir /tmp/test-cas \
      --no-warning

- name: Test with generated CAs
  run: |
    bundlecraft build \
      --craft test \
      --bundle ci-test \
      --output-root dist
```

## Certificate Specifications

### Root CA

- Self-signed
- `basicConstraints: CA:TRUE` (no path length limit)
- `keyUsage: keyCertSign, cRLSign`
- Subject Key Identifier (SKI)
- Default validity: 365 days
- Default key size: 2048-bit RSA

### Subordinate CA

- Signed by parent (root or intermediate)
- `basicConstraints: CA:TRUE, pathlen=<remaining_depth>`
- `keyUsage: keyCertSign, cRLSign`
- Subject Key Identifier (SKI)
- Authority Key Identifier (AKI) from parent
- Inherits validity and key size from generator config

### Subject DN

All generated CAs have:

- `CN=<name>` (provided via CLI)
- `O=BundleCraft Test CA`
- `OU=Testing Only`

## Use Cases

### ✅ Appropriate Uses

- **Development**: Generate test chains for local BundleCraft development
- **CI/CD**: Populate test environments with ephemeral CAs for pipeline validation
- **Testing**: Create multi-tier hierarchies to test chain verification logic
- **Proof-of-Concept**: Demonstrate trust bundle workflows without real CAs

### ❌ Inappropriate Uses

- **Production**: Never use for live services or systems
- **Long-term infrastructure**: Not a replacement for proper PKI
- **Personal CA**: Not suitable for issuing certificates to users or devices
- **Key management**: Tool intentionally prevents key export

## Troubleshooting

### Missing `cryptography` module

```bash
pip install cryptography
```

Or install BundleCraft with dev dependencies:

```bash
pip install -e ".[dev]"
```

### Permission denied on output directory

Ensure the output directory is writable:

```bash
mkdir -p generated-test-cas
chmod 755 generated-test-cas
```

### Accidentally committed test certificates

Test certificates are `.gitignore`d by default. To clean up:

```bash
rm -rf generated-test-cas/
```

### Script requires confirmation

For automation/CI, use `--no-warning`:

```bash
python scripts/generate_test_cas.py --name ci-root --no-warning
```

## Design Decisions

### Why Python over Shell?

- **Cryptographic libraries**: Modern `cryptography` library for proper X.509 generation
- **Memory management**: Better control over key disposal
- **Complex logic**: Hierarchies and config parsing
- **Cross-platform**: Works on Linux, macOS, Windows without modification

Shell would require multiple `openssl` command invocations and temp file management-much riskier for key material.

### Why Dispose Keys Immediately?

Even though keys are only for testing:

1. **Principle enforcement**: Aligns with BundleCraft's trust-only model
2. **Habit formation**: Developers don't get comfortable with key material
3. **Accident prevention**: Can't accidentally export or persist keys
4. **Clear separation**: Test cert generation vs. real PKI operations

### Why Max Depth of 10?

- Realistic: Real-world PKI rarely exceeds 5-6 levels
- Safe: Prevents runaway recursion or config errors
- Flexible: Enough for complex test scenarios
- Path length constraints properly enforced at each tier

## Future Enhancements

Potential additions (if needed):

- ECDSA/Ed25519 key algorithm support (currently RSA only)
- Custom subject DN fields via CLI
- CRL/OCSP URL extensions
- Certificate policy OIDs
- SAN (Subject Alternative Names) for test end-entity certs

These are intentionally omitted to keep the tool simple and focused on CA generation only.

## Related Documentation

- [Scripts Reference](../scripts/README.md#-generate_test_caspy) - CLI usage and examples
- [ADR-0002: Fetch Layer](adr-0002-fetch.md) - Context on trust-only principles
- [Troubleshooting](troubleshooting.md) - General BundleCraft debugging

## License

Same as BundleCraft (MIT).
