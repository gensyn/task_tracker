"""Playwright E2E tests – Task Tracker service calls.

These tests verify the two custom services exposed by Task Tracker:
* ``task_tracker.mark_as_done``
* ``task_tracker.set_last_done_date``

All assertions go through the HA REST API so they are independent of the
Playwright browser session.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

import pytest

from conftest import INTEGRATION_DOMAIN, TEST_TASK_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sensor_entity_id(task_name: str) -> str:
    slug = task_name.lower().replace(" ", "_")
    return f"sensor.task_tracker_{slug}"


def _get_state(ha_get, entity_id: str, timeout: int = 15) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = ha_get(f"states/{entity_id}")
        if resp.status_code == 200:
            return resp.json()
        time.sleep(1)
    pytest.fail(f"Entity {entity_id!r} did not appear within {timeout}s")


def _wait_for_state(ha_get, entity_id: str, expected: str, timeout: int = 15) -> dict:
    """Poll until the entity reaches *expected* state or *timeout* elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = _get_state(ha_get, entity_id)
        if state["state"] == expected:
            return state
        time.sleep(1)
    state = _get_state(ha_get, entity_id)
    pytest.fail(
        f"Entity {entity_id!r} did not reach state {expected!r} within {timeout}s; "
        f"current state: {state['state']!r}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestServices:
    """Tests for the Task Tracker custom services."""

    def test_mark_as_done_service_exists(self, ha_get):
        """The mark_as_done service is registered in the HA service registry."""
        resp = ha_get("services")
        assert resp.status_code == 200, f"Could not fetch service list: {resp.text}"
        services = resp.json()

        domain_services = next(
            (d["services"] for d in services if d["domain"] == INTEGRATION_DOMAIN), None
        )
        assert domain_services is not None, (
            f"Domain {INTEGRATION_DOMAIN!r} not found in service registry"
        )
        assert "mark_as_done" in domain_services, (
            f"mark_as_done not registered under {INTEGRATION_DOMAIN}"
        )

    def test_set_last_done_date_service_exists(self, ha_get):
        """The set_last_done_date service is registered in the HA service registry."""
        resp = ha_get("services")
        assert resp.status_code == 200
        services = resp.json()

        domain_services = next(
            (d["services"] for d in services if d["domain"] == INTEGRATION_DOMAIN), None
        )
        assert domain_services is not None, (
            f"Domain {INTEGRATION_DOMAIN!r} not found in service registry"
        )
        assert "set_last_done_date" in domain_services, (
            f"set_last_done_date not registered under {INTEGRATION_DOMAIN}"
        )

    def test_mark_as_done_sets_state_to_done(self, task_tracker_entry, ha_get, call_service):
        """Calling mark_as_done transitions the sensor state to 'done'."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)

        resp = call_service(INTEGRATION_DOMAIN, "mark_as_done", {"entity_id": entity_id})
        assert resp.status_code == 200, f"mark_as_done failed: {resp.text}"

        state = _wait_for_state(ha_get, entity_id, "done")
        assert state["state"] == "done"

    def test_mark_as_done_updates_last_done_to_today(self, task_tracker_entry, ha_get, call_service):
        """After mark_as_done, the last_done attribute equals today."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)

        resp = call_service(INTEGRATION_DOMAIN, "mark_as_done", {"entity_id": entity_id})
        assert resp.status_code == 200, f"mark_as_done failed: {resp.text}"
        time.sleep(2)

        state = _get_state(ha_get, entity_id)
        assert state["attributes"]["last_done"] == str(date.today()), (
            f"Expected last_done == {date.today()}, got {state['attributes']['last_done']!r}"
        )

    def test_set_last_done_date_to_specific_date(self, task_tracker_entry, ha_get, call_service):
        """set_last_done_date correctly persists a custom date."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)
        target = "2020-06-15"

        resp = call_service(
            INTEGRATION_DOMAIN,
            "set_last_done_date",
            {"entity_id": entity_id, "date": target},
        )
        assert resp.status_code == 200, f"set_last_done_date failed: {resp.text}"
        time.sleep(2)

        state = _get_state(ha_get, entity_id)
        assert state["attributes"]["last_done"] == target, (
            f"Expected last_done == {target!r}, got {state['attributes']['last_done']!r}"
        )

    def test_set_last_done_date_causes_due_state(self, task_tracker_entry, ha_get, call_service):
        """Setting last_done far in the past makes the sensor enter the 'due' state."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)

        resp = call_service(
            INTEGRATION_DOMAIN,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "2000-01-01"},
        )
        assert resp.status_code == 200, f"set_last_done_date failed: {resp.text}"

        state = _wait_for_state(ha_get, entity_id, "due")
        assert state["state"] == "due"

    def test_mark_as_done_recent_date_causes_done_state(self, task_tracker_entry, ha_get, call_service):
        """Calling mark_as_done (setting last_done to today) makes the sensor enter 'done'."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)

        resp = call_service(
            INTEGRATION_DOMAIN,
            "mark_as_done",
            {"entity_id": entity_id},
        )
        assert resp.status_code == 200, f"mark_as_done failed: {resp.text}"

        state = _wait_for_state(ha_get, entity_id, "done")
        assert state["state"] == "done"

    def test_mark_as_done_invalid_entity_returns_error(self, ha_get, call_service):
        """Calling mark_as_done with a nonexistent entity returns an error response."""
        resp = call_service(
            INTEGRATION_DOMAIN,
            "mark_as_done",
            {"entity_id": "sensor.does_not_exist_xyz"},
        )
        assert resp.status_code != 200, (
            "Expected an error response when calling mark_as_done with an invalid entity"
        )

    def test_set_last_done_date_invalid_entity_returns_error(self, ha_get, call_service):
        """Calling set_last_done_date with a nonexistent entity returns an error response."""
        resp = call_service(
            INTEGRATION_DOMAIN,
            "set_last_done_date",
            {"entity_id": "sensor.does_not_exist_xyz", "date": "2020-01-01"},
        )
        assert resp.status_code != 200, (
            "Expected an error response when calling set_last_done_date with an invalid entity"
        )

    def test_round_trip_mark_done_then_set_past_date(self, task_tracker_entry, ha_get, call_service):
        """After mark_as_done the sensor is 'done'; set_last_done_date to the past makes it 'due'."""
        entity_id = _sensor_entity_id(TEST_TASK_NAME)

        # Mark as done
        resp = call_service(INTEGRATION_DOMAIN, "mark_as_done", {"entity_id": entity_id})
        assert resp.status_code == 200
        _wait_for_state(ha_get, entity_id, "done")

        # Set to old date
        resp = call_service(
            INTEGRATION_DOMAIN,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "2000-01-01"},
        )
        assert resp.status_code == 200
        state = _wait_for_state(ha_get, entity_id, "due")
        assert state["state"] == "due"
