#!/usr/bin/env bash
# run_playwright_tests.sh
#
# Runs the Playwright E2E test suite in a fully isolated Docker environment.
# No local Python environment or browser installation is required.
#
# The suite spins up Home Assistant and the Playwright test runner via docker
# compose, then tears everything down on exit.
#
# Usage:
#   ./run_playwright_tests.sh

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[PASS]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[FAIL]${NC}  $*"; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yaml"

# ── Resolve docker compose command ───────────────────────────────────────────
get_compose_cmd() {
    if command -v docker &>/dev/null && sudo docker compose version &>/dev/null 2>&1; then
        echo "sudo docker compose"
    else
        error "docker compose is not available. Please install Docker with the Compose plugin."
        exit 1
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    if [[ $# -gt 0 ]]; then
        error "This script takes no arguments."
        echo "Usage: $0"
        exit 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "docker-compose.yaml not found at $COMPOSE_FILE"
        exit 1
    fi

    header "════════════════════════════════════════════════════"
    header " Playwright E2E tests (docker compose)"
    header "════════════════════════════════════════════════════"

    local compose_cmd
    compose_cmd="$(get_compose_cmd)"

    info "Building Docker images…"
    $compose_cmd -f "$COMPOSE_FILE" build

    info "Running test container (this may take several minutes on first run)…"
    local exit_code=0
    $compose_cmd -f "$COMPOSE_FILE" run --rm playwright-tests || exit_code=$?

    info "Stopping services…"
    $compose_cmd -f "$COMPOSE_FILE" down -v || true

    if [[ $exit_code -eq 0 ]]; then
        echo ""
        success "All Playwright E2E tests passed."
        exit 0
    else
        echo ""
        error "Playwright E2E tests failed (exit code ${exit_code})."
        exit "${exit_code}"
    fi
}

main "$@"
