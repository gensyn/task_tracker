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
from homeassistant.const import CONF_ICON
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.task_tracker.const import (
    CONF_ACTIVE,
    CONF_ACTIVE_OVERRIDE,
    CONF_DATE,
    CONF_DAY,
    CONF_DUE_SOON_DAYS,
    CONF_DUE_SOON_OVERRIDE,
    CONF_MONTH,
    CONF_NOTIFICATION_INTERVAL,
    CONF_TAGS,
    CONF_TASK_INTERVAL_OVERRIDE,
    CONF_TASK_INTERVAL_TYPE,
    CONF_TASK_INTERVAL_VALUE,
    CONF_TODO_LISTS,
    CONF_WEEK,
    CONF_YEAR,
    CONST_DONE,
    CONST_DUE,
    CONST_DUE_SOON,
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
    task_interval_type: str = CONF_DAY,
    notification_interval: int = 2,
    todo_lists: list | None = None,
    due_soon_days: int = 0,
    tags: str = "",
    active: bool = True,
    icon: str = "mdi:water",
    active_override: str | None = None,
    task_interval_override: str | None = None,
    due_soon_override: str | None = None,
) -> MockConfigEntry:
    """Return a MockConfigEntry covering all configurable options."""
    options: dict = {
        CONF_ACTIVE: active,
        CONF_TASK_INTERVAL_VALUE: task_interval_value,
        CONF_TASK_INTERVAL_TYPE: task_interval_type,
        CONF_NOTIFICATION_INTERVAL: notification_interval,
        CONF_TODO_LISTS: todo_lists if todo_lists is not None else [],
        CONF_DUE_SOON_DAYS: due_soon_days,
        CONF_TAGS: tags,
        CONF_ICON: icon,
    }
    if active_override is not None:
        options[CONF_ACTIVE_OVERRIDE] = active_override
    if task_interval_override is not None:
        options[CONF_TASK_INTERVAL_OVERRIDE] = task_interval_override
    if due_soon_override is not None:
        options[CONF_DUE_SOON_OVERRIDE] = due_soon_override
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        title=name,
        data={"name": name},
        options=options,
        version=1,
        minor_version=3,
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


# ---------------------------------------------------------------------------
# Task interval types (week / month / year)
# ---------------------------------------------------------------------------


class TestTaskIntervalTypes:
    """Different task_interval_type values produce correct due_date calculations."""

    async def test_week_interval_due_date(self, hass: HomeAssistant) -> None:
        """2-week interval: due_date = last_done + 14 calendar days."""
        entry = _make_entry(task_interval_value=2, task_interval_type=CONF_WEEK)
        await _setup_entry(hass, entry)

        last_done = date(2024, 1, 1)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": last_done},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_date"] == "2024-01-15"

    async def test_month_interval_due_date(self, hass: HomeAssistant) -> None:
        """1-month interval: due_date = last_done + 1 calendar month."""
        entry = _make_entry(task_interval_value=1, task_interval_type=CONF_MONTH)
        await _setup_entry(hass, entry)

        last_done = date(2024, 1, 31)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": last_done},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_date"] == "2024-02-29"  # 2024 is a leap year

    async def test_year_interval_due_date(self, hass: HomeAssistant) -> None:
        """1-year interval: due_date = last_done + 1 calendar year."""
        entry = _make_entry(task_interval_value=1, task_interval_type=CONF_YEAR)
        await _setup_entry(hass, entry)

        last_done = date(2024, 3, 15)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": last_done},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_date"] == "2025-03-15"

    async def test_interval_type_reflected_in_attributes(self, hass: HomeAssistant) -> None:
        """task_interval_type attribute reports the configured type."""
        entry = _make_entry(task_interval_value=3, task_interval_type=CONF_MONTH)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_type"] == CONF_MONTH
        assert state.attributes["task_interval_value"] == 3


# ---------------------------------------------------------------------------
# Tags option
# ---------------------------------------------------------------------------


class TestTagsOption:
    """Tags string is parsed into a list and exposed in sensor attributes."""

    async def test_comma_separated_tags(self, hass: HomeAssistant) -> None:
        entry = _make_entry(tags="garden,outdoor,weekly")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["tags"] == ["garden", "outdoor", "weekly"]

    async def test_semicolon_separated_tags(self, hass: HomeAssistant) -> None:
        entry = _make_entry(tags="garden;outdoor")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["tags"] == ["garden", "outdoor"]

    async def test_space_separated_tags(self, hass: HomeAssistant) -> None:
        entry = _make_entry(tags="garden outdoor")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["tags"] == ["garden", "outdoor"]

    async def test_empty_tags_produces_empty_list(self, hass: HomeAssistant) -> None:
        entry = _make_entry(tags="")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["tags"] == []


# ---------------------------------------------------------------------------
# Icon option
# ---------------------------------------------------------------------------


class TestIconOption:
    """Icon value is stored and exposed in sensor attributes."""

    async def test_icon_appears_in_attributes(self, hass: HomeAssistant) -> None:
        entry = _make_entry(icon="mdi:flower")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["icon"] == "mdi:flower"

    async def test_different_icon_value(self, hass: HomeAssistant) -> None:
        entry = _make_entry(icon="mdi:calendar-check")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["icon"] == "mdi:calendar-check"


# ---------------------------------------------------------------------------
# Notification interval option
# ---------------------------------------------------------------------------


class TestNotificationIntervalOption:
    """notification_interval option is exposed in sensor attributes."""

    async def test_notification_interval_in_attributes(self, hass: HomeAssistant) -> None:
        entry = _make_entry(notification_interval=3)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["notification_interval"] == 3

    async def test_notification_interval_default(self, hass: HomeAssistant) -> None:
        entry = _make_entry(notification_interval=1)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["notification_interval"] == 1


# ---------------------------------------------------------------------------
# Due soon days option
# ---------------------------------------------------------------------------


class TestDueSoonDaysOption:
    """due_soon_days option is exposed in sensor attributes."""

    async def test_due_soon_days_in_attributes(self, hass: HomeAssistant) -> None:
        entry = _make_entry(due_soon_days=5)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_soon_days"] == 5

    async def test_due_soon_days_zero_default(self, hass: HomeAssistant) -> None:
        entry = _make_entry(due_soon_days=0)
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_soon_days"] == 0


# ---------------------------------------------------------------------------
# active_override (input_boolean)
# ---------------------------------------------------------------------------


class TestActiveOverride:
    """active_override reads an input_boolean entity to override the active flag."""

    async def test_override_on_forces_active_state(self, hass: HomeAssistant) -> None:
        """active_override=on makes the task active even if active=False."""
        hass.states.async_set("input_boolean.task_active", "on")
        entry = _make_entry(active=False, active_override="input_boolean.task_active")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        # Task is overdue from epoch, so effective active + overdue → due
        assert state.state == CONST_DUE

    async def test_override_off_forces_inactive_state(self, hass: HomeAssistant) -> None:
        """active_override=off makes the task inactive even if active=True."""
        hass.states.async_set("input_boolean.task_active", "off")
        entry = _make_entry(active=True, active_override="input_boolean.task_active")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_INACTIVE

    async def test_override_unavailable_falls_back_to_active_true(self, hass: HomeAssistant) -> None:
        """When override entity is unavailable, active flag from config is used."""
        hass.states.async_set("input_boolean.task_active", "unavailable")
        entry = _make_entry(active=True, active_override="input_boolean.task_active")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DUE  # active=True + overdue → due

    async def test_override_unavailable_falls_back_to_active_false(self, hass: HomeAssistant) -> None:
        """When override entity is unavailable, active=False from config produces inactive."""
        hass.states.async_set("input_boolean.task_active", "unavailable")
        entry = _make_entry(active=False, active_override="input_boolean.task_active")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_INACTIVE

    async def test_override_unknown_falls_back_to_configured_active(self, hass: HomeAssistant) -> None:
        """When override entity is unknown, active flag from config is used."""
        hass.states.async_set("input_boolean.task_active", "unknown")
        entry = _make_entry(active=True, active_override="input_boolean.task_active")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DUE

    async def test_override_state_change_updates_sensor(self, hass: HomeAssistant) -> None:
        """Changing the override entity state triggers a sensor re-evaluation."""
        hass.states.async_set("input_boolean.task_active", "on")
        entry = _make_entry(active=True, active_override="input_boolean.task_active")
        await _setup_entry(hass, entry)

        assert hass.states.get("sensor.task_tracker_water_plants").state == CONST_DUE

        # Flip the override to "off" — sensor should become inactive
        hass.states.async_set("input_boolean.task_active", "off")
        await hass.async_block_till_done()

        assert hass.states.get("sensor.task_tracker_water_plants").state == CONST_INACTIVE


# ---------------------------------------------------------------------------
# task_interval_override (input_number)
# ---------------------------------------------------------------------------


class TestTaskIntervalOverride:
    """task_interval_override reads an input_number entity to override the interval."""

    async def test_override_value_replaces_interval_in_days(self, hass: HomeAssistant) -> None:
        """Override of 14 → 14-day interval (regardless of configured type/value)."""
        hass.states.async_set("input_number.task_interval", "14")
        # Configure a 7-day interval; the override of 14 should take precedence
        entry = _make_entry(
            task_interval_value=7,
            task_interval_type=CONF_DAY,
            task_interval_override="input_number.task_interval",
        )
        await _setup_entry(hass, entry)

        last_done = date(2024, 1, 1)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": last_done},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_value"] == 14
        assert state.attributes["task_interval_type"] == CONF_DAY
        assert state.attributes["due_date"] == "2024-01-15"

    async def test_override_forces_interval_type_to_day(self, hass: HomeAssistant) -> None:
        """Even when base type is 'month', the override always results in 'day' type."""
        hass.states.async_set("input_number.task_interval", "10")
        entry = _make_entry(
            task_interval_value=1,
            task_interval_type=CONF_MONTH,
            task_interval_override="input_number.task_interval",
        )
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_type"] == CONF_DAY

    async def test_override_minimum_clamped_to_one(self, hass: HomeAssistant) -> None:
        """Values below 1 are clamped to 1 day."""
        hass.states.async_set("input_number.task_interval", "0")
        entry = _make_entry(task_interval_override="input_number.task_interval")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_value"] == 1

    async def test_override_unavailable_falls_back_to_configured_interval(self, hass: HomeAssistant) -> None:
        """When override entity is unavailable, configured interval and type are used."""
        hass.states.async_set("input_number.task_interval", "unavailable")
        entry = _make_entry(
            task_interval_value=30,
            task_interval_type=CONF_MONTH,
            task_interval_override="input_number.task_interval",
        )
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_value"] == 30
        assert state.attributes["task_interval_type"] == CONF_MONTH

    async def test_override_unknown_falls_back_to_configured_interval(self, hass: HomeAssistant) -> None:
        """When override entity is unknown, configured interval is used."""
        hass.states.async_set("input_number.task_interval", "unknown")
        entry = _make_entry(
            task_interval_value=14,
            task_interval_type=CONF_DAY,
            task_interval_override="input_number.task_interval",
        )
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["task_interval_value"] == 14

    async def test_override_state_change_updates_interval(self, hass: HomeAssistant) -> None:
        """Changing the override entity value triggers sensor re-evaluation."""
        hass.states.async_set("input_number.task_interval", "7")
        entry = _make_entry(task_interval_override="input_number.task_interval")
        await _setup_entry(hass, entry)

        assert hass.states.get("sensor.task_tracker_water_plants").attributes["task_interval_value"] == 7

        hass.states.async_set("input_number.task_interval", "21")
        await hass.async_block_till_done()

        assert hass.states.get("sensor.task_tracker_water_plants").attributes["task_interval_value"] == 21


# ---------------------------------------------------------------------------
# due_soon_override (input_number)
# ---------------------------------------------------------------------------


class TestDueSoonOverride:
    """due_soon_override reads an input_number entity to override due_soon_days."""

    async def test_override_value_replaces_due_soon_days(self, hass: HomeAssistant) -> None:
        """Override of 10 → due_soon_days=10, ignoring configured value of 0."""
        hass.states.async_set("input_number.todo_offset", "10")
        entry = _make_entry(
            due_soon_days=0,
            due_soon_override="input_number.todo_offset",
        )
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_soon_days"] == 10

    async def test_override_minimum_clamped_to_zero(self, hass: HomeAssistant) -> None:
        """Negative override values are clamped to 0."""
        hass.states.async_set("input_number.todo_offset", "-5")
        entry = _make_entry(due_soon_override="input_number.todo_offset")
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_soon_days"] == 0

    async def test_override_unavailable_falls_back_to_configured_due_soon_days(self, hass: HomeAssistant) -> None:
        """When override entity is unavailable, configured due_soon_days is used."""
        hass.states.async_set("input_number.todo_offset", "unavailable")
        entry = _make_entry(
            due_soon_days=3,
            due_soon_override="input_number.todo_offset",
        )
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_soon_days"] == 3

    async def test_override_unknown_falls_back_to_configured_due_soon_days(self, hass: HomeAssistant) -> None:
        """When override entity is unknown, configured due_soon_days is used."""
        hass.states.async_set("input_number.todo_offset", "unknown")
        entry = _make_entry(
            due_soon_days=7,
            due_soon_override="input_number.todo_offset",
        )
        await _setup_entry(hass, entry)

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.attributes["due_soon_days"] == 7

    async def test_override_state_change_updates_due_soon_days(self, hass: HomeAssistant) -> None:
        """Changing the override entity value triggers sensor re-evaluation."""
        hass.states.async_set("input_number.todo_offset", "2")
        entry = _make_entry(due_soon_override="input_number.todo_offset")
        await _setup_entry(hass, entry)

        assert hass.states.get("sensor.task_tracker_water_plants").attributes["due_soon_days"] == 2

        hass.states.async_set("input_number.todo_offset", "8")
        await hass.async_block_till_done()

        assert hass.states.get("sensor.task_tracker_water_plants").attributes["due_soon_days"] == 8


# ---------------------------------------------------------------------------
# due_soon state
# ---------------------------------------------------------------------------


class TestDueSoonState:
    """Tasks within the due_soon_days threshold get the 'due_soon' state."""

    async def test_due_soon_state_when_within_threshold(self, hass: HomeAssistant) -> None:
        """Task is 'due_soon' when due_in <= due_soon_days and due_in > 0."""
        entry = _make_entry(task_interval_value=7, due_soon_days=5)
        await _setup_entry(hass, entry)

        # Mark as done 4 days ago → due_in = 3, which is ≤ 5
        last_done = date.today() - __import__("datetime").timedelta(days=4)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {"entity_id": "sensor.task_tracker_water_plants", "date": last_done},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DUE_SOON

    async def test_done_state_when_beyond_threshold(self, hass: HomeAssistant) -> None:
        """Task is 'done' when due_in > due_soon_days."""
        entry = _make_entry(task_interval_value=7, due_soon_days=2)
        await _setup_entry(hass, entry)

        # Mark as done today → due_in = 7, which is > 2
        await hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {"entity_id": "sensor.task_tracker_water_plants"},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DONE

    async def test_due_state_takes_precedence_over_due_soon(self, hass: HomeAssistant) -> None:
        """When the task is overdue (due_in=0), state is 'due' not 'due_soon'."""
        entry = _make_entry(task_interval_value=7, due_soon_days=999)
        await _setup_entry(hass, entry)

        # Default last_done = epoch → always overdue
        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DUE

    async def test_no_due_soon_when_threshold_is_zero(self, hass: HomeAssistant) -> None:
        """When due_soon_days=0, tasks are never in 'due_soon' state."""
        entry = _make_entry(task_interval_value=7, due_soon_days=0)
        await _setup_entry(hass, entry)

        # Mark as done today → due_in = 7 > 0, so should be 'done'
        await hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {"entity_id": "sensor.task_tracker_water_plants"},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("sensor.task_tracker_water_plants")
        assert state.state == CONST_DONE
