#!/usr/bin/env bash
# Example script demonstrating JSON output from all BundleCraft commands
# This script shows how to use the --json flag for CI/CD automation
#
# Dependencies:
#   - jq: Command-line JSON processor (sudo apt-get install jq)

set -e

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it first:"
    echo "  Ubuntu/Debian: sudo apt-get install jq"
    echo "  macOS: brew install jq"
    echo "  Other: https://jqlang.github.io/jq/download/"
    exit 1
fi

echo "=== BundleCraft JSON Output Examples ==="
echo ""

# Example 1: Fetch command with JSON output
echo "1. Fetch Command (dry-run)"
echo "Command: bundlecraft fetch --bundle-config-file config/sources/mozilla.yaml --dry-run --json"
echo ""
bundlecraft fetch --bundle-config-file config/sources/mozilla.yaml --dry-run --json | jq .
echo ""

# Example 2: Convert command with JSON output
echo "2. Convert Command"
echo "Command: bundlecraft convert --input tests/data/certs/sample.pem --output-dir /tmp/convert-example --output-format pem --json"
echo ""
mkdir -p /tmp/convert-example
bundlecraft convert --input tests/data/certs/sample.pem --output-dir /tmp/convert-example --output-format pem --json | jq .
echo ""

# Example 3: Verify command with JSON output (single file)
echo "3. Verify Command (single file)"
echo "Command: bundlecraft verify --target tests/data/certs/sample.pem --json"
echo ""
bundlecraft verify --target tests/data/certs/sample.pem --json | jq .
echo ""

# Example 4: Parse JSON with jq to extract specific fields
echo "4. Extracting Specific Fields with jq"
echo "Command: bundlecraft fetch ... --json | jq -r '.success'"
echo ""
SUCCESS=$(bundlecraft fetch --bundle-config-file config/sources/mozilla.yaml --dry-run --json | jq -r '.success')
echo "Success: $SUCCESS"
echo ""

# Example 5: Using JSON output in error handling
echo "5. Error Handling with JSON Output"
echo ""
OUTPUT=$(bundlecraft fetch --bundle-config-file config/sources/mozilla.yaml --dry-run --json)
if echo "$OUTPUT" | jq -e '.success' > /dev/null; then
    echo "✅ Operation succeeded"
    FETCHED=$(echo "$OUTPUT" | jq -r '.fetched_sources')
    echo "   Fetched $FETCHED source(s)"
else
    echo "❌ Operation failed"
    echo "$OUTPUT" | jq -r '.errors[]' | while read -r error; do
        echo "   Error: $error"
    done
fi
echo ""

echo "=== Examples Complete ==="
