# 04-config-design.md

# Configuration Design

This document defines the configuration model for **pki-ca-trust**, including supported fields, defaults, and examples.

---

## 🧱 Structure Overview

All configuration is YAML (JSON also supported) and split into three layers:

| Type | Path | Purpose |
|------|------|----------|
| **Defaults** | `config/defaults.yaml` | Global defaults applied everywhere |
| **Environment Configs** | `config/envs/<env>.yaml` | Controls per-environment publishing and overrides |
| **Bundle Configs** | `config/bundles/<bundle>.yaml` | Defines what goes into each trust store bundle |

---

## Bundle Configuration Schema

```yaml
bundle_name: <string>             # Identifier for the trust bundle
description: <string>             # Optional human-readable description

include:                          # List of files or directories to include
  - sources/<path>/file.pem
exclude: []                       # Paths to exclude from inclusion

output_formats:                   # Output formats to build
  - pem
  - jks
  - p7b

pem:                              # PEM-specific behavior
  include_subject_comments: true  # Adds "# Subject:" above each PEM block

verify:                           # Certificate verification policy
  fail_on_expired: true           # Abort build if any cert is expired
  warn_days_before_expiry: 30     # Warn if cert expires within N days

package: true                     # Whether to produce package.tar.gz
```
**Example: `config/bundles/internal.yaml`**
```yaml
bundle_name: internal
description: Trust bundle for internal PKI services
include:
  - sources/internal/rootCA.pem
  - sources/internal/issuingCA1.pem
output_formats:
  - pem
  - jks
  - p7b
pem:
  include_subject_comments: true
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30
package: true
```

## Environment Configuration Schema
```yaml
bundle_targets:                   # Which bundles to build for this environment
  - internal
  - external

publish_targets:                  # Where to distribute results
  - type: fileshare
    path: "\\\\server\\path"
  - type: artifactory
    repo: "pki-trust/prod"
    credentials: env:ARTIFACTORY_TOKEN

format_overrides:                 # Per-format customization
  jks:
    keystore_password: changeit
  pem:
    include_chain: true
```

## Defaults Configuration Schema
```yaml
pem:
  include_subject_comments: true

verify:
  fail_on_expired: true
  warn_days_before_expiry: 30

format_overrides: {}

package: false
```
## ⚙️ Configuration Precedence

| Priority 	|       Source       	|                     Description                     	|
|:--------:	|:------------------:	|:---------------------------------------------------:	|
| 1️⃣        	| Bundle Config      	| Highest priority. Overrides environment & defaults. 	|
| 2️⃣        	| Environment Config 	| Controls publishing and per-format overrides.       	|
| 3️⃣        	| Defaults           	| Base values applied when no overrides exist.        	|

For example:
- If `verify.fail_on_expired` is set in bundle config → it overrides defaults.
- If missing, environment config can override it globally (future feature).
- Otherwise, defaults apply.

# 📁 File Path Rules
- All paths are relative to the repository root (`pki-ca-trust/`).
- Directories are recursively searched for `.pem` files.
- `exclude`: entries use normalized `/` paths (even on Windows).
- `include`: can reference both individual files and folders.