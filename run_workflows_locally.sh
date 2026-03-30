#!/usr/bin/env bash
# run_workflows_locally.sh
#
# Runs the CI workflows (tests and linting) in this repository locally using
# Docker and act (https://github.com/nektos/act).
#
# Both tools are installed automatically if they are not already present.
#
# Workflows that depend on GitHub infrastructure (hassfest, HACS validation,
# release) are silently skipped as they cannot run meaningfully offline.
#
# Usage:
#   ./run_workflows_locally.sh

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

command_exists() { command -v "$1" &>/dev/null; }

# ── Docker installation / update ─────────────────────────────────────────────
install_docker() {
    if command_exists docker; then
        info "Docker is already installed: $(sudo docker --version)"
        info "Checking for Docker updates…"
        if command_exists apt-get; then
            sudo apt-get update -qq \
                && sudo apt-get install --only-upgrade -y \
                    docker-ce docker-ce-cli containerd.io docker-compose-plugin \
                || true
        elif command_exists yum; then
            sudo yum update -y \
                docker-ce docker-ce-cli containerd.io docker-compose-plugin \
                || true
        else
            warn "Cannot automatically update Docker on this platform; please update it manually."
        fi
        info "Docker version after update check: $(sudo docker --version)"
        return 0
    fi

    header "Installing Docker…"
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
    warn "Docker installed. You may need to run 'newgrp docker' or re-login for group membership to take effect."
}

# ── act installation / update ─────────────────────────────────────────────────
install_act() {
    if command_exists act; then
        local current_version latest_version
        current_version="$(act --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
        latest_version="$(curl -fsSL https://api.github.com/repos/nektos/act/releases/latest 2>/dev/null \
            | grep '"tag_name"' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"

        if [[ -z "$current_version" ]] || [[ -z "$latest_version" ]]; then
            warn "Could not determine act versions; skipping update check."
            info "act is already installed: $(act --version)"
            return 0
        fi

        if [[ "$current_version" == "$latest_version" ]]; then
            info "act is already up to date: $(act --version)"
            return 0
        fi

        header "Updating act from ${current_version} to ${latest_version}…"
        curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh \
            | sudo bash -s -- -b /usr/local/bin
        return 0
    fi

    header "Installing act…"
    curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh \
        | sudo bash -s -- -b /usr/local/bin
}

# ── Docker daemon check ───────────────────────────────────────────────────────
ensure_docker_running() {
    if sudo docker info &>/dev/null; then
        return 0
    fi

    warn "Docker daemon is not running – attempting to start it…"
    if command_exists systemctl; then
        sudo systemctl start docker
    else
        sudo service docker start
    fi
    sleep 3

    if ! sudo docker info &>/dev/null; then
        error "Docker daemon is still not running. Please start Docker manually and re-run this script."
        exit 1
    fi
}

# ── Workflow runner ───────────────────────────────────────────────────────────

# Ubuntu runner image used by act.  The "act-latest" tag is a medium-sized
# image that supports most common Actions without requiring the 20 GB+ full
# image.
ACT_IMAGE="catthehacker/ubuntu:act-latest"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOWS_DIR="$SCRIPT_DIR/.github/workflows"

# run_workflow <workflow-file> <event>
# Returns 0 on success, 1 on failure.
run_workflow() {
    local workflow_file="$1"
    local event="$2"
    local name
    name="$(basename "$workflow_file")"

    info "Running [$name] with event '$event'…"

    if sudo act "$event" \
        -W "$workflow_file" \
        -P "ubuntu-latest=$ACT_IMAGE" \
        --rm \
        2>&1; then
        success "$name passed"
        return 0
    else
        error "$name failed"
        return 1
    fi
}

# ── Playwright E2E tests via docker compose ───────────────────────────────────
# The playwright-tests.yml workflow uses `docker compose run` internally, which
# requires a real Docker daemon.  act (Docker-in-Docker) cannot reliably run
# that workflow, so we delegate to the dedicated run_playwright_tests.sh script.
run_playwright_tests() {
    local script="$SCRIPT_DIR/run_playwright_tests.sh"

    if [[ ! -f "$script" ]]; then
        warn "run_playwright_tests.sh not found – skipping Playwright E2E tests."
        return 1
    fi

    if bash "$script"; then
        success "playwright-tests.yml passed"
        return 0
    else
        error "playwright-tests.yml failed"
        return 1
    fi
}

run_all_workflows() {
    # Only act-compatible workflows (no Docker-in-Docker requirement).
    # Workflows that depend on GitHub infrastructure (hassfest, HACS validation,
    # release) are silently omitted.
    local workflow_files=(
        "test.yml"
        "pylint.yml"
        "integration-tests.yml"
    )
    local workflow_events=(
        "push"
        "push"
        "push"
    )

    local passed=()
    local failed=()

    local i
    for i in "${!workflow_files[@]}"; do
        local workflow="${workflow_files[$i]}"
        local event="${workflow_events[$i]}"
        local workflow_path="$WORKFLOWS_DIR/$workflow"

        if [[ ! -f "$workflow_path" ]]; then
            warn "Workflow file not found, skipping: $workflow"
            continue
        fi

        if run_workflow "$workflow_path" "$event"; then
            passed+=("$workflow")
        else
            failed+=("$workflow")
        fi
    done

    # ── Playwright E2E tests (docker compose, not act) ────────────────────────
    if run_playwright_tests; then
        passed+=("playwright-tests.yml")
    else
        failed+=("playwright-tests.yml")
    fi

    # ── Summary ───────────────────────────────────────────────────────────────
    header "══════════════════════════════════════════════"
    header " Results"
    header "══════════════════════════════════════════════"

    if [[ ${#passed[@]} -gt 0 ]]; then
        success "Passed  (${#passed[@]}): ${passed[*]}"
    fi
    if [[ ${#failed[@]} -gt 0 ]]; then
        error   "Failed  (${#failed[@]}): ${failed[*]}"
        return 1
    fi

    echo ""
    success "All workflows completed successfully."
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    if [[ $# -gt 0 ]]; then
        error "This script takes no arguments."
        echo "Usage: $0"
        exit 1
    fi

    header "════════════════════════════════════════════════════"
    header " Running GitHub Actions workflows locally with act"
    header "════════════════════════════════════════════════════"

    install_docker
    install_act
    ensure_docker_running
    run_all_workflows
}

main "$@"
