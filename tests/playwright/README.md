# Task Tracker – Playwright End-to-End Tests

This directory contains end-to-end (E2E) tests for the **Task Tracker** Home
Assistant custom component.  The tests run against a real Home Assistant
instance using [Playwright](https://playwright.dev/python/) and the HA REST
API.

---

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.12 or later |
| Home Assistant | A running instance (local or Docker) |
| Task Tracker | Installed in the HA instance |
| Long-lived access token | Generated in HA → Profile → Long-Lived Access Tokens |

---

## Quick start

### 1. Install dependencies

```bash
pip install -r tests/playwright/requirements.txt
playwright install chromium
```

### 2. Configure environment variables

```bash
export HOMEASSISTANT_URL="http://localhost:8123"   # default
export HA_TOKEN="<your long-lived access token>"
```

### 3. Start Home Assistant (Docker)

If you don't already have a running HA instance you can use the provided
`docker-compose.yaml` from the repo root:

```bash
docker-compose up -d homeassistant
# Wait until HA is fully started (check http://localhost:8123)
```

Then install the Task Tracker integration:

1. Copy (or symlink) the repository root into
   `<ha-config-dir>/custom_components/task_tracker`.
2. Add `task_tracker:` to `configuration.yaml`.
3. Restart Home Assistant.
4. Generate a long-lived access token and set `HA_TOKEN`.

### 4. Run the tests

```bash
# All Playwright tests
pytest tests/playwright/ -v

# A single file
pytest tests/playwright/test_services.py -v

# A single test
pytest tests/playwright/test_services.py::TestServices::test_mark_as_done_sets_state_to_done -v
```

---

## Test files

| File | What it tests |
|---|---|
| `conftest.py` | Shared fixtures (HA connection, auth, integration lifecycle) |
| `test_integration_setup.py` | Config flow – adding / removing integrations |
| `test_sensors.py` | Sensor state and attribute validation |
| `test_buttons.py` | Button entity creation and press functionality |
| `test_frontend.py` | Frontend card/panel and developer-tools UI |
| `test_services.py` | `mark_as_done` and `set_last_done_date` service calls |

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOMEASSISTANT_URL` | `http://localhost:8123` | Base URL of the HA instance |
| `HA_TOKEN` | *(empty)* | Long-lived access token for the HA REST API |

---

## Notes

* Tests are **idempotent** – each test that creates a config entry cleans it up
  in teardown.
* Browser tests use a shared Chromium context with the HA token injected into
  `localStorage` so no manual login is required.
* Tests that rely purely on the REST API (no browser) still live in this
  directory because they test the same integration endpoints as the UI tests.
* Service-error tests deliberately pass invalid entity IDs to verify that HA
  returns an appropriate error response; these tests do **not** depend on the
  `task_tracker_entry` fixture.
