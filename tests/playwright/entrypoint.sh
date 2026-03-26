#!/usr/bin/env bash
# entrypoint.sh — startup script for the Playwright E2E test-runner container.
#
# 1. Waits for Home Assistant to become reachable.
# 2. Runs the full HA onboarding flow to create the admin user and complete all
#    onboarding steps (if they haven't been completed yet).
# 3. Hands off to pytest.

set -euo pipefail

HA_URL="${HOMEASSISTANT_URL:-http://homeassistant:8123}"
HA_USER="${HA_USERNAME:-admin}"
HA_PASS="${HA_PASSWORD:-admin}"
RESULTS_DIR="/app/playwright-results"

log() { echo "[entrypoint] $*"; }

mkdir -p "${RESULTS_DIR}"

# ── 1. Wait for Home Assistant to respond ────────────────────────────────────
log "Waiting for Home Assistant at ${HA_URL} …"
ATTEMPT=0
MAX_ATTEMPTS=120
until HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${HA_URL}/api/onboarding" 2>/dev/null) && \
      [[ "${HTTP}" =~ ^[2-4][0-9]{2}$ ]]; do
    ATTEMPT=$(( ATTEMPT + 1 ))
    if [[ "${ATTEMPT}" -ge "${MAX_ATTEMPTS}" ]]; then
        log "ERROR: Home Assistant did not become ready after ${MAX_ATTEMPTS} attempts."
        exit 1
    fi
    log "  Attempt ${ATTEMPT}/${MAX_ATTEMPTS} (HTTP ${HTTP:-000}), retrying in 5 s …"
    sleep 5
done
log "Home Assistant is responding."

# ── 2. Onboarding (complete all steps on first start) ─────────────────────────
ONBOARDING=$(curl -sf "${HA_URL}/api/onboarding" 2>/dev/null || echo '[]')

# Check whether the "user" step is already done.
USER_DONE=$(_ONBOARDING="${ONBOARDING}" python3 - <<'PYEOF'
import json, os, sys
try:
    data = json.loads(os.environ.get("_ONBOARDING", "[]"))
    if not isinstance(data, list):
        raise ValueError("unexpected onboarding format")
    print("true" if any(s.get("step") == "user" and s.get("done") for s in data) else "false")
except Exception as e:
    # Unknown format – assume NOT done so we attempt onboarding
    print("false")
PYEOF
)

if [[ "${USER_DONE}" == "false" ]]; then
    log "Running HA onboarding — creating admin user '${HA_USER}' …"

    # Step 1: Create user; returns {"auth_code": "...", "client_id": "..."}
    PAYLOAD="{\"client_id\":\"${HA_URL}/\",\"name\":\"Admin\",\"username\":\"${HA_USER}\",\"password\":\"${HA_PASS}\",\"language\":\"en\"}"
    USER_RESPONSE=$(curl -sf -X POST "${HA_URL}/api/onboarding/users" \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" 2>&1) || {
        log "WARNING: Onboarding/users request failed. HA may already be fully onboarded."
        USER_RESPONSE=""
    }

    if [[ -n "${USER_RESPONSE}" ]]; then
        # Step 2: Exchange the auth_code for a bearer token
        AUTH_TOKEN=$(_RESP="${USER_RESPONSE}" HA_URL="${HA_URL}" python3 - <<'PYEOF'
import json, os, sys, urllib.request, urllib.parse

resp = os.environ.get("_RESP", "")
ha_url = os.environ.get("HA_URL", "")

try:
    auth_code = json.loads(resp)["auth_code"]
except Exception as e:
    print("")
    sys.exit(0)

data = urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "code": auth_code,
    "client_id": ha_url + "/",
}).encode()
req = urllib.request.Request(f"{ha_url}/auth/token", data=data,
                              method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(json.loads(r.read())["access_token"])
except Exception as e:
    print("")
PYEOF
        )

        if [[ -n "${AUTH_TOKEN}" ]]; then
            # Step 3: Complete remaining onboarding steps with the new token
            for STEP in core_config analytics integration; do
                log "  Completing onboarding step: ${STEP} …"
                curl -sf -X POST "${HA_URL}/api/onboarding/${STEP}" \
                    -H "Authorization: Bearer ${AUTH_TOKEN}" \
                    -H "Content-Type: application/json" \
                    -d '{}' > /dev/null 2>&1 || \
                    log "  WARNING: step '${STEP}' returned an error (may be harmless)."
            done
        fi
    fi

    log "Onboarding complete."
    # Give HA a moment to settle after onboarding
    sleep 10
fi

# ── 3. Run the test suite ─────────────────────────────────────────────────────
log "Starting Playwright E2E test suite …"

# Run from tests/playwright/ so pytest does not traverse up into the HA
# component package (which would try to import voluptuous etc.).
cd /app/tests/playwright
exec pytest . \
    --tb=short \
    -v \
    --junitxml="${RESULTS_DIR}/junit.xml" \
    "$@"
