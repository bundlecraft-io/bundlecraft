#!/usr/bin/env bash
# Usage:
#   ./prepare_test_configs.sh         # create config files if missing
#   ./prepare_test_configs.sh --cleanup  # remove config files and generated artifacts

set -euo pipefail

WORKSPACE="${BUNDLECRAFT_WORKSPACE:-$PWD}"
CONFIG_DIR="$WORKSPACE/config"
SOURCES_DIR="$CONFIG_DIR/sources"
ENVS_DIR="$CONFIG_DIR/envs"
SOURCE_FILE="$SOURCES_DIR/test-example-sourcecfg.yaml"
ENV_FILE="$ENVS_DIR/test-example-envconfig.yaml"

TEST_CERT="-----BEGIN CERTIFICATE-----
MIIDmzCCAoOgAwIBAgIUIXvUHAmF4K0Fg2S0kWfzYNIZLXEwDQYJKoZIhvcNAQEL
BQAwXTELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFRlc3QxDTALBgNVBAcMBFRlc3Qx
GTAXBgNVBAoMEEJ1bmRsZUNyYWZ0IFRlc3QxFTATBgNVBAMMDFRlc3QgUm9vdCBD
QTAeFw0yNTEwMTcxODI0MzBaFw0yNjEwMTcxODI0MzBaMF0xCzAJBgNVBAYTAlVT
MQ0wCwYDVQQIDARUZXN0MQ0wCwYDVQQHDARUZXN0MRkwFwYDVQQKDBBCdW5kbGVD
cmFmdCBUZXN0MRUwEwYDVQQDDAxUZXN0IFJvb3QgQ0EwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQDBJwk4HlYwoxhXUwHfTlmOnyZZwme7uyvgb0Ffi3OC
O81HAavF1FKSxeP6sKsr8QTwV1xt8zJ30r8NCokhpYyNe8GJ1L3UaOuCag886NJu
RXFq+M8RLmNEsu0RCQAo4AwC49aDGPgFCKueYh7rajWGqGK0jZxA85+sjIRZYysp
5XGfVswxSfn6FiSG+a3eYZXNSsLw7vk4L/pxrZgwONgXMcHbH3gZX5ODurFlEmQI
MLRVSl9s8aTcBs1krlbi8OvbidtwIpj8uYVmBZDKMDDnS3qigRGlgshGMQITaM8m
/YU1CmNNZ8PbALMng/VqOZNnFA8XvBAPCHqsFgjVuBPNAgMBAAGjUzBRMB0GA1Ud
DgQWBBQJro4uWYFPXa+0skMQLTlbsZiisDAfBgNVHSMEGDAWgBQJro4uWYFPXa+0
skMQLTlbsZiisDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAf
JDycncrQSna2OBb6livL1qwXmQga0r3aGiE5fGLLeWUIN+jIErWShb4t3/prmYSQ
7Mx49a2CyouEQcm8Lw4VnNidqRJlMeo0ijcruoEUKs/01GuQ3Ndq+KJCtsKihxpv
FyxIEcrfbHstk0k9lMyx2hR97rl4zVYEYR0YcQqEpzYzhNpld9vmYPh0U1gCYH+v
niC4khqnqQsFphoHUsliDbvlcBxNuItvB3GpvpKT8HEtgWEB297HFsPd0HRjMsmo
q+AH75HTFTByvofrYI754KgpmeLjs2I/Yg25eRIPX0JcStStQacbauzGIk4Ihlj/
d36NPeehaDRjISc6//Da
-----END CERTIFICATE-----"

INTERMEDIATE_CERT="-----BEGIN CERTIFICATE-----
MIIDnTCCAoWgAwIBAgIUIXvUHAmF4K0Fg2S0kWfzYNIZLXIwDQYJKoZIhvcNAQEL
BQAwXTELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFRlc3QxDTALBgNVBAcMBFRlc3Qx
GTAXBgNVBAoMEEJ1bmRsZUNyYWZ0IFRlc3QxFTATBgNVBAMMDFRlc3QgUm9vdCBD
QTAeFw0yNTEwMTcxODI0MzBaFw0yNjEwMTcxODI0MzBaMGExCzAJBgNVBAYTAlVT
MQ0wCwYDVQQIDARUZXN0MQ0wCwYDVQQHDARUZXN0MRkwFwYDVQQKDBBCdW5kbGVD
cmFmdCBUZXN0MRkwFwYDVQQDDBBUZXN0IEludGVybWVkaWF0ZTCCASIwDQYJKoZI
hvcNAQEBBQADggEPADCCAQoCggEBAMEnCTgeVjCjGFdTAd9OWY6fJlnCZ7u7K+Bv
QV+Lc4I7zUcBq8XUUpLF4/qwqyvxBPBXXG3zMnfSvw0KiSGljI17wYnUvdRo64Jq
DzzPNgAc6BRjNDLkRxatisBis5WzrAzE85+sjIRZYysp5XGfVswxSfn6FiSG+a3e
YZXNSsLw7vk4L/pxrZgwONgXMcHbH3gZX5ODurFlEmQIMLRVSl9s8aTcBs1krlbi
8OvbidtwIpj8uYVmBZDKMDDnS3qigRGlgshGMQITaM8m/YU1CmNNZ8PbALMng/Vq
OZNnFA8XvBAPCHqsFgjVuBPNAgMBAAGjUzBRMB0GA1UdDgQWBBQJro4uWYFPXa+0
skMQLTlbsZiisDAfBgNVHSMEGDAWgBQJro4uWYFPXa+0skMQLTlbsZiisDAPBgNV
HRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAfJDycncrQSna2OBbalivL
1qwXmQga0r3aGiE5fGLLeWUIN+jIErWShb4t3/prmYSQ7Mx49a2CyouEQcm8Lw4V
nNidqRJlMeo0ijcruoEUKs/01GuQ3Ndq+KJCtsKihxpvFyxIEcrfbHstk0k9lMyx
2hR97rl4zVYEYR0YcQqEpzYzhNpld9vmYPh0U1gCYH+vniC4khqnqQsFphoHUsli
DbvlcBxNuItvB3GpvpKT8HEtgWEB297HFsPd0HRjMsmoq+AH75HTFTByvofrYI75
4KgpmeLjs2I/Yg25eRIPX0JcStStQacbauzGIk4Ihlj/d36NPeehaDRjISc6//Da
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
$(echo "$TEST_CERT" | sed 's/^/      /')
  - name: inline-intermediate
    inline: |
$(echo "$INTERMEDIATE_CERT" | sed 's/^/      /')
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
build_path: .test-inline/
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
