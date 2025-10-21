# BundleCraft CLI Exit Codes

BundleCraft uses standardized exit codes to communicate command outcomes to calling processes. This is particularly important for CI/CD integration, automation, and error handling.

## Exit Code Reference

### Success
| Code | Name | Description |
|------|------|-------------|
| `0` | `SUCCESS` | Operation completed successfully |

### General Errors
| Code | Name | Description |
|------|------|-------------|
| `1` | `GENERAL_ERROR` | Unspecified error (catch-all for unexpected failures) |

### Configuration Errors (2-9)
| Code | Name | Description |
|------|------|-------------|
| `2` | `CONFIG_ERROR` | Invalid configuration (schema validation failed, syntax error, or invalid values) |
| `3` | `CONFIG_NOT_FOUND` | Missing required configuration file |

### Input/Output Errors (10-19)
| Code | Name | Description |
|------|------|-------------|
| `10` | `INPUT_ERROR` | Invalid input arguments or missing required input |
| `11` | `OUTPUT_ERROR` | Cannot write output files (permissions, disk space, etc.) |

### Network/Fetch Errors (20-29)
| Code | Name | Description |
|------|------|-------------|
| `20` | `NETWORK_ERROR` | Network connection failure (timeout, DNS resolution, etc.) |
| `21` | `AUTH_ERROR` | Authentication or authorization failure |
| `22` | `FETCH_ERROR` | Remote fetch failed (non-network issue, e.g., resource not found) |

### Validation Errors (30-39)
| Code | Name | Description |
|------|------|-------------|
| `30` | `VALIDATION_ERROR` | Certificate or bundle validation failed |
| `31` | `EXPIRED_CERT` | One or more certificates have expired |
| `32` | `INVALID_CERT` | Certificate is malformed or cannot be parsed |

### Build/Conversion Errors (40-49)
| Code | Name | Description |
|------|------|-------------|
| `40` | `BUILD_ERROR` | Build process failed (general build failure) |
| `41` | `CONVERSION_ERROR` | Format conversion failed (PEM ↔ P7B/JKS/P12) |

### Runtime Errors (50-59)
| Code | Name | Description |
|------|------|-------------|
| `50` | `DEPENDENCY_ERROR` | Missing required system dependency (openssl, keytool, etc.) |
| `51` | `PERMISSION_ERROR` | Insufficient permissions to perform operation |

---

## Command-Specific Exit Codes

### `bundlecraft build`

| Exit Code | Scenario |
|-----------|----------|
| `0` | Build completed successfully |
| `2` | Invalid craft config file (schema error, syntax error) |
| `3` | Missing required config file |
| `31` | Certificate(s) expired during build |
| `32` | Invalid or malformed certificate(s) in source |
| `40` | Build failed (cannot write output, conversion failure) |

**Example:**
```bash
bundlecraft build --craft-config-file craft.yaml
echo $?  # Check exit code
```

### `bundlecraft verify`

| Exit Code | Scenario |
|-----------|----------|
| `0` | Verification passed |
| `1` | Certificates expiring soon (warning) |
| `10` | Invalid target path |
| `30` | Verification failed (checksum mismatch, signature invalid) |
| `31` | Expired certificates detected |
| `32` | Invalid/malformed certificates |

**Example:**
```bash
bundlecraft verify --target dist/my-craft/production/
if [ $? -eq 31 ]; then
    echo "ERROR: Expired certificates detected"
    exit 1
fi
```

### `bundlecraft convert`

| Exit Code | Scenario |
|-----------|----------|
| `0` | Conversion successful |
| `10` | Missing or invalid input file |
| `11` | Cannot write to output directory |
| `41` | Conversion failed (format error, openssl/keytool failure) |

**Example:**
```bash
bundlecraft convert --input bundle.pem --output-dir ./output --output-format p7b
if [ $? -ne 0 ]; then
    echo "ERROR: Conversion failed"
fi
```

### `bundlecraft fetch`

| Exit Code | Scenario |
|-----------|----------|
| `0` | Fetch completed successfully |
| `2` | Invalid bundle config file |
| `20` | Network connection failure |
| `21` | Authentication/authorization failure |
| `22` | Fetch failed (resource not found, invalid response) |

**Example:**
```bash
bundlecraft fetch --bundle-config-file bundle.yaml
if [ $? -eq 20 ]; then
    echo "Network error - retrying..."
    sleep 5
    bundlecraft fetch --bundle-config-file bundle.yaml
fi
```

### `bundlecraft diff`

| Exit Code | Scenario |
|-----------|----------|
| `0` | Diff completed (changes detected or no changes) |
| `1` | Diff failed (invalid arguments, error reading files) |

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Build trust bundle
  id: build
  run: bundlecraft build --craft-config-file craft.yaml
  continue-on-error: true

- name: Handle build failure
  if: steps.build.outcome == 'failure'
  run: |
    EXIT_CODE=${{ steps.build.outputs.exit_code }}
    if [ "$EXIT_CODE" -eq 2 ]; then
      echo "::error::Configuration error - fix craft.yaml"
      exit 1
    elif [ "$EXIT_CODE" -eq 31 ]; then
      echo "::warning::Expired certificates detected"
      # Continue with build but notify team
    elif [ "$EXIT_CODE" -eq 20 ]; then
      echo "::warning::Network error - retrying"
      bundlecraft build --craft-config-file craft.yaml
    else
      echo "::error::Build failed with exit code $EXIT_CODE"
      exit 1
    fi
```

### GitLab CI

```yaml
build_bundle:
  script:
    - bundlecraft build --craft-config-file craft.yaml
  allow_failure:
    exit_codes:
      - 31  # Allow expired cert warnings in dev
  only:
    - develop
```

### Jenkins

```groovy
pipeline {
    stages {
        stage('Build') {
            steps {
                script {
                    def exitCode = sh(
                        script: 'bundlecraft build --craft-config-file craft.yaml',
                        returnStatus: true
                    )
                    
                    if (exitCode == 0) {
                        echo 'Build successful'
                    } else if (exitCode == 2) {
                        error('Configuration error - check craft.yaml')
                    } else if (exitCode == 31) {
                        unstable('Expired certificates detected')
                    } else if (exitCode == 20) {
                        // Retry on network errors
                        retry(3) {
                            sh 'bundlecraft build --craft-config-file craft.yaml'
                        }
                    } else {
                        error("Build failed with exit code: ${exitCode}")
                    }
                }
            }
        }
    }
}
```

---

## Troubleshooting Guide

### Quick Reference: Exit Code → Solution

| Exit Code | Problem | Solution |
|-----------|---------|----------|
| `2` | Configuration error | Validate config with `yamllint`, check schema |
| `3` | Config file not found | Verify file path, check working directory |
| `10` | Invalid input | Check input file exists and is readable |
| `11` | Cannot write output | Check disk space, permissions, parent directory exists |
| `20` | Network error | Check network connectivity, firewall rules, proxy settings |
| `21` | Auth error | Verify credentials, API tokens, certificate paths |
| `22` | Fetch error | Check remote resource exists, URL is correct |
| `30` | Validation failed | Review verification output, check checksums |
| `31` | Expired certs | Update certificates, check expiry dates with `openssl x509 -noout -dates` |
| `32` | Invalid cert | Verify PEM format, check for corruption |
| `40` | Build error | Check logs, verify dependencies (openssl, keytool) |
| `41` | Conversion error | Ensure input format is correct, check conversion target is supported |
| `50` | Missing dependency | Install required tools: `openssl`, `keytool` (JDK) |
| `51` | Permission error | Check file/directory permissions, run with appropriate user |

### Common Patterns

#### Network Retry Logic
```bash
#!/bin/bash
MAX_RETRIES=3
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
    bundlecraft fetch --bundle-config-file bundle.yaml
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Fetch successful"
        break
    elif [ $EXIT_CODE -eq 20 ]; then
        echo "Network error (attempt $i/$MAX_RETRIES) - retrying in ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    else
        echo "Fetch failed with exit code $EXIT_CODE"
        exit $EXIT_CODE
    fi
done
```

#### Expired Certificate Handling
```bash
#!/bin/bash
bundlecraft build --craft-config-file craft.yaml
EXIT_CODE=$?

case $EXIT_CODE in
    0)
        echo "✅ Build successful"
        ;;
    31)
        echo "⚠️  Expired certificates detected"
        # Send notification
        curl -X POST https://hooks.slack.com/... \
            -d '{"text": "Expired certificates in build"}'
        exit 0  # Continue deployment with warning
        ;;
    *)
        echo "❌ Build failed with exit code $EXIT_CODE"
        exit $EXIT_CODE
        ;;
esac
```

---

## Best Practices

1. **Always check exit codes in automation:**
   ```bash
   bundlecraft build --craft-config-file craft.yaml || exit $?
   ```

2. **Use exit codes for conditional logic:**
   ```bash
   if [ $? -eq 31 ]; then
       # Handle expired certs
   fi
   ```

3. **Log exit codes for debugging:**
   ```bash
   bundlecraft verify --target dist/
   EXIT_CODE=$?
   echo "Verification exit code: $EXIT_CODE" >> build.log
   ```

4. **Test failure scenarios in CI:**
   ```yaml
   - name: Test exit codes
     run: |
       # Test config error
       bundlecraft build --craft-config-file invalid.yaml || true
       # Test network error handling
       bundlecraft fetch --bundle-config-file bundle.yaml || true
   ```

5. **Document expected exit codes in your CI/CD pipeline:**
   ```yaml
   # Expected exit codes:
   #   0  - Success
   #   31 - Expired certs (warning only in dev)
   #   2  - Config error (fail build)
   ```

---

## Backward Compatibility

- **Exit code 0** (success) remains unchanged
- **Exit code 1** (general error) remains as catch-all
- **Exit code 2** used to indicate config errors (previously used for various errors)
- **New specific codes** (3, 10-11, 20-22, 30-32, 40-41, 50-51) provide finer granularity

Existing CI/CD pipelines checking only for `$? -eq 0` (success) or `$? -ne 0` (failure) will continue to work without modification.

---

## Related Documentation

- [Configuration Specification](./CONFIG-SPEC.md)
- [JSON Output Format](./JSON-OUTPUT.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [GitHub Actions Integration](./.github/workflows/bundlecraft.yaml)

---

## Feedback

If you encounter an error scenario that doesn't map clearly to an exit code, please [open an issue](https://github.com/chrisjpich/bundlecraft/issues) with details.
