"""Playwright E2E tests: Task Tracker configuration management."""

from __future__ import annotations

import time
from typing import Any

import requests

from conftest import HA_URL, _add_integration, _get_task_tracker_entry_ids, call_service, get_sensor_state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Tests covering configuration options of the Task Tracker integration."""

    def test_interval_type_day(self, ha_api: requests.Session) -> None:
        """An entry created with interval_type='day' is accepted by the config flow."""
        entries_before = _get_task_tracker_entry_ids(ha_api)
        result = _add_integration(
            ha_api, name="Day Interval Task", interval_value=3, interval_type="day"
        )
        assert result.get("type") == "create_entry"

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_interval_type_week(self, ha_api: requests.Session) -> None:
        """An entry created with interval_type='week' is accepted by the config flow."""
        entries_before = _get_task_tracker_entry_ids(ha_api)
        result = _add_integration(
            ha_api, name="Week Interval Task", interval_value=2, interval_type="week"
        )
        assert result.get("type") == "create_entry"

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_interval_type_month(self, ha_api: requests.Session) -> None:
        """An entry created with interval_type='month' is accepted by the config flow."""
        entries_before = _get_task_tracker_entry_ids(ha_api)
        result = _add_integration(
            ha_api, name="Month Interval Task", interval_value=1, interval_type="month"
        )
        assert result.get("type") == "create_entry"

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_interval_type_year(self, ha_api: requests.Session) -> None:
        """An entry created with interval_type='year' is accepted by the config flow."""
        entries_before = _get_task_tracker_entry_ids(ha_api)
        result = _add_integration(
            ha_api, name="Year Interval Task", interval_value=1, interval_type="year"
        )
        assert result.get("type") == "create_entry"

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_sensor_reflects_task_interval(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """The sensor's task_interval_value attribute reflects the configured interval."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        state = get_sensor_state(ha_api, entity_id)
        # The fixture creates a task with interval_value=7
        assert state["attributes"].get("task_interval_value") == 7, (
            f"Expected task_interval_value=7, got: {state['attributes'].get('task_interval_value')!r}"
        )
        assert state["attributes"].get("task_interval_type") == "day", (
            f"Expected task_interval_type='day', got: {state['attributes'].get('task_interval_type')!r}"
        )

    def test_mark_as_done_then_due_after_interval(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """After mark_as_done the sensor is 'done'; after setting last_done to the past it is 'due'."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        # Mark as done → state should be 'done'
        call_service(ha_api, "mark_as_done", {"entity_id": entity_id})
        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        assert state["state"] == "done"

        # Set last done far in the past → state should be 'due'
        call_service(
            ha_api,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "1970-01-01"},
        )
        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        assert state["state"] == "due"

    def test_sensor_starts_in_due_state(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """A freshly created task sensor starts in the 'due' state (last_done=1970-01-01)."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        state = get_sensor_state(ha_api, entity_id)
        # A task with last_done=1970-01-01 and any positive interval is overdue
        assert state["state"] == "due", (
            f"Expected new task to start in 'due' state, got: {state['state']!r}"
        )

    def test_multiple_tasks_independent(self, ha_api: requests.Session) -> None:
        """Multiple tasks can be configured and managed independently."""
        entries_before = _get_task_tracker_entry_ids(ha_api)

        _add_integration(ha_api, name="Independent Task A", interval_value=7, interval_type="day")
        _add_integration(ha_api, name="Independent Task B", interval_value=14, interval_type="day")

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        assert len(new_entries) == 2, f"Expected 2 new entries, got {len(new_entries)}"

        # Wait for entities to appear
        time.sleep(3)
        states_resp = ha_api.get(f"{HA_URL}/api/states")
        sensor_entities = [
            s["entity_id"]
            for s in states_resp.json()
            if s["entity_id"].startswith("sensor.task_tracker_")
        ]
        assert len(sensor_entities) >= 2, (
            f"Expected at least 2 sensor entities, found: {sensor_entities}"
        )

        # Cleanup
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_due_in_attribute_reflects_interval(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """The due_in attribute is 0 when the task is overdue."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        # Set last done to the past to ensure overdue
        call_service(
            ha_api,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "1970-01-01"},
        )
        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        assert state["attributes"].get("due_in") == 0, (
            f"Expected due_in=0 for overdue task, got: {state['attributes'].get('due_in')!r}"
        )
