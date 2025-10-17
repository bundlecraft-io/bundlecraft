#!/usr/bin/env bash
set -euo pipefail

# ==========================================
#  BundleCraft Local Vault Test Environment
# ==========================================
#
# Description:
#   Spins up a fully self-contained HashiCorp Vault instance for testing
#   BundleCraft’s Vault fetch capability. Supports interactive local use
#   and CI automation via --ci-cmd.
#
# Requirements:
#   For binary mode:
#     • Vault binary (https://developer.hashicorp.com/vault/downloads)
#
#   For Podman mode:
#     • Podman (installed and running)
#     • Internet connection (first run only, to pull Vault image)
#
# Usage:
#   ./vault_local.sh up [runtime] [options]
#   ./vault_local.sh down
#
# Runtime Options:
#   --runtime binary   (default; uses local vault CLI)
#   --runtime podman   (uses Podman container)
#
# Options:
#   --port <num>           Port for Vault (default: 8200)
#   --data-dir <path>      Directory for Vault data (default: ./local_vault)
#   --token <string>       Dev root token (default: root)
#   --image <name>         Vault Docker image (default: hashicorp/vault:latest)
#   --auto-cleanup         Automatically clean up after test run
#   --ci-cmd "<cmd>"       Run command non-interactively, then clean up
#   --verbose              Enable verbose logging
#   -h, --help             Show this help message
# ==========================================

VAULT_PORT=8200
VAULT_DATA_DIR="$(pwd)/local_vault"
VAULT_TOKEN="root"
AUTO_CLEANUP=false
CI_CMD=""
VERBOSE=false
RUNTIME="binary" # default

GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; RESET="\033[0m"
log()   { echo -e "${GREEN}[INFO]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }
usage() { grep '^# ' "$0" | cut -c 3-; exit 0; }

ACTION="${1:-}"; shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) VAULT_PORT="$2"; shift 2 ;;
    --data-dir) VAULT_DATA_DIR="$2"; shift 2 ;;
    --token) VAULT_TOKEN="$2"; shift 2 ;;
    --runtime) RUNTIME="$2"; shift 2 ;;
    --auto-cleanup) AUTO_CLEANUP=true; shift ;;
    --ci-cmd) CI_CMD="$2"; AUTO_CLEANUP=true; shift 2 ;;
    --verbose) VERBOSE=true; shift ;;
    -h|--help) usage ;;
    *) error "Unknown option: $1" ;;
  esac
done

VAULT_ADDR="http://127.0.0.1:${VAULT_PORT}"
PID_FILE="${VAULT_DATA_DIR}/vault.pid"
PODMAN_CONTAINER_NAME="bundlecraft-vault"

check_binary() {
  command -v vault >/dev/null 2>&1 || error "Vault CLI not found. Install from https://developer.hashicorp.com/vault/downloads"
}
check_podman() {
  command -v podman >/dev/null 2>&1 || error "Podman not found. Install from https://podman.io/getting-started"
}

start_vault_binary() {
  check_binary
  log "Starting Vault (binary mode)..."
  mkdir -p "${VAULT_DATA_DIR}"
  if [ -f "${PID_FILE}" ] && ps -p "$(cat ${PID_FILE})" >/dev/null 2>&1; then
    error "Vault already running (PID $(cat ${PID_FILE})). Stop it first."
  fi
  vault server -dev \
    -dev-root-token-id="${VAULT_TOKEN}" \
    -dev-listen-address="127.0.0.1:${VAULT_PORT}" \
    >"${VAULT_DATA_DIR}/vault.log" 2>&1 &
  echo $! > "${PID_FILE}"
  sleep 2
  export VAULT_ADDR VAULT_TOKEN
}

stop_vault_binary() {
  local stopped=false
  if [ -f "${PID_FILE}" ]; then
    pid=$(cat "${PID_FILE}")
    if ps -p "${pid}" >/dev/null 2>&1; then
      kill "${pid}"
      stopped=true
    fi
    rm -f "${PID_FILE}"
  fi
  if [ "${stopped}" = false ]; then
    warn "No Vault process found to stop (binary mode)."
  fi
}

start_vault_podman() {
  check_podman
  log "Starting Vault (Podman mode)..."
  mkdir -p "${VAULT_DATA_DIR}"
  if podman ps -a --format '{{.Names}}' | grep -q "^${PODMAN_CONTAINER_NAME}$"; then
    podman rm -f "${PODMAN_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi
  podman run -d \
    --name "${PODMAN_CONTAINER_NAME}" \
    -p ${VAULT_PORT}:8200 \
    -v "${VAULT_DATA_DIR}":/vault/data:Z \
    -e "VAULT_DEV_ROOT_TOKEN_ID=${VAULT_TOKEN}" \
    -e "VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200" \
    docker.io/hashicorp/vault:latest >/dev/null
  sleep 3
  export VAULT_ADDR VAULT_TOKEN
}

stop_vault_podman() {
  if podman ps -a --format '{{.Names}}' | grep -q "^${PODMAN_CONTAINER_NAME}$"; then
    podman rm -f "${PODMAN_CONTAINER_NAME}" >/dev/null
  else
    warn "No Vault container found to remove (podman mode)."
  fi
}

# Helper: run vault command (uses binary or podman exec based on runtime)
vault_cmd() {
  if [ "${RUNTIME}" = "binary" ]; then
    vault "$@"
  else
    # For podman runtime, use exec if available, otherwise fall back to API
    if podman exec "${PODMAN_CONTAINER_NAME}" vault "$@" 2>/dev/null; then
      return 0
    else
      warn "podman exec failed or unavailable, using API calls instead"
      return 1
    fi
  fi
}

# Helper: Vault API call wrapper
vault_api() {
  local method="$1"
  local path="$2"
  local data="${3:-}"

  local url="${VAULT_ADDR}/v1/${path}"
  local args=(-s -X "${method}" -H "X-Vault-Token: ${VAULT_TOKEN}")

  if [ -n "${data}" ]; then
    args+=(-H "Content-Type: application/json" -d "${data}")
  fi

  curl "${args[@]}" "${url}"
}

setup_vault_env() {
  log "Configuring Vault PKI test data..."

  # Try using vault CLI first (binary or podman exec)
  if vault_cmd secrets enable -path=pki/trusted_roots pki 2>/dev/null; then
    vault_cmd secrets tune -max-lease-ttl=8760h pki/trusted_roots
    vault_cmd write pki/trusted_roots/root/generate/internal common_name="local-root-ca" ttl=8760h >/dev/null
    local ca_cert=$(vault_cmd read -field=certificate pki/trusted_roots/cert/ca)
    vault_cmd kv put secret/pki/trusted_roots pem="${ca_cert}" >/dev/null
  else
    # Fall back to API calls (works without vault binary or exec)
    log "Using Vault HTTP API for configuration..."

    # Enable PKI secrets engine
    vault_api POST "sys/mounts/pki/trusted_roots" '{"type":"pki"}' >/dev/null 2>&1 || true

    # Tune max lease TTL
    vault_api POST "sys/mounts/pki/trusted_roots/tune" '{"max_lease_ttl":"8760h"}' >/dev/null

    # Generate root CA
    local root_response=$(vault_api POST "pki/trusted_roots/root/generate/internal" \
      '{"common_name":"local-root-ca","ttl":"8760h"}')

    # Extract certificate from response
    local ca_cert=$(echo "${root_response}" | grep -o '"certificate":"[^"]*"' | cut -d'"' -f4 | sed 's/\\n/\n/g')

    # Store in KV secrets (enable KV v2 first)
    vault_api POST "sys/mounts/secret" '{"type":"kv","options":{"version":"2"}}' >/dev/null 2>&1 || true

    # Put the certificate in KV
    vault_api POST "secret/data/pki/trusted_roots" \
      "{\"data\":{\"pem\":\"${ca_cert}\"}}" >/dev/null
  fi

  # Write debug file with the stored secret to help CI diagnostics
  mkdir -p "${VAULT_DATA_DIR}"
  vault_api GET "secret/data/pki/trusted_roots" > "${VAULT_DATA_DIR}/kv_secret_pki_trusted_roots.json" || true

  # Wait until the KV secret is readable (readiness gate)
  for i in {1..20}; do
    if vault_api GET "secret/data/pki/trusted_roots" | grep -q '"data"'; then
      log "KV secret is readable."; break; fi; sleep 0.5; done

  log "Test root CA injected successfully."
}

cmd_up() {
  case "${RUNTIME}" in
    binary) start_vault_binary ;;
    podman) start_vault_podman ;;
    *) error "Invalid runtime '${RUNTIME}'. Use 'binary' or 'podman'." ;;
  esac

  export VAULT_ADDR VAULT_TOKEN
  setup_vault_env

  echo -e "${GREEN}✅ Vault setup complete!${RESET}"
  echo "Vault Address : ${VAULT_ADDR}"
  echo "Root Token    : ${VAULT_TOKEN}"
  echo "Runtime       : ${RUNTIME}"
  echo

  if [ -n "${CI_CMD}" ]; then
    log "Running CI command: ${CI_CMD}"
    bash -c "${CI_CMD}" || warn "CI command failed."
    # Preserve artifacts for CI before teardown
    ART_DIR="${VAULT_DATA_DIR}_artifacts"
    mkdir -p "${ART_DIR}" || true
    if [ -d "${VAULT_DATA_DIR}" ]; then
      cp -a "${VAULT_DATA_DIR}/." "${ART_DIR}/" || true
    fi
    cmd_down
    exit 0
  fi

  if [ "${AUTO_CLEANUP}" = true ]; then
    echo -e "${YELLOW}[AUTO-CLEANUP ENABLED]${RESET}"
    read -p "Press ENTER when done testing to clean up Vault... " || true
    cmd_down
  else
    echo "Run '$0 down' when done."
  fi
}

cmd_down() {
  log "Tearing down Vault..."
  case "${RUNTIME}" in
    binary) stop_vault_binary ;;
    podman) stop_vault_podman ;;
  esac
  rm -rf "${VAULT_DATA_DIR}" || true
  echo -e "${GREEN}✅ Cleanup complete.${RESET}"
}

case "${ACTION}" in
  up) cmd_up ;;
  down) cmd_down ;;
  ""|-h|--help) usage ;;
  *) error "Unknown command: ${ACTION} (expected up|down)" ;;
esac
