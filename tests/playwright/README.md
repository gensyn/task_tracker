# Task Tracker Playwright E2E Tests

End-to-end tests for the **Task Tracker** Home Assistant custom component using
[Playwright](https://playwright.dev/python/).

## Running with Docker (recommended)

The repository ships a `docker-compose.yaml` that starts Home Assistant and a
self-contained Playwright test-runner — no local Python environment or browser
installation required.

```bash
# From the repository root:

# First run: build the images (only needed once, or after code changes)
docker compose build

# Run the full E2E suite
docker compose run --rm playwright-tests

# Stop background services and remove volumes when done
docker compose down -v
```

On the **first run** the test-runner container automatically creates the HA
admin user via the onboarding API, so no manual UI interaction is needed.

Test results (JUnit XML) are written to `playwright-results/` in the repository
root and can be used by CI or inspected locally.

## Running as a script

Use the dedicated helper script to build, run, and tear down everything in one
command:

```bash
./run_playwright_tests.sh
```

## Running without Docker (advanced)

If you prefer to run outside the container (e.g. against a pre-existing HA
instance), install dependencies on the host and point the env vars at your
services:

```bash
# Install dependencies
pip install -r tests/playwright/requirements.txt
playwright install chromium

# Point at your HA instance
export HOMEASSISTANT_URL=http://localhost:8123
export HA_USERNAME=admin
export HA_PASSWORD=admin

pytest tests/playwright/ -v
```

## GitHub Actions

The `.github/workflows/playwright-tests.yml` workflow is triggered **manually
only** (`workflow_dispatch`).  It builds the images, calls
`docker compose run playwright-tests`, and uploads `playwright-results/junit.xml`
as a workflow artifact.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOMEASSISTANT_URL` | `http://homeassistant:8123` | Home Assistant base URL |
| `HA_USERNAME` | `admin` | Home Assistant admin username |
| `HA_PASSWORD` | `admin` | Home Assistant admin password |

## Docker image layout

| File | Purpose |
|---|---|
| `Dockerfile` | Playwright test-runner (Python 3.12 + Chromium) |
| `entrypoint.sh` | Container startup: wait for HA → onboard → run pytest |
| `ha-init-wrapper.sh` | HA container entrypoint wrapper |
| `docker-compose.yaml` | (repo root) Orchestrates HA and the test runner |

## Test Modules

| File | What it tests |
|---|---|
| `test_integration_setup.py` | Add/remove integration lifecycle, multiple entries |
| `test_services.py` | The `mark_as_done` and `set_last_done_date` HA services |
| `test_frontend.py` | Home Assistant frontend pages and UI interactions |
| `test_configuration.py` | Configuration options (intervals, states, multiple tasks) |
| `test_security.py` | Security properties (auth validation, input validation) |

## Fixtures (`conftest.py`)

| Fixture | Scope | Description |
|---|---|---|
| `playwright_instance` | session | Playwright instance |
| `browser` | session | Headless Chromium browser |
| `ha_base_url` | session | Configured HA URL |
| `ha_token` | session | Long-lived HA access token |
| `context` | function | Authenticated browser context |
| `page` | function | Fresh page within the authenticated context |
| `ha_api` | function | `requests.Session` for the HA REST API |
| `ensure_integration` | function | Creates a Task Tracker entry; fully restores state after test |

## Notes

- Tests are **idempotent** – each test cleans up after itself.
- Tests do **not** depend on each other.
- Browser-based tests use a headless Chromium instance.
- API-based tests call Home Assistant's REST API directly for speed.
- Task Tracker has **no external service dependencies** — no SSH servers or
  Docker-in-Docker is required.
