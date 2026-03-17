"""Integration tests for the Task Tracker custom component.

These tests use ``pytest-homeassistant-custom-component`` which spins up a
real (in-process) Home Assistant instance per test.  No hand-rolled mocks
are needed: the ``hass`` fixture IS a real ``HomeAssistant`` object, and
entities, states, and services all behave exactly as they do at runtime.

Run with:
    pytest tests/ -v
"""

from __future__ import annotations

from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.task_tracker.const import (
    CONF_ACTIVE,
    CONF_DATE,
    CONF_DAY,
    CONF_ICON,
    CONF_NOTIFICATION_INTERVAL,
    CONF_TAGS,
    CONF_TASK_INTERVAL_TYPE,
    CONF_TASK_INTERVAL_VALUE,
    CONF_TODO_LISTS,
    CONF_TODO_OFFSET_DAYS,
    CONST_DONE,
    CONST_DUE,
    CONST_INACTIVE,
    DOMAIN,
    SERVICE_MARK_AS_DONE,
    SERVICE_SET_LAST_DONE_DATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    entry_id: str = "entry1",
    name: str = "Water Plants",
    task_interval_value: int = 7,
    active: bool = True,
) -> MockConfigEntry:
    """Return a minimal MockConfigEntry ready to add to hass."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        title=name,
        data={"name": name},
        options={
            CONF_ACTIVE: active,
            CONF_TASK_INTERVAL_VALUE: task_interval_value,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_NOTIFICATION_INTERVAL: 2,
            CONF_TODO_LISTS: [],
            CONF_TODO_OFFSET_DAYS: 0,
            CONF_TAGS: "",
            CONF_ICON: "mdi:water",
        },
        version=1,
        minor_version=2,
    )


async def _setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add *entry* to hass and wait for setup to complete."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


# ---------------------------------------------------------------------------
# Entry setup
# ---------------------------------------------------------------------------


class TestSetupEntry:
    """Config entry setup creates the expected entities and coordinator."""

    async def test_sensor_state_created(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state is not None

    async def test_button_state_created(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        state = hass.states.get("button.task_tracker_water_plants_mark_as_done")
        assert state is not None

    async def test_sensor_initial_state_is_due(self, hass: HomeAssistant) -> None:
        """With last_done at the epoch the task is always overdue → state is 'due'."""
        entry = _make_entry()
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DUE

    async def test_sensor_due_in_attribute_is_zero_when_overdue(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_in"] == 0

    async def test_coordinator_stored_in_hass_data(self, hass: HomeAssistant) -> None:
        from custom_components.task_tracker.coordinator import TaskTrackerCoordinator

        entry = _make_entry(entry_id="e1")
        await _setup_entry(hass, entry)

        coordinator = hass.data[DOMAIN]["e1"]
        assert isinstance(coordinator, TaskTrackerCoordinator)

    async def test_sensor_task_interval_reflected_in_attributes(self, hass: HomeAssistant) -> None:
        entry = _make_entry(task_interval_value=14)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_value"] == 14
        assert state.attributes["task_interval_type"] == CONF_DAY


# ---------------------------------------------------------------------------
# mark_as_done service
# ---------------------------------------------------------------------------


class TestMarkAsDoneService:
    """The mark_as_done service updates the sensor state end-to-end."""

    async def test_service_is_registered(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        assert hass.services.has_service(DOMAIN, SERVICE_MARK_AS_DONE)

    async def test_service_changes_state_to_done(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        assert hass.states.get("sensor.task_tracker_water_plants").state == CONST_DUE

        await hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {"entity_id": "sensor.task_tracker_water_plants"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert hass.states.get("sensor.task_tracker_water_plants").state == CONST_DONE

    async def test_service_updates_last_done_to_today(self, hass: HomeAssistant) -> None:
        entry = _make_entry(entry_id="e1")
        await _setup_entry(hass, entry)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {"entity_id": "sensor.task_tracker_water_plants"},
            blocking=True,
        )
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN]["e1"]
        assert coordinator.last_done == date.today()

    async def test_last_done_attribute_updated_to_today(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {"entity_id": "sensor.task_tracker_water_plants"},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["last_done"] == str(date.today())


# ---------------------------------------------------------------------------
# set_last_done_date service
# ---------------------------------------------------------------------------


class TestSetLastDoneDateService:
    """The set_last_done_date service propagates through to sensor attributes."""

    async def test_service_is_registered(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        assert hass.services.has_service(DOMAIN, SERVICE_SET_LAST_DONE_DATE)

    async def test_service_updates_last_done_attribute(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        target = date(2024, 6, 15)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": target},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["last_done"] == "2024-06-15"

    async def test_service_recalculates_due_date(self, hass: HomeAssistant) -> None:
        """With a 7-day interval, due_date = last_done + 7 days."""
        entry = _make_entry(task_interval_value=7)
        await _setup_entry(hass, entry)

        target = date(2024, 6, 15)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": target},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_date"] == "2024-06-22"


# ---------------------------------------------------------------------------
# Button press
# ---------------------------------------------------------------------------


class TestButtonPress:
    """Pressing the 'mark as done' button updates coordinator and sensor state."""

    async def test_button_press_sets_state_to_done(self, hass: HomeAssistant) -> None:
        entry = _make_entry()
        await _setup_entry(hass, entry)

        assert hass.states.get("sensor.task_tracker_water_plants").state == CONST_DUE

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.task_tracker_water_plants_mark_as_done"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert hass.states.get("sensor.task_tracker_water_plants").state == CONST_DONE

    async def test_button_press_updates_coordinator_last_done(self, hass: HomeAssistant) -> None:
        entry = _make_entry(entry_id="e1")
        await _setup_entry(hass, entry)

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.task_tracker_water_plants_mark_as_done"},
            blocking=True,
        )
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN]["e1"]
        assert coordinator.last_done == date.today()


# ---------------------------------------------------------------------------
# Inactive task
# ---------------------------------------------------------------------------


class TestInactiveTask:
    """An inactive task shows the 'inactive' state."""

    async def test_inactive_task_state(self, hass: HomeAssistant) -> None:
        entry = _make_entry(active=False)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_INACTIVE


# ---------------------------------------------------------------------------
# Entry unload
# ---------------------------------------------------------------------------


class TestEntryUnload:
    """Unloading an entry removes its coordinator from hass.data."""

    async def test_unload_removes_coordinator(self, hass: HomeAssistant) -> None:
        entry = _make_entry(entry_id="e1")
        await _setup_entry(hass, entry)
        assert "e1" in hass.data.get(DOMAIN, {})

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert "e1" not in hass.data.get(DOMAIN, {})

    async def test_second_entry_unaffected_by_first_unload(self, hass: HomeAssistant) -> None:
        entry_a = _make_entry(entry_id="ea", name="Task A")
        entry_b = _make_entry(entry_id="eb", name="Task B")
        await _setup_entry(hass, entry_a)
        await _setup_entry(hass, entry_b)

        await hass.config_entries.async_unload(entry_a.entry_id)
        await hass.async_block_till_done()

        assert "ea" not in hass.data.get(DOMAIN, {})
        assert "eb" in hass.data.get(DOMAIN, {})


# ---------------------------------------------------------------------------
# Multiple independent entries
# ---------------------------------------------------------------------------


class TestMultipleEntries:
    """Multiple config entries coexist without interfering."""

    async def test_both_sensors_created(self, hass: HomeAssistant) -> None:
        await _setup_entry(hass, _make_entry(entry_id="ea", name="Task Alpha"))
        await _setup_entry(hass, _make_entry(entry_id="eb", name="Task Beta"))

        assert hass.states.get("sensor.task_tracker_task_alpha") is not None
        assert hass.states.get("sensor.task_tracker_task_beta") is not None

    async def test_marking_one_done_does_not_affect_other(self, hass: HomeAssistant) -> None:
        await _setup_entry(hass, _make_entry(entry_id="ea", name="Task Alpha"))
        await _setup_entry(hass, _make_entry(entry_id="eb", name="Task Beta"))

        await hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {"entity_id": "sensor.task_tracker_task_alpha"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert hass.states.get("sensor.task_tracker_task_alpha").state == CONST_DONE
        assert hass.states.get("sensor.task_tracker_task_beta").state == CONST_DUE

    async def test_coordinators_are_independent_instances(self, hass: HomeAssistant) -> None:
        await _setup_entry(hass, _make_entry(entry_id="ea", name="Task Alpha"))
        await _setup_entry(hass, _make_entry(entry_id="eb", name="Task Beta"))

        coord_a = hass.data[DOMAIN]["ea"]
        coord_b = hass.data[DOMAIN]["eb"]
        assert coord_a is not coord_b
