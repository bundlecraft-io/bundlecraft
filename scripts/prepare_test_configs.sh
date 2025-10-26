#!/usr/bin/env bash
# Usage:
#   ./prepare_test_configs.sh         # create config files if missing
#   ./prepare_test_configs.sh --cleanup  # remove config files and generated artifacts

set -euo pipefail

WORKSPACE="${BUNDLECRAFT_WORKSPACE:-$PWD}"
CONFIG_DIR="$WORKSPACE/config"
SOURCES_DIR="$CONFIG_DIR/sources"
ENVS_DIR="$CONFIG_DIR/envs"
SOURCE_FILE="$SOURCES_DIR/.test-example-sourcecfg.yaml"
ENV_FILE="$ENVS_DIR/.test-example-envconfig.yaml"

ROOT_PEM="-----BEGIN CERTIFICATE-----
MIIBszCCAVmgAwIBAgIUQW1QkQw1QkQw1QkQw1QkQw1QkQw1QwDQYJKoZIhvcNAQEL
BQAwEzERMA8GA1UEAwwIdGVzdC1yb290MB4XDTI1MTAyNjAwMDAwMFoXDTI2MTAyNjAw
MDAwMFowEzERMA8GA1UEAwwIdGVzdC1yb290MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJB
ALwQkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1
QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkCAwEAAaNT
MFEwHQYDVR0OBBYEFK1QkQw1QkQw1QkQw1QkQw1QkQw1QkQwDwYDVR0TAQH/BAUwAwEB
/zAOBgNVHQ8BAf8EBAMCAQYwDQYJKoZIhvcNAQELBQADQQA1QkQw1QkQw1QkQw1QkQw1
QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQ
w1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1QkQw1
-----END CERTIFICATE-----"

INTERMEDIATE_PEM="-----BEGIN CERTIFICATE-----
MIIBtzCCAVugAwIBAgIUQW2QkQw2QkQw2QkQw2QkQw2QkQw2QwDQYJKoZIhvcNAQEL
BQAwEzERMA8GA1UEAwwIdGVzdC1yb290MB4XDTI1MTAyNjAwMDAwMFoXDTI2MTAyNjAw
MDAwMFowFzEVMBMGA1UEAwwMdGVzdC1pbnRlcm1lZGlhdGUwXDANBgkqhkiG9w0BAQEF
AANLADBIAkEA1QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2
QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkC
AwEAAaNTMFEwHQYDVR0OBBYEFK2QkQw2QkQw2QkQw2QkQw2QkQw2QkQwDwYDVR0TAQH/
BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAQYwDQYJKoZIhvcNAQELBQADQQA2QkQw2QkQw2Qk
Qw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2
QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQ
w2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2QkQw2Qk
-----END CERTIFICATE-----"

cleanup() {
  echo "[cleanup] Removing generated artifacts and test config files..."
  rm -rf "$WORKSPACE/cert_sources/staged" "$WORKSPACE/build_cache" "$WORKSPACE/dist"
  rm -f "$SOURCE_FILE" "$ENV_FILE"
  echo "[cleanup] Done."
}

ensure() {
  mkdir -p "$SOURCES_DIR" "$ENVS_DIR"
  if [[ ! -f "$SOURCE_FILE" ]]; then
    cat > "$SOURCE_FILE" <<EOF
---
apiVersion: bundlecraft.io/v1alpha1
kind: SourceConfig
source_name: test-example-sourcecfg
description: Inline test source config for quick BundleCraft testing.
repo:
  - name: inline-root
    inline: |
      $ROOT_PEM
  - name: inline-intermediate
    inline: |
      $INTERMEDIATE_PEM
metadata:
  owner: test@bundlecraft.io
  purpose: Quick test source config
  tags: [test, inline]
EOF
    echo "[create] $SOURCE_FILE"
  else
    echo "[skip] $SOURCE_FILE already exists; not overwriting."
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<EOF
---
apiVersion: bundlecraft.io/v1alpha1
kind: EnvConfig
name: test-example-envconfig
description: Minimal test env config for quick BundleCraft testing.
bundles:
  test-inline:
    include_sources: [test-example-sourcecfg]
output_formats:
  - pem
  - p7b
  - jks
  - p12
package: true
build_path: dist/test-inline/
verify:
  fail_on_expired: false
filters:
  unique_by_fingerprint: true
  not_expired_only: false
  ca_certs_only: true
pem:
  include_subject_comments: true
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD
    alias_format: '{subject.CN}-{serial}'
  pkcs12:
    password_env: TRUST_P12_PASSWORD
metadata:
  contact: test@bundlecraft.io
  environment_tier: test
EOF
    echo "[create] $ENV_FILE"
  else
    echo "[skip] $ENV_FILE already exists; not overwriting."
  fi

  echo "[ready] Test config files prepared:"
  echo "        - $SOURCE_FILE"
  echo "        - $ENV_FILE"
}

case "${1:-}" in
  --cleanup)
    cleanup
    ;;
  "")
    ensure
    ;;
  *)
    echo "Usage: $0 [--cleanup]" >&2
    exit 2
    ;;
esac
