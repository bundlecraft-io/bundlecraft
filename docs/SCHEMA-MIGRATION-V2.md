# Schema Migration Guide v2.0

**Date:** 2025-01-XX
**Status:** Complete
**Breaking Change:** Yes

## Overview

This document describes the comprehensive schema refactor applied to BundleCraft to better align configuration file names and terminology with their actual purposes.

## Summary of Changes

### 1. Configuration Directory Renaming

| Old Path | New Path | Purpose |
|----------|----------|---------|
| `config/crafts/` | `config/envs/` | Environment-specific build configurations |
| `config/bundles/` | `config/sources/` | Certificate source definitions |

**Rationale:** The terms "craft" and "bundle" were ambiguous. "Environment" and "source" more clearly express the distinction between *how* to build (environment settings) and *what* to build from (certificate sources).

### 2. Configuration Schema Changes

#### Environment Configs (formerly Craft Configs)

**Location:** `config/envs/*.yaml` (formerly `config/crafts/*.yaml`)

**Changes:**
- `targets` → `bundles` (top-level field)
- `targets.<name>.includes` → `bundles.<name>.include_sources`

**Before:**
```yaml
name: Development
description: Development environment
targets:
  internal:
    includes: [internal, mozilla]
  mozilla-only:
    includes: [mozilla]
```

**After:**
```yaml
name: Development
description: Development environment
bundles:
  internal:
    include_sources: [internal, mozilla]
  mozilla-only:
    include_sources: [mozilla]
```

#### Source Configs (formerly Bundle Configs)

**Location:** `config/sources/*.yaml` (formerly `config/bundles/*.yaml`)

**Changes:**
- `bundle_name` → `source_name`

**Before:**
```yaml
bundle_name: internal
description: Internal PKI trust sources
repo:
  - name: roots
    include: [sources/internal/rootCA.pem]
```

**After:**
```yaml
source_name: internal
description: Internal PKI trust sources
repo:
  - name: roots
    include: [sources/internal/rootCA.pem]
```

### 3. CLI Changes

| Old Option | New Option | Command |
|------------|------------|---------|
| `--craft <name>` | `--env <name>` | `build`, `fetch` |

**Before:**
```bash
bundlecraft build --craft dev --bundle internal
```

**After:**
```bash
bundlecraft build --env dev --bundle internal
```

### 4. Terminology Updates

Throughout the codebase, documentation, and outputs:

| Old Term | New Term | Context |
|----------|----------|---------|
| Craft | Environment (or Env) | Build configuration context |
| Target | Bundle | Output bundle to be built |
| includes | include_sources | Source composition in bundles |
| bundle_name | source_name | Source configuration identifier |

## Migration Steps

### For Users

1. **Rename Configuration Directories**
   ```bash
   cd /path/to/your/bundlecraft/repo
   mv config/crafts config/envs
   mv config/bundles config/sources
   ```

2. **Update Environment Config Files**

   In each file under `config/envs/*.yaml`:
   ```bash
   sed -i 's/targets:/bundles:/g' config/envs/*.yaml
   sed -i 's/includes:/include_sources:/g' config/envs/*.yaml
   ```

3. **Update Source Config Files**

   In each file under `config/sources/*.yaml`:
   ```bash
   sed -i 's/bundle_name:/source_name:/g' config/sources/*.yaml
   ```

4. **Update CLI Commands**

   Replace `--craft` with `--env` in all scripts and CI pipelines:
   ```bash
   # Old
   bundlecraft build --craft prod --bundle internal

   # New
   bundlecraft build --env prod --bundle internal
   ```

5. **Update CI/CD Workflows**

   Update GitHub Actions, GitLab CI, or other automation:
   ```yaml
   # Old
   - run: bundlecraft build --craft production

   # New
   - run: bundlecraft build --env production
   ```

### For Developers

1. **Update Code References**

   If you have custom scripts or integrations:
   - Replace `config/crafts` → `config/envs`
   - Replace `config/bundles` → `config/sources`
   - Replace API references: `craft_config` → `env_config`, `bundle_config` → `source_config`

2. **Update Test Fixtures**

   Update any test data or mock configurations to use the new schema.

3. **Schema Validation**

   The Pydantic models in `bundlecraft/helpers/config_schema.py` now validate:
   - `EnvConfig` (formerly `CraftConfig`)
   - `SourceConfig` (formerly `BundleConfig`)
   - Legacy field names are supported via aliases for backward compatibility during transition

## Backward Compatibility

### Transition Period Support

The schema includes **temporary backward compatibility** through Pydantic field aliases:

- `targets` is aliased to `bundles` in environment configs
- `includes` is aliased to `include_sources`
- `bundle_name` is aliased to `source_name` in source configs

**Important:** These aliases will be **removed in v2.0.0**. Migrate your configs now.

### Legacy Config Path Support

The config loader checks both old and new paths:
- Looks for `config/envs/<name>.yaml` first
- Falls back to `config/crafts/<name>.yaml` if not found

This fallback will be removed in a future release.

## Validation

After migration, validate your setup:

1. **Check Configuration**
   ```bash
   python3 -c "
   from bundlecraft.helpers.config_schema import validate_env_config, validate_source_config
   from bundlecraft.helpers.utils import load_yaml
   from pathlib import Path

   # Validate an environment config
   env = load_yaml(Path('config/envs/dev.yaml'))
   validate_env_config(env, 'config/envs/dev.yaml')

   # Validate a source config
   source = load_yaml(Path('config/sources/internal.yaml'))
   validate_source_config(source, 'config/sources/internal.yaml')

   print('✓ Validation passed')
   "
   ```

2. **Test Build**
   ```bash
   bundlecraft build --env dev --bundle internal --dry-run --verbose
   ```

3. **Run Test Suite**
   ```bash
   pytest -v
   ```

## Impact Assessment

### Files Changed

- **Python modules:** 8 files (`builder.py`, `fetch.py`, `cli.py`, `verifier.py`, etc.)
- **Helper modules:** 4 files (config_schema.py, etc.)
- **Test files:** 12 files
- **CI workflows:** 3 files
- **Documentation:** README.md, CONTRIBUTING.md, 8 docs/*.md files
- **Scripts:** 5 utility scripts
- **Config examples:** All example configs updated

### Breaking Changes

- ❌ Old CLI flag `--craft` no longer works (use `--env`)
- ❌ Old config paths `config/crafts/` and `config/bundles/` will not be checked after v2.0.0
- ❌ Old schema fields (`targets`, `includes`, `bundle_name`) will not be supported after v2.0.0

### Non-Breaking (Backward Compatible During Transition)

- ✅ Legacy config paths still checked as fallback (temporary)
- ✅ Legacy field names accepted via Pydantic aliases (temporary)
- ✅ Existing builds continue to work with old directory structure (temporary)

## Rollback Plan

If you encounter issues after migration:

1. **Restore old directory structure:**
   ```bash
   mv config/envs config/crafts
   mv config/sources config/bundles
   ```

2. **Revert CLI changes:**
   ```bash
   # Use old commands
   bundlecraft build --craft prod --bundle internal
   ```

3. **Report the issue** with full context at: https://github.com/bundlecraft-io/bundlecraft/issues

## FAQ

### Q: Why this change?

**A:** The old terminology was confusing:
- "Craft" didn't clearly indicate it was an environment-specific config
- "Bundle" was overloaded (both source definition AND output bundle)
- "Target" vs "Bundle" distinction was unclear

The new naming is explicit:
- **Environment** = how/where to build
- **Source** = what certificates to source
- **Bundle** = output trust bundle

### Q: When will legacy support be removed?

**A:** Legacy field aliases and path fallbacks will be removed in **v2.0.0** (planned for Q2 2025). Migrate your configs by then.

### Q: Do I need to migrate immediately?

**A:** No, but it's recommended. The transition period allows old configs to work, but you should migrate to avoid breakage in v2.0.0.

### Q: Will my old builds still work?

**A:** Yes, temporarily. The system checks both old and new paths. However, plan to migrate before v2.0.0.

### Q: What about third-party integrations?

**A:** If you've built tooling around BundleCraft, update config paths and API references. Check the "For Developers" section above.

## Support

- **Issues:** https://github.com/bundlecraft-io/bundlecraft/issues
- **Discussions:** https://github.com/bundlecraft-io/bundlecraft/discussions
- **Security:** security@bundlecraft.io (for security-related config questions)

---

**Migration checklist:**

- [ ] Renamed `config/crafts/` → `config/envs/`
- [ ] Renamed `config/bundles/` → `config/sources/`
- [ ] Updated environment configs: `targets` → `bundles`, `includes` → `include_sources`
- [ ] Updated source configs: `bundle_name` → `source_name`
- [ ] Updated CLI commands: `--craft` → `--env`
- [ ] Updated CI/CD pipelines
- [ ] Updated custom scripts and integrations
- [ ] Tested build with `--dry-run`
- [ ] Ran full test suite
- [ ] Reviewed git diff for unexpected changes

---

© 2025 BundleCraft Contributors
Licensed under the MIT License
