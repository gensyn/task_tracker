"""Playwright E2E tests – Task Tracker integration setup.

These tests verify that the Task Tracker integration can be added and removed
through the Home Assistant UI config flow.
"""

from __future__ import annotations

import time

import pytest
import requests
from playwright.sync_api import Page, expect

from conftest import HA_URL, INTEGRATION_DOMAIN, TEST_TASK_NAME, _api_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _delete_entry(entry_id: str) -> None:
    """Delete a config entry via the REST API (best-effort)."""
    requests.delete(
        f"{HA_URL}/api/config/config_entries/{entry_id}",
        headers=_api_headers(),
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIntegrationSetup:
    """Tests for adding and configuring the Task Tracker integration."""

    def test_integration_api_flow_create_entry(self, ha_post, ha_get):
        """Adding a Task Tracker entry via the config-entries REST API succeeds.

        This exercises the full config flow (start flow → submit user form →
        confirm the resulting entry) without a browser.
        """
        # Start the config flow
        resp = ha_post(
            "config/config_entries/flow",
            json={"handler": INTEGRATION_DOMAIN},
        )
        assert resp.status_code in (200, 201), f"Could not start config flow: {resp.text}"
        flow = resp.json()
        assert flow.get("step_id") == "user", f"Expected 'user' step, got: {flow}"
        flow_id = flow["flow_id"]

        # Submit the user step
        resp = ha_post(
            f"config/config_entries/flow/{flow_id}",
            json={
                "name": f"{TEST_TASK_NAME}_setup_test",
                "task_interval_value": 7,
                "task_interval_type": "day",
            },
        )
        assert resp.status_code in (200, 201), f"Config flow submission failed: {resp.text}"
        result = resp.json()
        assert result.get("type") == "create_entry", f"Expected 'create_entry' result, got: {result}"
        assert result.get("title"), "Config entry title should not be empty"
        entry_id = result["entry_id"]

        # Verify the entry exists
        entries_resp = ha_get("config/config_entries")
        assert entries_resp.status_code == 200
        entry_ids = [e["entry_id"] for e in entries_resp.json()]
        assert entry_id in entry_ids, "Newly created entry not found in config entries list"

        # Cleanup
        _delete_entry(entry_id)

    def test_integration_appears_in_config_entries(self, task_tracker_entry, ha_get):
        """After setup, the entry appears in the config-entries list with the correct domain."""
        resp = ha_get("config/config_entries")
        assert resp.status_code == 200
        entries = resp.json()

        matching = [e for e in entries if e["entry_id"] == task_tracker_entry]
        assert len(matching) == 1, "Expected exactly one matching config entry"
        entry = matching[0]
        assert entry["domain"] == INTEGRATION_DOMAIN
        assert entry["state"] == "loaded", f"Entry state should be 'loaded', got: {entry['state']}"

    def test_integration_delete(self, ha_post, ha_get):
        """A Task Tracker config entry can be deleted via the REST API."""
        # Create a temporary entry
        resp = ha_post(
            "config/config_entries/flow",
            json={"handler": INTEGRATION_DOMAIN},
        )
        assert resp.status_code in (200, 201)
        flow_id = resp.json()["flow_id"]

        resp = ha_post(
            f"config/config_entries/flow/{flow_id}",
            json={
                "name": f"{TEST_TASK_NAME}_delete_test",
                "task_interval_value": 3,
                "task_interval_type": "day",
            },
        )
        assert resp.status_code in (200, 201)
        entry_id = resp.json()["entry_id"]

        # Delete it
        del_resp = requests.delete(
            f"{HA_URL}/api/config/config_entries/{entry_id}",
            headers=_api_headers(),
            timeout=10,
        )
        assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"

        # Verify it's gone
        entries_resp = ha_get("config/config_entries")
        assert entries_resp.status_code == 200
        entry_ids = [e["entry_id"] for e in entries_resp.json()]
        assert entry_id not in entry_ids, "Deleted entry should not appear in config entries"

    def test_duplicate_name_is_rejected(self, ha_post, task_tracker_entry):
        """The config flow should reject a second entry with an identical task name."""
        # Try to create a flow with the same name as the existing fixture entry
        resp = ha_post(
            "config/config_entries/flow",
            json={"handler": INTEGRATION_DOMAIN},
        )
        assert resp.status_code in (200, 201)
        flow_id = resp.json()["flow_id"]

        resp = ha_post(
            f"config/config_entries/flow/{flow_id}",
            json={
                "name": TEST_TASK_NAME,
                "task_interval_value": 7,
                "task_interval_type": "day",
            },
        )
        # HA either returns an error step or a 400/409 status
        if resp.status_code in (200, 201):
            result = resp.json()
            assert result.get("type") in ("abort", "form"), (
                f"Expected flow abort or error form for duplicate name, got: {result}"
            )
        else:
            assert resp.status_code in (400, 409), (
                f"Expected 4xx for duplicate name, got {resp.status_code}: {resp.text}"
            )

    def test_ui_integrations_page_loads(self, page: Page):
        """The Home Assistant integrations page renders without errors."""
        page.goto(f"{HA_URL}/config/integrations")
        # HA renders a <home-assistant> root element
        expect(page.locator("home-assistant")).to_be_visible(timeout=30_000)

    def test_ui_integration_visible_after_setup(self, page: Page, task_tracker_entry):
        """After adding the integration, it appears somewhere on the integrations page."""
        page.goto(f"{HA_URL}/config/integrations")
        # Wait for content to render
        page.wait_for_load_state("networkidle", timeout=30_000)
        # The integration card title or domain should appear on the page
        content = page.content()
        assert "task_tracker" in content.lower() or "task tracker" in content.lower(), (
            "Task Tracker integration not visible on the integrations page"
        )
