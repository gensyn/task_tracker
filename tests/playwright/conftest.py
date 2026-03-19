"""Shared fixtures for Task Tracker Playwright end-to-end tests.

These tests target a *running* Home Assistant instance.  Configure it via
environment variables before running:

    HOMEASSISTANT_URL   Base URL of the HA instance (default: http://localhost:8123)
    HA_TOKEN            Long-lived access token for the HA REST API
"""

from __future__ import annotations

import os
import time
from typing import Generator

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

HA_URL: str = os.environ.get("HOMEASSISTANT_URL", "http://localhost:8123").rstrip("/")
HA_TOKEN: str = os.environ.get("HA_TOKEN", "")

INTEGRATION_DOMAIN: str = "task_tracker"
TEST_TASK_NAME: str = "playwright_test_task"


def _api_headers() -> dict[str, str]:
    """Return HTTP headers with the Bearer token."""
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def _wait_for_ha(timeout: int = 60) -> None:
    """Block until Home Assistant responds or *timeout* seconds have elapsed."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"{HA_URL}/api/", headers=_api_headers(), timeout=5)
            if resp.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"Home Assistant at {HA_URL} did not become ready within {timeout}s")


# ---------------------------------------------------------------------------
# Session-scoped browser
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_api_headers() -> dict[str, str]:
    """Return the API headers for direct REST calls."""
    return _api_headers()


@pytest.fixture(scope="session", autouse=True)
def wait_for_homeassistant() -> None:
    """Ensure HA is reachable before any test runs."""
    _wait_for_ha()


@pytest.fixture(scope="session")
def browser_instance(playwright: Playwright) -> Generator[Browser, None, None]:
    """Launch a single Chromium browser for the entire test session."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def ha_context(browser_instance: Browser) -> Generator[BrowserContext, None, None]:
    """Browser context that is pre-authenticated with Home Assistant.

    Authentication is performed via the HA REST API; the resulting token is
    injected into localStorage so Playwright pages are immediately logged in.
    """
    context = browser_instance.new_context(base_url=HA_URL)

    # Inject the long-lived access token into localStorage so the frontend
    # considers the browser already logged in.
    if HA_TOKEN:
        context.add_init_script(
            f"""
            window.addEventListener('load', () => {{
                const token = {{
                    access_token: '{HA_TOKEN}',
                    token_type: 'Bearer',
                    expires_in: 1800,
                    refresh_token: '',
                    expires: Date.now() + 1800000,
                }};
                localStorage.setItem(
                    'hassTokens',
                    JSON.stringify(token)
                );
            }});
            """
        )

    yield context
    context.close()


@pytest.fixture
def page(ha_context: BrowserContext) -> Generator[Page, None, None]:
    """Open a new page in the shared HA browser context."""
    p = ha_context.new_page()
    yield p
    p.close()


# ---------------------------------------------------------------------------
# API helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_get(ha_api_headers: dict[str, str]):
    """Return a helper that performs an authenticated GET against the HA REST API."""

    def _get(path: str, **kwargs) -> requests.Response:
        return requests.get(f"{HA_URL}/api/{path.lstrip('/')}", headers=ha_api_headers, timeout=10, **kwargs)

    return _get


@pytest.fixture(scope="session")
def ha_post(ha_api_headers: dict[str, str]):
    """Return a helper that performs an authenticated POST against the HA REST API."""

    def _post(path: str, json: dict | None = None, **kwargs) -> requests.Response:
        return requests.post(
            f"{HA_URL}/api/{path.lstrip('/')}",
            headers=ha_api_headers,
            json=json,
            timeout=10,
            **kwargs,
        )

    return _post


@pytest.fixture(scope="session")
def call_service(ha_post):
    """Return a helper that calls an HA service via the REST API."""

    def _call(domain: str, service: str, service_data: dict | None = None) -> requests.Response:
        return ha_post(
            f"services/{domain}/{service}",
            json=service_data or {},
        )

    return _call


# ---------------------------------------------------------------------------
# Integration lifecycle fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def task_tracker_entry(ha_post, ha_get, call_service):
    """Create a Task Tracker config entry via the HA config-entries/flow API.

    Yields the ``entry_id`` of the created entry, then deletes it on teardown.
    """
    # Step 1 – initiate the config flow
    resp = ha_post(
        "config/config_entries/flow",
        json={"handler": INTEGRATION_DOMAIN},
    )
    assert resp.status_code in (200, 201), f"Failed to start config flow: {resp.text}"
    flow = resp.json()
    flow_id = flow["flow_id"]

    # Step 2 – submit the user form
    resp = ha_post(
        f"config/config_entries/flow/{flow_id}",
        json={
            "name": TEST_TASK_NAME,
            "task_interval_value": 7,
            "task_interval_type": "day",
        },
    )
    assert resp.status_code in (200, 201), f"Failed to submit config flow: {resp.text}"
    result = resp.json()
    assert result.get("type") == "create_entry", f"Unexpected flow result: {result}"
    entry_id = result["entry_id"]

    yield entry_id

    # Teardown – remove the config entry
    requests.delete(
        f"{HA_URL}/api/config/config_entries/{entry_id}",
        headers=_api_headers(),
        timeout=10,
    )
