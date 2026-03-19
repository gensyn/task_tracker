"""Playwright E2E tests – Task Tracker sensor entities.

These tests verify that sensor entities are created correctly when a Task
Tracker integration entry is set up, and that their state and attributes are
updated as expected when services are called.
"""

from __future__ import annotations

import time
from datetime import date

import pytest

from conftest import INTEGRATION_DOMAIN, TEST_TASK_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


class TestSensors:
    """Tests for Task Tracker sensor entities."""

    def test_sensor_is_created_after_integration_setup(self, task_tracker_entry, ha_get):
        """A sensor entity is created when the integration entry is loaded."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        state = _get_state(ha_get, entity_id)
        assert state["entity_id"] == entity_id

    def test_sensor_initial_state_is_due(self, task_tracker_entry, ha_get):
        """The sensor starts in the 'due' state (last_done defaults to 1970-01-01)."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        state = _get_state(ha_get, entity_id)
        assert state["state"] == "due", (
            f"Expected sensor state 'due', got {state['state']!r}"
        )

    def test_sensor_has_required_attributes(self, task_tracker_entry, ha_get):
        """The sensor exposes the required set of extra-state attributes."""
        required_attrs = {
            "last_done",
            "due_date",
            "due_in",
            "overdue_by",
            "task_interval_value",
            "task_interval_type",
            "icon",
            "tags",
            "todo_lists",
            "todo_offset_days",
            "notification_interval",
        }
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        state = _get_state(ha_get, entity_id)
        attributes = set(state.get("attributes", {}).keys())
        missing = required_attrs - attributes
        assert not missing, f"Sensor is missing attributes: {missing}"

    def test_sensor_task_interval_attribute_matches_config(self, task_tracker_entry, ha_get):
        """task_interval_value and task_interval_type reflect the configured values."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        state = _get_state(ha_get, entity_id)
        attrs = state["attributes"]
        assert attrs["task_interval_value"] == 7
        assert attrs["task_interval_type"] == "day"

    def test_sensor_state_becomes_done_after_mark_as_done(self, task_tracker_entry, ha_get, call_service):
        """Calling the mark_as_done service transitions the sensor state to 'done'."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)

        resp = call_service(
            INTEGRATION_DOMAIN,
            "mark_as_done",
            {"entity_id": entity_id},
        )
        assert resp.status_code == 200, f"mark_as_done service call failed: {resp.text}"

        # Poll until state changes or timeout
        deadline = time.time() + 15
        while time.time() < deadline:
            state = _get_state(ha_get, entity_id)
            if state["state"] == "done":
                break
            time.sleep(1)

        state = _get_state(ha_get, entity_id)
        assert state["state"] == "done", (
            f"Expected sensor state 'done' after mark_as_done, got {state['state']!r}"
        )

    def test_sensor_last_done_attribute_updated_after_mark_as_done(
        self, task_tracker_entry, ha_get, call_service
    ):
        """last_done attribute is set to today after calling mark_as_done."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        call_service(INTEGRATION_DOMAIN, "mark_as_done", {"entity_id": entity_id})
        time.sleep(2)

        state = _get_state(ha_get, entity_id)
        last_done = state["attributes"].get("last_done")
        assert last_done == str(date.today()), (
            f"Expected last_done == {date.today()}, got {last_done!r}"
        )

    def test_sensor_state_after_set_last_done_date(self, task_tracker_entry, ha_get, call_service):
        """set_last_done_date service correctly updates the sensor's last_done attribute."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        target_date = "2000-01-01"

        resp = call_service(
            INTEGRATION_DOMAIN,
            "set_last_done_date",
            {"entity_id": entity_id, "date": target_date},
        )
        assert resp.status_code == 200, f"set_last_done_date service call failed: {resp.text}"
        time.sleep(2)

        state = _get_state(ha_get, entity_id)
        assert state["attributes"].get("last_done") == target_date, (
            f"Expected last_done == {target_date!r}, got {state['attributes'].get('last_done')!r}"
        )
        assert state["state"] == "due", "Sensor should be 'due' after setting an old last_done date"

    def test_sensor_overdue_by_attribute_when_overdue(self, task_tracker_entry, ha_get, call_service):
        """overdue_by attribute is positive when the task is overdue."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        # Set last_done far in the past so the task is definitely overdue
        call_service(
            INTEGRATION_DOMAIN,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "2000-01-01"},
        )
        time.sleep(2)

        state = _get_state(ha_get, entity_id)
        overdue_by = state["attributes"].get("overdue_by", 0)
        assert overdue_by > 0, f"Expected overdue_by > 0, got {overdue_by!r}"

    def test_sensor_entity_id_format(self, task_tracker_entry, ha_get):
        """Sensor entity IDs follow the ``sensor.task_tracker_<slug>`` convention."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        assert entity_id.startswith("sensor.task_tracker_"), (
            f"Entity ID {entity_id!r} does not follow the expected naming convention"
        )
        # Confirm the entity actually exists
        state = _get_state(ha_get, entity_id)
        assert state["entity_id"] == entity_id
