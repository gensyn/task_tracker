"""Playwright E2E tests: task_tracker service behaviour."""

from __future__ import annotations

import time
from typing import Any

import requests

from conftest import HA_URL, call_service, get_sensor_state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestServices:
    """Tests focused on the HA service interface of Task Tracker."""

    def test_services_registered(self, ha_api: requests.Session, ensure_integration: Any) -> None:
        """Both task_tracker services should appear in the HA services list."""
        resp = ha_api.get(f"{HA_URL}/api/services")
        resp.raise_for_status()
        services = resp.json()
        domains = {svc["domain"] for svc in services}
        assert "task_tracker" in domains, "task_tracker domain not found in services"

        tt_services = next(
            (svc for svc in services if svc["domain"] == "task_tracker"), None
        )
        assert tt_services is not None
        assert "mark_as_done" in tt_services.get("services", {}), (
            "mark_as_done service not found"
        )
        assert "set_last_done_date" in tt_services.get("services", {}), (
            "set_last_done_date service not found"
        )

    def test_mark_as_done_sets_done_state(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """mark_as_done transitions the sensor state to 'done'."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]
        assert entity_id is not None, "No entity_id available from ensure_integration"

        # First set the task as overdue so there is a clear before/after
        ha_api.post(
            f"{HA_URL}/api/services/task_tracker/set_last_done_date",
            json={"entity_id": entity_id, "date": "1970-01-01"},
        )
        time.sleep(2)
        before = get_sensor_state(ha_api, entity_id)
        assert before["state"] == "due", f"Expected 'due', got {before['state']!r}"

        # Call the service
        resp = call_service(ha_api, "mark_as_done", {"entity_id": entity_id})
        assert resp.status_code in (200, 204), resp.text

        time.sleep(2)
        after = get_sensor_state(ha_api, entity_id)
        assert after["state"] == "done", (
            f"Expected 'done' after mark_as_done, got {after['state']!r}"
        )

    def test_mark_as_done_updates_last_done_attribute(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """mark_as_done updates the last_done attribute to today's date."""
        from datetime import date

        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        resp = call_service(ha_api, "mark_as_done", {"entity_id": entity_id})
        assert resp.status_code in (200, 204), resp.text

        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        last_done = state["attributes"].get("last_done")
        assert last_done == str(date.today()), (
            f"Expected last_done == {date.today()!s}, got {last_done!r}"
        )

    def test_set_last_done_date_overdue(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date with a date far in the past makes the sensor 'due'."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        resp = call_service(
            ha_api,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "1970-01-01"},
        )
        assert resp.status_code in (200, 204), resp.text

        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        assert state["state"] == "due", (
            f"Expected 'due' after setting past date, got {state['state']!r}"
        )

    def test_set_last_done_date_today(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date with today's date makes the sensor 'done'."""
        from datetime import date

        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        resp = call_service(
            ha_api,
            "set_last_done_date",
            {"entity_id": entity_id, "date": str(date.today())},
        )
        assert resp.status_code in (200, 204), resp.text

        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        assert state["state"] == "done", (
            f"Expected 'done' after setting today's date, got {state['state']!r}"
        )

    def test_set_last_done_date_stores_attribute(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date stores the provided date in the last_done attribute."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]
        target_date = "2020-06-15"

        resp = call_service(
            ha_api,
            "set_last_done_date",
            {"entity_id": entity_id, "date": target_date},
        )
        assert resp.status_code in (200, 204), resp.text

        time.sleep(2)
        state = get_sensor_state(ha_api, entity_id)
        assert state["attributes"].get("last_done") == target_date, (
            f"Expected last_done == {target_date!r}, got {state['attributes'].get('last_done')!r}"
        )

    def test_mark_as_done_invalid_entity_id(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """mark_as_done with a non-existent entity_id returns an error."""
        resp = call_service(
            ha_api,
            "mark_as_done",
            {"entity_id": "sensor.task_tracker_nonexistent_xyz_12345"},
        )
        assert resp.status_code >= 400, (
            f"Expected error for invalid entity_id, got {resp.status_code}"
        )

    def test_set_last_done_date_invalid_entity_id(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date with a non-existent entity_id returns an error."""
        resp = call_service(
            ha_api,
            "set_last_done_date",
            {
                "entity_id": "sensor.task_tracker_nonexistent_xyz_12345",
                "date": "2020-01-01",
            },
        )
        assert resp.status_code >= 400, (
            f"Expected error for invalid entity_id, got {resp.status_code}"
        )

    def test_sensor_attributes_present(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """The sensor exposes the expected state attributes."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        state = get_sensor_state(ha_api, entity_id)
        attrs = state["attributes"]

        expected_attrs = [
            "last_done",
            "due_date",
            "due_in",
            "overdue_by",
            "task_interval_value",
            "task_interval_type",
            "icon",
            "tags",
            "notification_interval",
        ]
        for attr in expected_attrs:
            assert attr in attrs, f"Missing expected attribute: {attr!r}"
