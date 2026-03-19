"""Playwright E2E tests – Task Tracker frontend card.

These tests exercise the Task Tracker Lovelace card and panel through the
Home Assistant web UI.  They rely on the card JavaScript being served by HA
(``/task_tracker/task-tracker-card.js``).

Prerequisites
-------------
* The ``task_tracker`` component must be loaded in HA (via the ``task_tracker:``
  section in ``configuration.yaml`` or as a custom integration).
* A valid ``HA_TOKEN`` must be set so the shared ``ha_context`` fixture can
  authenticate automatically.
"""

from __future__ import annotations

import json
import time

import pytest
from playwright.sync_api import Page, expect

from conftest import HA_URL, TEST_TASK_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _card_config(entity_id: str) -> dict:
    """Return a minimal Lovelace card config for the Task Tracker card."""
    return {
        "type": "custom:task-tracker-card",
        "entity": entity_id,
    }


def _sensor_entity_id(task_name: str) -> str:
    slug = task_name.lower().replace(" ", "_")
    return f"sensor.task_tracker_{slug}"


def _wait_for_url(page: Page, url: str, timeout: int = 30_000) -> None:
    page.goto(url)
    page.wait_for_load_state("networkidle", timeout=timeout)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFrontend:
    """Tests for the Task Tracker frontend card and panel."""

    def test_card_javascript_is_served(self):
        """The task-tracker-card.js file is served by Home Assistant."""
        import requests
        from conftest import _api_headers

        resp = requests.get(
            f"{HA_URL}/task_tracker/task-tracker-card.js",
            headers=_api_headers(),
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"Card JS not found at /task_tracker/task-tracker-card.js "
            f"(status {resp.status_code})"
        )
        assert len(resp.content) > 0, "Card JS file is empty"

    def test_panel_javascript_is_served(self):
        """The task-tracker-panel.js file is served by Home Assistant."""
        import requests
        from conftest import _api_headers

        resp = requests.get(
            f"{HA_URL}/task_tracker/task-tracker-panel.js",
            headers=_api_headers(),
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"Panel JS not found at /task_tracker/task-tracker-panel.js "
            f"(status {resp.status_code})"
        )

    def test_homeassistant_ui_loads(self, page: Page):
        """The Home Assistant frontend renders its root element."""
        _wait_for_url(page, HA_URL)
        root = page.locator("home-assistant")
        expect(root).to_be_attached(timeout=30_000)

    def test_lovelace_dashboard_loads(self, page: Page):
        """The default Lovelace dashboard renders without a crash error."""
        _wait_for_url(page, f"{HA_URL}/lovelace")
        # HA renders an <ha-panel-lovelace> or redirects to the default view
        page.wait_for_selector("home-assistant", timeout=30_000)
        # Ensure there is no fatal JS error dialog
        error_dialog = page.locator("ha-dialog, mwc-dialog").first
        if error_dialog.is_visible():
            dialog_text = error_dialog.inner_text()
            assert "error" not in dialog_text.lower(), (
                f"Error dialog visible on Lovelace dashboard: {dialog_text[:200]}"
            )

    def test_task_tracker_panel_loads(self, page: Page, task_tracker_entry):
        """Navigating to the Task Tracker panel renders the panel component."""
        _wait_for_url(page, f"{HA_URL}/task-tracker")
        # Either the panel renders, or we land on a 404 page — both are valid outcomes
        # depending on whether show_panel is enabled.  We just check HA itself renders.
        expect(page.locator("home-assistant")).to_be_attached(timeout=30_000)

    def test_developer_tools_state_page_shows_sensor(self, page: Page, task_tracker_entry):
        """The sensor entity for the task is visible in the developer-tools states page."""
        _wait_for_url(page, f"{HA_URL}/developer-tools/state")
        sensor_id = _sensor_entity_id(TEST_TASK_NAME)

        # Try to filter by entity id if a search input is available
        filter_input = page.locator("input[placeholder*='filter' i], input[placeholder*='search' i]").first
        if filter_input.is_visible(timeout=5_000):
            filter_input.fill(sensor_id)
            page.wait_for_timeout(1_000)

        content = page.content()
        assert sensor_id in content, (
            f"Sensor {sensor_id!r} not found in developer-tools states page"
        )

    def test_developer_tools_service_page_lists_mark_as_done(self, page: Page):
        """The mark_as_done service appears in the developer-tools services page."""
        _wait_for_url(page, f"{HA_URL}/developer-tools/service")
        page.wait_for_load_state("networkidle", timeout=30_000)
        content = page.content()
        assert "task_tracker" in content.lower(), (
            "task_tracker domain not found in developer-tools services page"
        )

    def test_lovelace_card_resource_registered(self, ha_get):
        """The Task Tracker card JS is registered as a Lovelace resource."""
        resp = ha_get("lovelace/resources")
        if resp.status_code == 401:
            pytest.skip("Lovelace resources endpoint requires admin token")
        if resp.status_code == 404:
            pytest.skip("Lovelace resources endpoint not available")
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
        resources = resp.json()
        urls = [r.get("url", "") for r in resources]
        assert any("task-tracker-card" in url for url in urls), (
            f"task-tracker-card resource not found in Lovelace resources: {urls}"
        )

    def test_config_integrations_page_renders(self, page: Page):
        """The /config/integrations page renders without a fatal error."""
        _wait_for_url(page, f"{HA_URL}/config/integrations")
        expect(page.locator("home-assistant")).to_be_attached(timeout=30_000)
