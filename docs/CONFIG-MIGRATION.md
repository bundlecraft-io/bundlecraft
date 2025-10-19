# Configuration Migration Guide

## Config Separation Enforcement (v0.1.0+)

### What Changed

Starting with version 0.1.0, BundleCraft strictly enforces the separation of concerns between bundle configs and craft configs:

- **Bundle configs** (`config/bundles/*.yaml`) — Define WHAT certificates to source and WHERE to get them
- **Craft configs** (`config/crafts/*.yaml`) — Define HOW to build and WHERE to distribute

Previously, the builder would fall back to bundle configs for build settings if they weren't found in craft configs. This fallback behavior has been **removed** to maintain clear config separation.

### Affected Settings

The following settings are **no longer read from bundle configs** and must be defined in craft configs (or use defaults):

- `verify` — Verification policies (fail_on_expired, warn_days_before_expiry)
- `pem` — PEM output options (include_subject_comments)
- `output_formats` — Output format list (pem, p7b, jks, p12)
- `package` — Whether to create .tar.gz archives
- `filters` — Certificate filtering rules
- `format_overrides` — Format-specific configuration (passwords, aliases)

### Migration Steps

If you have bundle configs that contain any of these settings:

#### Step 1: Identify Affected Bundle Configs

Run the builder with your existing configs. You'll see warnings like:

```
[WARN] Bundle config 'my-bundle' contains build settings: verify, output_formats, package. 
These keys are ignored. Move them to craft config 'my-env' instead.
```

Or search manually:

```bash
grep -E "^(verify|pem|output_formats|package|filters|format_overrides):" config/bundles/*.yaml
```

#### Step 2: Move Settings to Craft Configs

**Before** (bundle config):
```yaml
# config/bundles/internal.yaml
---
bundle_name: internal
description: Internal PKI certificates
include:
  - sources/internal/rootCA.pem
verify:                        # ❌ Not allowed in bundle config
  fail_on_expired: false
output_formats: [pem, jks]     # ❌ Not allowed in bundle config
package: true                  # ❌ Not allowed in bundle config
```

**After** (bundle config):
```yaml
# config/bundles/internal.yaml
---
bundle_name: internal
description: Internal PKI certificates
include:
  - sources/internal/rootCA.pem
# Build settings removed - moved to craft config
```

**After** (craft config):
```yaml
# config/crafts/dev.yaml
---
name: Development
description: Development environment
targets:
  internal:
    includes: [internal]
verify:                        # ✅ Correctly placed in craft config
  fail_on_expired: false
output_formats: [pem, jks]     # ✅ Correctly placed in craft config
package: true                  # ✅ Correctly placed in craft config
```

#### Step 3: Verify

Run the builder again. The warnings should disappear, and your builds should work as before:

```bash
bundlecraft build --env dev --bundle internal
```

### Default Values

If you don't specify these settings in your craft config, the following defaults apply:

| Setting | Default |
|---------|---------|
| `verify.fail_on_expired` | `true` |
| `verify.warn_days_before_expiry` | `30` |
| `pem.include_subject_comments` | `true` |
| `output_formats` | `["pem"]` |
| `package` | `false` |

### Why This Change?

This enforcement provides several benefits:

1. **Clarity** — No confusion about which config file controls build behavior
2. **Consistency** — Aligns with the documented config philosophy
3. **Flexibility** — Different environments can use the same bundle with different build settings
4. **Maintainability** — Build settings are centralized in one place per environment

### Example: Multi-Environment Setup

The same bundle can be used in different environments with different build settings:

```yaml
# config/bundles/shared.yaml (source definition only)
---
bundle_name: shared
description: Shared trust anchors
include:
  - sources/mozilla/cacert.pem
  - sources/internal/rootCA.pem
```

```yaml
# config/crafts/dev.yaml (permissive for development)
---
targets:
  shared:
    includes: [shared]
verify:
  fail_on_expired: false      # Allow expired certs in dev
output_formats: [pem]         # Only PEM for development
```

```yaml
# config/crafts/prod.yaml (strict for production)
---
targets:
  shared:
    includes: [shared]
verify:
  fail_on_expired: true       # Strict validation in prod
output_formats: [pem, jks, p12]  # Multiple formats for prod
package: true                 # Create archives for distribution
```

### Need Help?

If you encounter issues during migration:

1. Check the warning messages from the builder
2. Review the [CONFIG-SPEC.md](CONFIG-SPEC.md) for correct config structure
3. Look at example configs in `config/bundles/example-bundle.yaml` and `config/crafts/example-craft.yaml`
4. Open an issue on GitHub if you need assistance
