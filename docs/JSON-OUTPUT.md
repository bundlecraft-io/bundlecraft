# JSON Output Schemas

This document describes the machine-readable JSON output schemas for all BundleCraft commands when using the `--json` flag.

## Overview

All BundleCraft commands support a `--json` flag that emits structured, machine-readable output suitable for CI/CD automation and scripting. When `--json` is used, human-readable output is suppressed, and only the JSON response is printed to stdout.

## Base Schema

All JSON responses share a common base structure:

```json
{
  "success": boolean,
  "command": string,
  "timestamp": string (ISO 8601),
  "version": string
}
```

### Base Fields

- **success**: `boolean` - Indicates whether the command executed successfully
- **command**: `string` - The name of the command that was executed (e.g., "build", "verify", "convert", "fetch")
- **timestamp**: `string` - ISO 8601 formatted timestamp of when the command completed (UTC timezone)
- **version**: `string` - Version of BundleCraft that generated the response

## Command-Specific Schemas

### Build-All Plan (Discovery)

When running `bundlecraft build-all --print-plan --json`, the CLI emits a discovery plan that lists which environments would be built. This does not perform any build actions.

```json
{
  "pattern": "/abs/path/to/config/envs/*.yaml",
  "environments": [
    {
      "env": "dev",
      "name": "Development",
      "path": "/abs/path/to/config/envs/dev.yaml"
    },
    {
      "env": "prod",
      "name": "Production",
      "path": "/abs/path/to/config/envs/prod.yaml"
    }
  ]
}
```

Fields:

- **pattern**: `string` - The resolved glob or directory pattern used for discovery. Defaults to `config/envs/*.yaml` under the detected workspace.
- **environments**: `array` - List of discovered environments
  - **env**: `string` - Environment identifier (file stem of the YAML, e.g., `dev` for `dev.yaml`)
  - **name**: `string` - Human-friendly name from the environment config (`name`), falls back to `env` when unspecified
  - **path**: `string` - Absolute path to the environment config file

Examples:

```bash
# Discover all envs
bundlecraft build-all --print-plan --json

# Discover envs scoped to a subdirectory
bundlecraft build-all --envs-path teamA --print-plan --json

# Discover envs using a glob pattern
bundlecraft build-all --envs-path "teamA/*.yaml" --print-plan --json

# Recursively discover all envs in subdirectories
bundlecraft build-all --recursive --print-plan --json

# Combine recursive with scoping
bundlecraft build-all --envs-path teamA --recursive --print-plan --json
```

### Build Command

The `build` command produces the following JSON structure:

```json
{
  "success": boolean,
  "command": "build",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "env": string,
  "bundles": [
    {
      "name": string,
      "certificate_count": integer,
      "output_formats": [string],
      "output_path": string,
      "sources": [string],
      "verification": {
        "passed": boolean,
        "errors": [string],
        "warnings": [string]
      }
    }
  ],
  "errors": [string] (optional),
  "dry_run": boolean (optional)
}
```

#### Build Fields

- **env**: `string` - Name of the env/environment used for the build
- **bundles**: `array` - List of bundles that were built
  - **name**: `string` - Name of the bundle
  - **certificate_count**: `integer` - Number of certificates in the bundle
  - **output_formats**: `array of string` - List of output formats generated (e.g., ["pem", "jks", "p12"])
  - **output_path**: `string` - Path to the output directory
  - **sources**: `array of string` - List of source names included in this bundle
  - **verification**: `object` - Verification results (if verification was performed)
    - **passed**: `boolean` - Whether verification passed
    - **errors**: `array of string` - List of verification errors
    - **warnings**: `array of string` - List of verification warnings
- **errors**: `array of string` (optional) - List of errors if the build failed
- **dry_run**: `boolean` (optional) - Present and `true` if `--dry-run` was used

#### Build Examples

**Successful build:**

```bash
bundlecraft build --env prod --bundle mozilla --json
```

```json
{
  "success": true,
  "command": "build",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "env": "prod",
  "bundles": [
    {
      "name": "mozilla",
      "certificate_count": 137,
      "output_formats": ["pem", "jks", "p12"],
      "output_path": "dist/prod/mozilla",
      "sources": ["mozilla"],
      "verification": {
        "passed": true,
        "errors": [],
        "warnings": []
      }
    }
  ]
}
```

**Build with errors:**

```json
{
  "success": false,
  "command": "build",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "env": "prod",
  "bundles": [],
  "errors": ["Env config not found: prod"]
}
```

### Verify Command

The `verify` command produces the following JSON structure:

```json
{
  "success": boolean,
  "command": "verify",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "target_path": string,
  "verified_files": integer,
  "skipped_files": integer,
  "total_certificates": integer,
  "errors": [string] (optional),
  "warnings": [string] (optional),
  "file_sha256": string (optional, for single file verification)
}
```

#### Verify Fields

- **target_path**: `string` - Path to the target file or directory that was verified
- **verified_files**: `integer` - Number of files successfully verified
- **skipped_files**: `integer` - Number of files skipped during verification
- **total_certificates**: `integer` - Total number of certificates counted across all files
- **errors**: `array of string` (optional) - List of verification errors
- **warnings**: `array of string` (optional) - List of verification warnings
- **file_sha256**: `string` (optional) - SHA256 hash of the file (only present when verifying a single file)

#### Verify Examples

**Successful verification:**

```bash
bundlecraft verify --target dist/prod/mozilla --json
```

```json
{
  "success": true,
  "command": "verify",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "target_path": "dist/prod/mozilla",
  "verified_files": 4,
  "skipped_files": 2,
  "total_certificates": 137
}
```

**Verification with errors:**

```json
{
  "success": false,
  "command": "verify",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "target_path": "dist/prod/mozilla",
  "verified_files": 3,
  "skipped_files": 2,
  "total_certificates": 137,
  "errors": [
    "bundlecraft-ca-trust.jks: hash mismatch (expected: abc123..., got: def456...)"
  ],
  "warnings": [
    "Certificate count mismatch detected: {'bundlecraft-ca-trust.pem': 137, 'bundlecraft-ca-trust.jks': 136}"
  ]
}
```

### Convert Command

The `convert` command produces the following JSON structure:

```json
{
  "success": boolean,
  "command": "convert",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "input_path": string,
  "output_dir": string,
  "output_format": string,
  "certificate_count": integer,
  "errors": [string] (optional),
  "dry_run": boolean (optional)
}
```

#### Convert Fields

- **input_path**: `string` - Path to the input file
- **output_dir**: `string` - Path to the output directory
- **output_format**: `string` - Bundle output format (e.g., "pem", "jks", "p12", "p7b")
- **certificate_count**: `integer` - Number of certificates processed (0 if count unavailable)
- **errors**: `array of string` (optional) - List of errors if conversion failed
- **dry_run**: `boolean` (optional) - Present and `true` if `--dry-run` was used

#### Convert Examples

**Successful conversion:**

```bash
bundlecraft convert --input bundle.pem --output-dir dist --output-format jks --json
```

```json
{
  "success": true,
  "command": "convert",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "input_path": "/path/to/bundle.pem",
  "output_dir": "/path/to/dist",
  "output_format": "jks",
  "certificate_count": 137
}
```

**Conversion with errors:**

```json
{
  "success": false,
  "command": "convert",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "input_path": "/path/to/bundle.pem",
  "output_dir": "/path/to/dist",
  "output_format": "jks",
  "certificate_count": 0,
  "errors": ["Input file not found: /path/to/bundle.pem"]
}
```

### Fetch Command

The `fetch` command produces the following JSON structure:

```json
{
  "success": boolean,
  "command": "fetch",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "bundle_name": string,
  "staging_path": string,
  "fetched_sources": integer,
  "local_sources": integer,
  "total_files": integer,
  "errors": [string] (optional),
  "dry_run": boolean (optional)
}
```

#### Fetch Fields

- **bundle_name**: `string` - Name of the bundle being fetched
- **staging_path**: `string` - Path to the staging directory where sources were fetched
- **fetched_sources**: `integer` - Number of remote sources fetched
- **local_sources**: `integer` - Number of local sources copied
- **total_files**: `integer` - Total number of files staged
- **errors**: `array of string` (optional) - List of errors if fetch failed
- **dry_run**: `boolean` (optional) - Present and `true` if `--dry-run` was used

#### Fetch Examples

**Successful fetch:**

```bash
bundlecraft fetch --source-config-file config/cert_sources/mozilla.yaml --json
```

```json
{
  "success": true,
  "command": "fetch",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "bundle_name": "mozilla",
  "staging_path": "/path/to/cert_sources/staged/mozilla",
  "fetched_sources": 1,
  "local_sources": 0,
  "total_files": 1
}
```

**Fetch with errors:**

```json
{
  "success": false,
  "command": "fetch",
  "timestamp": "2025-10-21T12:00:00+00:00",
  "version": "0.1.1",
  "bundle_name": "",
  "staging_path": "",
  "errors": ["Fetch failed: Connection timeout"]
}
```

## Error Handling

When a command fails, the JSON response will:

1. Set `success` to `false`
1. Include an `errors` array with one or more error messages
1. Still include all command-specific fields (some may be empty or have default values)
1. Exit with a non-zero exit code

## Using JSON Output in Scripts

### Bash Example

```bash
#!/bin/bash

# Build and capture JSON output
output=$(bundlecraft build --env prod --bundle mozilla --json)

# Check if successful
if echo "$output" | jq -e '.success' > /dev/null; then
  echo "Build succeeded"
  cert_count=$(echo "$output" | jq -r '.bundles[0].certificate_count')
  echo "Built $cert_count certificates"
else
  echo "Build failed"
  echo "$output" | jq -r '.errors[]'
  exit 1
fi
```

### Python Example

```python
import json
import subprocess
import sys

# Run build command
result = subprocess.run(
    ["bundlecraft", "build", "--env", "prod", "--bundle", "mozilla", "--json"],
    capture_output=True,
    text=True
)

# Parse JSON output
data = json.loads(result.stdout)

if data["success"]:
    print(f"Build succeeded")
    for bundle in data["bundles"]:
        print(f"  Bundle: {bundle['name']}")
        print(f"  Certificates: {bundle['certificate_count']}")
        print(f"  Formats: {', '.join(bundle['output_formats'])}")
else:
    print("Build failed:")
    for error in data.get("errors", []):
        print(f"  - {error}")
    sys.exit(1)
```

### GitHub Actions Example

```yaml
- name: Build trust bundle
  id: build
  run: |
    bundlecraft build --env prod --bundle mozilla --json > build-output.json
    echo "success=$(jq -r '.success' build-output.json)" >> $GITHUB_OUTPUT
    echo "cert_count=$(jq -r '.bundles[0].certificate_count' build-output.json)" >> $GITHUB_OUTPUT

- name: Check build result
  if: steps.build.outputs.success != 'true'
  run: |
    echo "Build failed"
    jq -r '.errors[]' build-output.json
    exit 1

- name: Report metrics
  run: |
    echo "Built ${cert_count} certificates"
  env:
    cert_count: ${{ steps.build.outputs.cert_count }}
```

## Schema Stability

The JSON schemas documented here are considered stable and will follow semantic versioning:

- **Patch versions** (0.1.x): No schema changes
- **Minor versions** (0.x.0): Additive changes only (new optional fields)
- **Major versions** (x.0.0): Breaking changes allowed (field removal, type changes, etc.)

When new fields are added in minor versions, they will always be optional to maintain backward compatibility.

## Validation

You can validate JSON output against expected schemas using tools like `jsonschema` or by checking for required fields in your automation scripts.

Example with Python jsonschema:

```python
from jsonschema import validate

build_schema = {
    "type": "object",
    "required": ["success", "command", "timestamp", "version", "env", "bundles"],
    "properties": {
        "success": {"type": "boolean"},
        "command": {"type": "string", "const": "build"},
        "timestamp": {"type": "string"},
        "version": {"type": "string"},
        "env": {"type": "string"},
        "bundles": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "certificate_count", "output_formats", "output_path", "sources"],
                "properties": {
                    "name": {"type": "string"},
                    "certificate_count": {"type": "integer"},
                    "output_formats": {"type": "array", "items": {"type": "string"}},
                    "output_path": {"type": "string"},
                    "bundles": {"type": "array", "items": {"type": "string"}},
                    "verification": {
                        "type": "object",
                        "properties": {
                            "passed": {"type": "boolean"},
                            "errors": {"type": "array", "items": {"type": "string"}},
                            "warnings": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        }
    }
}

# Validate output
validate(instance=json_output, schema=build_schema)
```
