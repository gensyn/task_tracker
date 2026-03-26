"""Playwright E2E tests: Task Tracker security properties."""

from __future__ import annotations

from typing import Any

import requests

from conftest import HA_URL, call_service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSecurity:
    """Tests that validate the security properties of the Task Tracker integration."""

    def test_api_requires_authentication(self) -> None:
        """Calling the HA service API without an auth token is rejected with 401."""
        resp = requests.post(
            f"{HA_URL}/api/services/task_tracker/mark_as_done",
            json={"entity_id": "sensor.task_tracker_test"},
            timeout=10,
        )
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated request, got {resp.status_code}"
        )

    def test_states_api_requires_authentication(self) -> None:
        """Reading HA state without an auth token is rejected with 401."""
        resp = requests.get(
            f"{HA_URL}/api/states",
            timeout=10,
        )
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated state read, got {resp.status_code}"
        )

    def test_config_entries_api_requires_authentication(self) -> None:
        """Reading config entries without an auth token is rejected with 401."""
        resp = requests.get(
            f"{HA_URL}/api/config/config_entries/entry",
            timeout=10,
        )
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated config entries read, got {resp.status_code}"
        )

    def test_mark_as_done_requires_valid_entity(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """mark_as_done with a syntactically invalid entity_id is rejected."""
        resp = call_service(
            ha_api,
            "mark_as_done",
            {"entity_id": "not_a_valid_entity_id"},
        )
        assert resp.status_code >= 400, (
            f"Expected error for invalid entity_id format, got {resp.status_code}"
        )

    def test_set_last_done_date_requires_valid_entity(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date with a non-existent entity_id is rejected."""
        resp = call_service(
            ha_api,
            "set_last_done_date",
            {
                "entity_id": "sensor.task_tracker_nonexistent_abcxyz",
                "date": "2020-01-01",
            },
        )
        assert resp.status_code >= 400, (
            f"Expected error for non-existent entity_id, got {resp.status_code}"
        )

    def test_set_last_done_date_requires_valid_date(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date with a malformed date string is rejected."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        resp = call_service(
            ha_api,
            "set_last_done_date",
            {"entity_id": entity_id, "date": "not-a-date"},
        )
        assert resp.status_code >= 400, (
            f"Expected error for invalid date format, got {resp.status_code}"
        )

    def test_mark_as_done_missing_entity_id(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """mark_as_done called without entity_id is rejected by HA schema validation."""
        resp = ha_api.post(
            f"{HA_URL}/api/services/task_tracker/mark_as_done",
            json={},
        )
        assert resp.status_code >= 400, (
            f"Expected error when entity_id is missing, got {resp.status_code}"
        )

    def test_set_last_done_date_missing_date(
        self, ha_api: requests.Session, ensure_integration: Any
    ) -> None:
        """set_last_done_date called without date is rejected by HA schema validation."""
        integration = ensure_integration
        entity_id: str = integration["entity_id"]

        resp = ha_api.post(
            f"{HA_URL}/api/services/task_tracker/set_last_done_date",
            json={"entity_id": entity_id},
        )
        assert resp.status_code >= 400, (
            f"Expected error when date is missing, got {resp.status_code}"
        )
