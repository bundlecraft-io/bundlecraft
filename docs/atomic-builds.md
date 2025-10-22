# Atomic Build Implementation

## Overview

BundleCraft implements **atomic builds** to ensure reliability and consistency. Builds are all-or-nothing operations: either the entire build succeeds and commits to the final location, or it fails and leaves existing artifacts untouched.

## How It Works

### Build Process

1. **Temporary Build**: Each target builds to a unique temporary directory (`/tmp/bundlecraft-build-<uuid>/`)
2. **Complete Build**: All stages (fetch, convert, verify, finalize) execute in the temp location
3. **Atomic Commit**: On success, temp directory atomically moves to final location
4. **Cleanup**: On failure, temp directory is removed, final location preserved

```
Build Flow:
┌─────────────────────────────────────────────────────┐
│ 1. Create temp directory                           │
│    /tmp/bundlecraft-build-abc123/                  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│ 2. Build to temp                                    │
│    - Fetch sources                                  │
│    - Convert formats                                │
│    - Verify certificates                            │
│    - Write manifest & checksums                     │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│ 3. Atomic commit (on success)                       │
│    os.replace(temp, final) → POSIX atomic rename    │
│    dist/env/bundle/ now contains complete build   │
└─────────────────────────────────────────────────────┘
```

### Failure Handling

If build fails at any stage:
- Temp directory is automatically cleaned up
- Existing final directory (if any) is preserved
- No partial artifacts remain

```
Failure Flow:
┌─────────────────────────────────────────────────────┐
│ Build fails (expired cert, network error, etc.)     │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│ Cleanup temp directory                              │
│ rm -rf /tmp/bundlecraft-build-abc123/               │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│ Existing final location unchanged                   │
│ dist/env/bundle/ still has previous build (if any)│
└─────────────────────────────────────────────────────┘
```

## Features

### Signal Handling

Graceful cleanup on interruption (Ctrl+C, SIGTERM):

```bash
# Start build
bundlecraft build --env prod --bundle root-ca

# Press Ctrl+C during build
^C
[atomic] Received SIGINT, cleaning up...
[atomic] Cleaned up temp directory: /tmp/bundlecraft-build-abc123/
```

Temp directories are automatically removed, preventing disk space waste.

### Debug Mode

Use `--keep-temp` to preserve temp directory on failure for debugging:

```bash
bundlecraft build --env prod --bundle root-ca --keep-temp

# On failure:
[atomic] Build failed, cleaning up temp directory: /tmp/bundlecraft-build-abc123/
[atomic] Preserved temp directory for debugging: /tmp/bundlecraft-build-abc123/

# Inspect temp directory to debug
ls -la /tmp/bundlecraft-build-abc123/
```

**Remember to manually clean up preserved temp directories:**
```bash
rm -rf /tmp/bundlecraft-build-*
```

### Dry-Run Mode

Dry-run mode shows what would happen without committing:

```bash
bundlecraft build --env prod --bundle root-ca --dry-run

[atomic] Created temp build directory: /tmp/bundlecraft-build-abc123/
[dry-run] Would fetch: 3 sources
[dry-run] Would convert to: pem, jks, p12
[atomic] [dry-run] Would move /tmp/bundlecraft-build-abc123/ → dist/prod/root-ca/
```

Temp directories are not moved in dry-run mode but are cleaned up automatically.

## Platform Support

### Unix/Linux (Primary)

- **Atomic rename**: `os.replace()` uses POSIX `rename(2)` (atomic operation)
- **Signal handling**: Full SIGINT/SIGTERM support
- **Temp location**: `/tmp/` or `$TMPDIR`

### Windows (Best Effort)

- **Atomic rename**: `os.replace()` atomic if on same volume
- **Signal handling**: SIGINT only (limited)
- **Temp location**: `%TEMP%`

### Cross-Filesystem

If temp and final are on different filesystems (rare):
- Falls back to copy + verify + remove
- Logs when non-atomic fallback is used

## Benefits

### Reliability

- ✅ **No partial artifacts**: Failed builds don't corrupt output
- ✅ **Idempotent**: Can retry builds without manual cleanup
- ✅ **Concurrent safe**: Multiple targets build to separate temp dirs

### Safety

- ✅ **Preserves existing**: Failed builds don't delete previous successful builds
- ✅ **Interrupt safe**: Ctrl+C doesn't leave temp directories
- ✅ **Atomic commit**: Either complete build or no build (no in-between)

### Developer Experience

- ✅ **Debug mode**: `--keep-temp` for troubleshooting
- ✅ **Dry-run**: Preview builds without side effects
- ✅ **Clear errors**: Explicit failure handling with cleanup logs

## Implementation Details

### AtomicBuildContext

Context manager in `bundlecraft/helpers/atomic_build.py`:

```python
from bundlecraft.helpers.atomic_build import AtomicBuildContext

final_path = Path("dist/prod/root-ca")

with AtomicBuildContext(final_path, keep_temp=False, verbose=True) as temp_dir:
    # Build to temp_dir
    (temp_dir / "output.pem").write_text(build_output)
    # ... more build operations ...

# On __exit__:
# - Success: temp_dir atomically moved to final_path
# - Failure: temp_dir cleaned up, final_path preserved
```

### Builder Integration

Each target builds atomically in `bundlecraft/builder.py`:

```python
for target_name, bundle_dirs in staging_map.items():
    final_build_root = Path(output_root) / env / bundle_name

    with AtomicBuildContext(final_build_root, keep_temp=keep_temp) as build_root:
        # All build operations happen in build_root (temp)
        # ... fetch, convert, verify, finalize ...

    # Temp automatically committed to final_build_root on success
```

## Troubleshooting

### Temp Directories Not Cleaned Up

**Symptom**: `/tmp/bundlecraft-build-*` directories remain after builds

**Causes**:
1. Used `--keep-temp` flag (intentional)
2. Process killed with SIGKILL (uncatchable signal)
3. System crash during build

**Solution**:
```bash
# Safe cleanup (no active builds)
rm -rf /tmp/bundlecraft-build-*

# Check for active builds first
ps aux | grep bundlecraft
```

### Cross-Filesystem Issues

**Symptom**: Logs show "Cross-filesystem detected, using copy+verify fallback"

**Cause**: Temp directory (`/tmp/`) and output directory on different filesystems

**Impact**: Build still succeeds but uses copy instead of atomic rename (slower)

**Solution**: Not required (fallback works), but you can:
- Use same filesystem for temp and output
- Set `TMPDIR` environment variable to output filesystem

### Permission Errors

**Symptom**: `PermissionError` during atomic commit

**Cause**: Insufficient permissions to write to final location

**Solution**:
```bash
# Check permissions
ls -ld dist/env/bundle/

# Fix permissions
sudo chown -R $(whoami) dist/
```

## Testing

Atomic build behavior is tested in `tests/test_atomic_build.py`:

```bash
# Run atomic build tests
pytest tests/test_atomic_build.py -v

# Test scenarios:
# ✓ Successful builds commit atomically
# ✓ Failed builds preserve existing output
# ✓ Failed builds clean temp directories
# ✓ --keep-temp preserves temp on failure
# ✓ --dry-run doesn't commit
# ✓ Signal handling (SIGINT/SIGTERM)
# ✓ Concurrent builds don't interfere
```

## See Also

- [Issue #50: Atomic build implementation for resiliency](https://github.com/bundlecraft-io/bundlecraft/issues/50)
- [CONFIG-SPEC.md](CONFIG-SPEC.md) - Configuration options
- [troubleshooting.md](troubleshooting.md) - Common issues
