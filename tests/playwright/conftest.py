"""Pytest configuration and fixtures for Task Tracker Playwright E2E tests."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Generator

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# ---------------------------------------------------------------------------
# Environment-variable driven configuration
# ---------------------------------------------------------------------------

HA_URL: str = os.environ.get("HOMEASSISTANT_URL", "http://homeassistant:8123")

HA_USERNAME: str = os.environ.get("HA_USERNAME", "admin")
HA_PASSWORD: str = os.environ.get("HA_PASSWORD", "admin")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HA_TOKEN: str | None = None


def get_ha_token() -> str:
    """Obtain a Home Assistant access token via the login flow.

    On the first call the token is fetched and cached for the remainder of
    the test session.  Retries up to 5 times with a short delay to handle
    the window immediately after HA onboarding completes.
    """
    global _HA_TOKEN  # noqa: PLW0603
    if _HA_TOKEN:
        return _HA_TOKEN

    last_exc: Exception | None = None
    for attempt in range(5):
        if attempt:
            time.sleep(5)
        try:
            session = requests.Session()

            # 1. Initiate the login flow
            flow_resp = session.post(
                f"{HA_URL}/auth/login_flow",
                json={
                    "client_id": f"{HA_URL}/",
                    "handler": ["homeassistant", None],
                    "redirect_uri": f"{HA_URL}/",
                },
                timeout=30,
            )
            flow_resp.raise_for_status()
            flow_id = flow_resp.json()["flow_id"]

            # 2. Submit credentials
            cred_resp = session.post(
                f"{HA_URL}/auth/login_flow/{flow_id}",
                json={
                    "username": HA_USERNAME,
                    "password": HA_PASSWORD,
                    "client_id": f"{HA_URL}/",
                },
                timeout=30,
            )
            cred_resp.raise_for_status()
            cred_data = cred_resp.json()
            if cred_data.get("type") != "create_entry":
                raise RuntimeError(
                    f"Login flow did not complete: type={cred_data.get('type')!r}, "
                    f"errors={cred_data.get('errors')}"
                )
            auth_code = cred_data["result"]

            # 3. Exchange code for token
            token_resp = session.post(
                f"{HA_URL}/auth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "client_id": f"{HA_URL}/",
                },
                timeout=30,
            )
            token_resp.raise_for_status()
            _HA_TOKEN = token_resp.json()["access_token"]
            return _HA_TOKEN
        except Exception as exc:  # noqa: BLE001
            last_exc = exc

    raise RuntimeError(f"Failed to obtain HA token after 5 attempts: {last_exc}") from last_exc


def wait_for_ha(timeout: int = 300) -> None:
    """Block until Home Assistant is fully started and accepts API requests.

    Polls GET /api/onboarding which requires no authentication and therefore
    cannot trigger HA's IP-ban mechanism.  The endpoint returns HTTP 200 even
    during onboarding, so it is safe to use as a startup indicator.

    A second pass waits for the integration to be loadable (the custom
    component may still be installing its requirements).
    """
    deadline = time.time() + timeout

    # Phase 1: wait for the web server to respond at all
    while time.time() < deadline:
        try:
            resp = requests.get(f"{HA_URL}/api/onboarding", timeout=5)
            if resp.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(3)
    else:
        raise RuntimeError(f"Home Assistant did not become ready within {timeout}s")

    # Phase 2: wait for the config-entries API to be usable (integrations loaded)
    # We use a small fixed delay to let HA finish loading custom components
    # after the web server is up.
    time.sleep(15)


# ---------------------------------------------------------------------------
# Session-scoped Playwright fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    """Provide a session-scoped Playwright instance."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Generator[Browser, None, None]:
    """Provide a session-scoped Chromium browser."""
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def ha_base_url() -> str:
    """Return the configured Home Assistant base URL."""
    return HA_URL


@pytest.fixture(scope="session")
def ha_token() -> str:
    """Provide a valid Home Assistant long-lived access token."""
    wait_for_ha()
    return get_ha_token()


# ---------------------------------------------------------------------------
# Per-test browser context with an authenticated HA session
# ---------------------------------------------------------------------------


@pytest.fixture()
def context(browser: Browser, ha_token: str) -> Generator[BrowserContext, None, None]:
    """Provide an authenticated browser context for Home Assistant.

    The HA frontend reads ``hassTokens`` from ``localStorage`` to determine
    whether the user is authenticated.  Using Playwright's ``storage_state``
    pre-populates ``localStorage`` *before* the first navigation, which is
    more reliable than ``add_init_script`` (the latter can lose a race with
    HA's own auth-check code and cause a redirect to ``/onboarding.html``).
    """
    hass_tokens = json.dumps({
        "access_token": ha_token,
        "token_type": "Bearer",
        "expires_in": 1800,
        "hassUrl": HA_URL,
        "clientId": f"{HA_URL}/",
        "expires": int(time.time() * 1000) + 1_800_000,
        "refresh_token": "",
    })
    ctx = browser.new_context(
        base_url=HA_URL,
        storage_state={
            "cookies": [],
            "origins": [
                {
                    "origin": HA_URL,
                    "localStorage": [
                        {"name": "hassTokens", "value": hass_tokens},
                    ],
                }
            ],
        },
    )
    yield ctx
    ctx.close()


@pytest.fixture()
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Provide a fresh page within the authenticated browser context."""
    pg = context.new_page()
    yield pg
    pg.close()


# ---------------------------------------------------------------------------
# HA REST API session fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def ha_api(ha_token: str) -> requests.Session:
    """Return a requests Session pre-configured to call the HA REST API."""
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {ha_token}"
    session.headers["Content-Type"] = "application/json"
    return session


# ---------------------------------------------------------------------------
# Integration setup / teardown helpers
# ---------------------------------------------------------------------------


def _get_task_tracker_entry_ids(ha_api: requests.Session) -> set[str]:
    """Return the set of current task_tracker config-entry IDs."""
    resp = ha_api.get(f"{HA_URL}/api/config/config_entries/entry")
    resp.raise_for_status()
    return {e["entry_id"] for e in resp.json() if e.get("domain") == "task_tracker"}


def _add_integration(
    ha_api: requests.Session,
    name: str = "Playwright Test Task",
    interval_value: int = 7,
    interval_type: str = "day",
) -> dict:
    """Add a Task Tracker config entry via the config flow.

    Returns the completed flow response dict (``type == "create_entry"``).
    Raises if the flow does not complete successfully.
    """
    # Step 1: Start the config flow
    flow_resp = ha_api.post(
        f"{HA_URL}/api/config/config_entries/flow",
        json={"handler": "task_tracker"},
    )
    flow_resp.raise_for_status()
    flow_data = flow_resp.json()
    assert flow_data.get("type") == "form", (
        f"Expected config flow to present a form, got: {flow_data.get('type')!r}"
    )
    flow_id = flow_data["flow_id"]

    # Step 2: Submit the user data
    submit_resp = ha_api.post(
        f"{HA_URL}/api/config/config_entries/flow/{flow_id}",
        json={
            "name": name,
            "task_interval_value": interval_value,
            "task_interval_type": interval_type,
        },
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    assert result.get("type") == "create_entry", (
        f"Expected flow to complete with 'create_entry', got: {result.get('type')!r}"
    )
    return result


def _remove_all_task_tracker_entries(ha_api: requests.Session) -> None:
    """Delete every task_tracker config entry from Home Assistant."""
    for entry_id in _get_task_tracker_entry_ids(ha_api):
        ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{entry_id}")


def call_service(ha_api: requests.Session, service: str, payload: dict) -> requests.Response:
    """POST to a task_tracker service and return the raw response."""
    return ha_api.post(
        f"{HA_URL}/api/services/task_tracker/{service}",
        json=payload,
    )


def get_sensor_state(ha_api: requests.Session, entity_id: str) -> dict:
    """Return the full state object for *entity_id*."""
    resp = ha_api.get(f"{HA_URL}/api/states/{entity_id}")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# ensure_integration fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def ensure_integration(ha_api: requests.Session) -> Generator[dict[str, Any], None, None]:
    """Ensure one Task Tracker integration entry is configured before a test runs.

    Yields a dict with ``entry_id``, ``entity_id``, and ``name``.

    After the test the environment is restored to its exact pre-test state:
    any entries added during the test (including the one created by this
    fixture) are removed so subsequent tests start from the same baseline.
    """
    # Snapshot entries before the test
    entries_before = _get_task_tracker_entry_ids(ha_api)

    # Create a fresh test entry
    result = _add_integration(ha_api)
    entry_id: str = result["entry_id"]

    # Wait for the entity to appear in HA's state machine
    entity_id: str | None = None
    deadline = time.time() + 30
    while time.time() < deadline:
        resp = ha_api.get(f"{HA_URL}/api/states")
        resp.raise_for_status()
        for state in resp.json():
            if state["entity_id"].startswith("sensor.task_tracker_"):
                entity_id = state["entity_id"]
                break
        if entity_id:
            break
        time.sleep(1)

    yield {"entry_id": entry_id, "entity_id": entity_id, "name": "Playwright Test Task"}

    # --- Teardown: remove all entries that were added during the test ---
    entries_after = _get_task_tracker_entry_ids(ha_api)
    for eid in entries_after - entries_before:
        ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")
