"""Playwright E2E tests: Task Tracker integration setup via the config flow."""

from __future__ import annotations

from typing import Any

import requests

from conftest import (
    HA_URL,
    _add_integration,
    _get_task_tracker_entry_ids,
    _remove_all_task_tracker_entries,
)


class TestIntegrationSetup:
    """Tests that cover adding and removing the Task Tracker integration."""

    def test_add_integration(self, ha_api: requests.Session) -> None:
        """Adding the integration creates a config entry."""
        entries_before = _get_task_tracker_entry_ids(ha_api)

        result = _add_integration(ha_api, name="Setup Test Task")
        assert result.get("type") == "create_entry"

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        assert len(new_entries) == 1

        # Cleanup
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_add_multiple_integrations(self, ha_api: requests.Session) -> None:
        """Multiple Task Tracker entries can be added (one per task)."""
        entries_before = _get_task_tracker_entry_ids(ha_api)

        result1 = _add_integration(ha_api, name="Multi Task 1")
        result2 = _add_integration(ha_api, name="Multi Task 2")

        assert result1.get("type") == "create_entry"
        assert result2.get("type") == "create_entry"

        entries_after = _get_task_tracker_entry_ids(ha_api)
        new_entries = entries_after - entries_before
        assert len(new_entries) == 2

        # Cleanup
        for eid in new_entries:
            ha_api.delete(f"{HA_URL}/api/config/config_entries/entry/{eid}")

    def test_remove_integration(self, ha_api: requests.Session) -> None:
        """Removing a config entry deletes it from Home Assistant."""
        entries_before = _get_task_tracker_entry_ids(ha_api)

        result = _add_integration(ha_api, name="Remove Test Task")
        entry_id: str = result["entry_id"]

        entries_after_add = _get_task_tracker_entry_ids(ha_api)
        assert entry_id in entries_after_add

        del_resp = ha_api.delete(
            f"{HA_URL}/api/config/config_entries/entry/{entry_id}"
        )
        assert del_resp.status_code in (200, 204), del_resp.text

        entries_after_remove = _get_task_tracker_entry_ids(ha_api)
        remaining = entries_after_remove - entries_before
        assert entry_id not in remaining


class TestIntegrationLifecycle:
    """Single end-to-end lifecycle test covering the full add → use → remove cycle."""

    def test_full_lifecycle(self, ha_api: requests.Session) -> None:
        """Complete add → use services → remove → verify-clean lifecycle."""
        import time

        # ------------------------------------------------------------------ #
        # 0. Start from a clean state.                                        #
        # ------------------------------------------------------------------ #
        _remove_all_task_tracker_entries(ha_api)
        assert _get_task_tracker_entry_ids(ha_api) == set(), (
            "Precondition failed: task_tracker entries still present after cleanup"
        )

        # ------------------------------------------------------------------ #
        # 1. Add the integration via the config flow.                          #
        # ------------------------------------------------------------------ #
        result = _add_integration(ha_api, name="Lifecycle Task", interval_value=7, interval_type="day")
        assert result.get("type") == "create_entry", (
            f"Expected 'create_entry', got: {result.get('type')!r}"
        )
        entry_id: str = result["entry_id"]

        entry_ids_after_add = _get_task_tracker_entry_ids(ha_api)
        assert entry_id in entry_ids_after_add

        # ------------------------------------------------------------------ #
        # 2. Wait for the sensor entity to appear.                            #
        # ------------------------------------------------------------------ #
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

        assert entity_id is not None, "Sensor entity did not appear within 30s"

        # ------------------------------------------------------------------ #
        # 3. Call services against the task.                                   #
        # ------------------------------------------------------------------ #
        # mark_as_done
        done_resp = ha_api.post(
            f"{HA_URL}/api/services/task_tracker/mark_as_done",
            json={"entity_id": entity_id},
        )
        assert done_resp.status_code in (200, 204), done_resp.text

        # Verify the sensor state is now "done"
        time.sleep(2)
        state_resp = ha_api.get(f"{HA_URL}/api/states/{entity_id}")
        state_resp.raise_for_status()
        assert state_resp.json()["state"] == "done", (
            f"Expected 'done' after mark_as_done, got: {state_resp.json()['state']!r}"
        )

        # set_last_done_date to a date far in the past → task becomes due
        past_resp = ha_api.post(
            f"{HA_URL}/api/services/task_tracker/set_last_done_date",
            json={"entity_id": entity_id, "date": "1970-01-01"},
        )
        assert past_resp.status_code in (200, 204), past_resp.text

        time.sleep(2)
        state_resp2 = ha_api.get(f"{HA_URL}/api/states/{entity_id}")
        state_resp2.raise_for_status()
        assert state_resp2.json()["state"] == "due", (
            f"Expected 'due' after setting past date, got: {state_resp2.json()['state']!r}"
        )

        # ------------------------------------------------------------------ #
        # 4. Remove the integration and verify clean state.                   #
        # ------------------------------------------------------------------ #
        del_resp = ha_api.delete(
            f"{HA_URL}/api/config/config_entries/entry/{entry_id}"
        )
        assert del_resp.status_code in (200, 204), del_resp.text

        remaining = _get_task_tracker_entry_ids(ha_api)
        assert entry_id not in remaining, (
            f"Expected entry {entry_id!r} to be absent after removal"
        )
