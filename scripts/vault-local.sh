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
    docker.io/library/vault:latest >/dev/null
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

setup_vault_env() {
  log "Configuring Vault PKI test data..."
  vault secrets enable -path=pki/trusted_roots pki 2>/dev/null || true
  vault secrets tune -max-lease-ttl=8760h pki/trusted_roots
  vault write pki/trusted_roots/root/generate/internal common_name="local-root-ca" ttl=8760h >/dev/null
  vault kv put secret/pki/trusted_roots \
    pem="$(vault read -field=certificate pki/trusted_roots/cert/ca)" >/dev/null
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
