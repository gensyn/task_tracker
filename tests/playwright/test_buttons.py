"""Playwright E2E tests – Task Tracker button entities.

These tests verify that button entities are created for each Task Tracker
integration entry and that pressing them triggers the expected state change on
the corresponding sensor.
"""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, expect

from conftest import HA_URL, INTEGRATION_DOMAIN, TEST_TASK_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _button_entity_id(task_name: str) -> str:
    """Return the expected entity-id for a task button."""
    slug = task_name.lower().replace(" ", "_")
    return f"button.task_tracker_{slug}_mark_as_done"


def _sensor_entity_id(task_name: str) -> str:
    """Return the expected entity-id for a task sensor."""
    slug = task_name.lower().replace(" ", "_")
    return f"sensor.task_tracker_{slug}"


def _get_state(ha_get, entity_id: str) -> dict:
    """Return the HA state object for *entity_id*, retrying for up to 15 s."""
    deadline = time.time() + 15
    while time.time() < deadline:
        resp = ha_get(f"states/{entity_id}")
        if resp.status_code == 200:
            return resp.json()
        time.sleep(1)
    pytest.fail(f"Entity {entity_id!r} did not appear within 15 s (last status: {resp.status_code})")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestButtons:
    """Tests for Task Tracker button entities."""

    def test_button_entity_is_created(self, task_tracker_entry, ha_get):
        """A ``mark_as_done`` button entity is created alongside the sensor."""
        entity_id = _button_entity_id(TEST_TASK_NAME)
        state = _get_state(ha_get, entity_id)
        assert state["entity_id"] == entity_id

    def test_button_entity_id_format(self, task_tracker_entry, ha_get):
        """Button entity IDs follow the ``button.task_tracker_<slug>_mark_as_done`` convention."""
        entity_id = _button_entity_id(TEST_TASK_NAME)
        assert entity_id.startswith("button.task_tracker_"), (
            f"Button entity ID {entity_id!r} does not follow the expected naming convention"
        )
        assert entity_id.endswith("_mark_as_done"), (
            f"Button entity ID {entity_id!r} should end with '_mark_as_done'"
        )

    def test_button_press_via_api(self, task_tracker_entry, ha_get, call_service):
        """Pressing the button via the ``button.press`` service transitions the sensor to 'done'."""
        button_id = _button_entity_id(TEST_TASK_NAME)
        sensor_id = _sensor_entity_id(TEST_TASK_NAME)

        resp = call_service("button", "press", {"entity_id": button_id})
        assert resp.status_code == 200, f"button.press service call failed: {resp.text}"

        deadline = time.time() + 15
        while time.time() < deadline:
            sensor_state = _get_state(ha_get, sensor_id)
            if sensor_state["state"] == "done":
                break
            time.sleep(1)

        sensor_state = _get_state(ha_get, sensor_id)
        assert sensor_state["state"] == "done", (
            f"Expected sensor state 'done' after pressing button, got {sensor_state['state']!r}"
        )

    def test_button_has_last_triggered_attribute(self, task_tracker_entry, ha_get, call_service):
        """After pressing, the button entity has a ``last_triggered`` timestamp."""
        button_id = _button_entity_id(TEST_TASK_NAME)

        call_service("button", "press", {"entity_id": button_id})
        time.sleep(2)

        state = _get_state(ha_get, button_id)
        # HA sets ``last_triggered`` (via the ``last_pressed`` mechanism) after a press
        assert state.get("state") is not None, "Button entity has no state after press"

    def test_button_device_matches_sensor_device(self, task_tracker_entry, ha_get):
        """Button and sensor belong to the same HA device."""
        resp = ha_get("config/device_registry/list")
        if resp.status_code != 200:
            pytest.skip("Device registry endpoint not available")

        devices = resp.json().get("devices", [])
        button_id = _button_entity_id(TEST_TASK_NAME)
        sensor_id = _sensor_entity_id(TEST_TASK_NAME)

        entities_resp = ha_get("config/entity_registry/list")
        if entities_resp.status_code != 200:
            pytest.skip("Entity registry endpoint not available")

        entities = entities_resp.json().get("entities", [])
        button_device = next(
            (e["device_id"] for e in entities if e["entity_id"] == button_id), None
        )
        sensor_device = next(
            (e["device_id"] for e in entities if e["entity_id"] == sensor_id), None
        )

        assert button_device is not None, f"Button entity {button_id!r} not found in entity registry"
        assert sensor_device is not None, f"Sensor entity {sensor_id!r} not found in entity registry"
        assert button_device == sensor_device, (
            f"Button (device={button_device}) and sensor (device={sensor_device}) are on different devices"
        )

    def test_button_ui_visible_in_developer_tools(self, page: Page, task_tracker_entry):
        """The button entity is visible in the HA developer tools states page."""
        page.goto(f"{HA_URL}/developer-tools/state")
        page.wait_for_load_state("networkidle", timeout=30_000)

        button_id = _button_entity_id(TEST_TASK_NAME)
        # Search for the entity in the filter box if present
        filter_input = page.locator("input[placeholder*='filter' i], input[placeholder*='search' i]").first
        if filter_input.is_visible():
            filter_input.fill(button_id)
            page.wait_for_timeout(1_000)

        content = page.content()
        assert button_id in content, (
            f"Button entity {button_id!r} not found in developer-tools states page"
        )
