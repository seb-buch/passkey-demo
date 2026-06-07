#!/usr/bin/env zsh
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KRABSVAULT_DIR="${BASE_DIR}/krabsvault-app"
PHISHING_DIR="${BASE_DIR}/phishing-app"
INFRA_DIR="${BASE_DIR}/infra"

KRABSVAULT_PORT=8000
PHISHING_PORT=8666
PROXY_PORT=443

CHROME_PROFILE="Profile 2"
ZELLIJ_SESSION="demo-krabsvault"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STASHED=false

log_info() { echo "${BLUE}[INFO]${NC} $1" }
log_ok()   { echo "${GREEN}[ OK ]${NC} $1" }
log_err()  { echo "${RED}[FAIL]${NC} $1" >&2 }
log_warn() { echo "${YELLOW}[WARN]${NC} $1" }

kill_on_port() {
    local port=$1 name=$2
    local pids
    pids=$(lsof -ti "TCP:${port}" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        log_ok "Stopped $name (port $port)"
    else
        log_info "$name was not running (port $port)"
    fi
}

setup_krabsvault() {
    log_info "Setting up KrabsVault repository..."

    rm -f "${KRABSVAULT_DIR}/*.db" \
          "${KRABSVAULT_DIR}/*.db-shm" \
          "${KRABSVAULT_DIR}/*.db-wal"
    log_ok "Database cleaned"
}

start_proxy() {
    log_info "Checking podman machine..."

    local running
    running=$(podman machine list --format '{{.Running}}' 2>/dev/null | head -1)
    if [[ "$running" != "true" ]]; then
        log_info "Starting podman machine (this may take a moment)..."
        podman machine start
    fi
    log_ok "Podman machine is running"

    log_info "Starting reverse proxy..."
    podman compose -f "${INFRA_DIR}/compose.yml" up -d
    log_ok "Reverse proxy started"
}

open_chrome() {
    log_info "Opening Chrome with Demo-Devoxx profile..."
    open -na "Google Chrome" --args --profile-directory="$CHROME_PROFILE"
    log_ok "Chrome opened"
}

start_services() {
    log_info "Creating zellij session '${ZELLIJ_SESSION}'..."
    zellij attach --create-background "$ZELLIJ_SESSION"
    sleep 0.5

    log_info "Starting KrabsVault..."
    zellij --session "$ZELLIJ_SESSION" action new-tab --name "KrabsVault" --cwd "$KRABSVAULT_DIR" -- uv run krabsvault

    log_info "Starting Phishing..."
    zellij --session "$ZELLIJ_SESSION" action new-tab --name "Phishing" --cwd "$PHISHING_DIR" -- uv run phishing

    log_ok "All services launched in zellij tabs"
}

do_start() {
    echo ""
    echo "${BLUE}======================================${NC}"
    echo "${BLUE}      Preparing demo environment      ${NC}"
    echo "${BLUE}======================================${NC}"
    echo ""

    if [[ -n "${ZELLIJ:-}" ]]; then
        log_err "Already inside a zellij session. Run this from a plain terminal."
        exit 1
    fi

    zellij delete-session "$ZELLIJ_SESSION" 2>/dev/null || true
    if zellij list-sessions 2>/dev/null | grep -q "$ZELLIJ_SESSION"; then
        log_err "Zellij session '${ZELLIJ_SESSION}' is still running. Run '$0 stop' first."
        exit 1
    fi

    setup_krabsvault
    start_proxy
    open_chrome
    start_services

    echo ""
    if $STASHED; then
        log_warn "Your changes were stashed. Run 'cd $KRABSVAULT_DIR && git stash pop' when done."
    fi
    log_info "Attaching to zellij session..."
    log_info "To stop the demo, run: $0 stop"
    echo ""

    exec zellij attach "$ZELLIJ_SESSION"
}

do_stop() {
    echo ""
    echo "${BLUE}======================================${NC}"
    echo "${BLUE}  Tearing down demo environment       ${NC}"
    echo "${BLUE}======================================${NC}"
    echo ""

    kill_on_port $KRABSVAULT_PORT "KrabsVault"
    kill_on_port $PHISHING_PORT "Phishing"

    log_info "Stopping reverse proxy..."
    podman compose -f "${INFRA_DIR}/compose.yml" down 2>/dev/null || true
    log_ok "Reverse proxy stopped"

    if zellij list-sessions 2>/dev/null | grep -q "$ZELLIJ_SESSION"; then
        zellij kill-session "$ZELLIJ_SESSION" 2>/dev/null || true
        sleep 0.5
        zellij delete-session "$ZELLIJ_SESSION" 2>/dev/null || true
        log_ok "Zellij session '${ZELLIJ_SESSION}' removed"
    fi

    echo ""
    echo "${GREEN}  All services stopped.${NC}"
    echo ""
}

show_help() {
    echo "Usage: $0 <start|stop>"
    echo ""
    echo "  start  Set up git, database, reverse proxy, and launch all"
    echo "         services in a zellij session with Chrome"
    echo "  stop   Kill all services, zellij session, and reverse proxy"
}

case "${1:-}" in
    start) do_start ;;
    stop)  do_stop ;;
    *)
        show_help
        exit 1
        ;;
esac
