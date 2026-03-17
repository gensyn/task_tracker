"""Integration tests for the Task Tracker custom component.

These tests exercise the component as a whole, wiring together config entries,
the coordinator, sensor and button entities, and the service layer — without
requiring a full Home Assistant installation.  They complement the unit tests
in ``test/`` which verify individual pieces in isolation.
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Path setup: inject the lightweight HA mock so that every ``homeassistant.*``
# import in the component resolves to the local stub, not a real installation.
# ---------------------------------------------------------------------------

_MOCK_PATH = str(Path(__file__).parent.parent / "homeassistant_mock")
_PLUGIN_PATH = str(Path(__file__).parent.parent.parent.parent.absolute())

for _p in (_MOCK_PATH, _PLUGIN_PATH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Component imports (must come after sys.path is set up)
# ---------------------------------------------------------------------------

import homeassistant.helpers.entity_registry as _entity_registry_module  # noqa: E402
from homeassistant.config_entries import ConfigEntry  # noqa: E402
from homeassistant.const import CONF_ENTITY_ID  # noqa: E402
from homeassistant.core import ServiceCall  # noqa: E402

import task_tracker as tt_init  # noqa: E402
import task_tracker.button as tt_button  # noqa: E402
import task_tracker.sensor as tt_sensor  # noqa: E402
from task_tracker.const import (  # noqa: E402
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
    DOMAIN,
    SERVICE_MARK_AS_DONE,
    SERVICE_SET_LAST_DONE_DATE,
)
from task_tracker.coordinator import TaskTrackerCoordinator  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal functional stubs used only in integration tests
# ---------------------------------------------------------------------------


class _ServiceRegistry:
    """Minimal service registry that records and dispatches service handlers."""

    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], object] = {}

    def async_register(self, domain: str, service: str, handler, schema=None) -> None:
        self._handlers[(domain, service)] = handler

    async def async_call(
        self,
        domain: str,
        service: str,
        service_data: dict | None = None,
        blocking: bool = False,
        return_response: bool = False,
    ) -> None:
        handler = self._handlers.get((domain, service))
        if handler:
            call = ServiceCall(data=service_data or {})
            result = handler(call)
            if asyncio.iscoroutine(result):
                await result


class _EventBus:
    """Minimal event bus that tracks listener subscriptions."""

    def __init__(self) -> None:
        self._listeners: dict[str, list] = {}

    def async_listen(self, event_type: str, callback, event_filter=None):
        self._listeners.setdefault(event_type, []).append((callback, event_filter))

        def _unsubscribe() -> None:
            self._listeners[event_type].remove((callback, event_filter))

        return _unsubscribe


class _EntityRegistry:
    """Minimal entity registry that maps entity_id → config_entry_id."""

    def __init__(self) -> None:
        self._entries: dict[str, MagicMock] = {}

    def async_get(self, entity_id: str) -> MagicMock | None:
        return self._entries.get(entity_id)

    def register(self, entity_id: str, config_entry_id: str) -> None:
        entry = MagicMock()
        entry.config_entry_id = config_entry_id
        self._entries[entity_id] = entry


class _ConfigEntries:
    """Minimal config-entries stub that can load sensor and button platforms."""

    def __init__(self, hass: "IntegrationHass") -> None:
        self._hass = hass

    def async_entries(self, domain: str | None = None) -> list:
        return []

    async def async_forward_entry_setups(self, entry: ConfigEntry, platforms) -> None:
        """Call each platform's async_setup_entry and wire the resulting entities."""
        from homeassistant.const import Platform

        for platform in platforms:
            entities: list = []
            if platform == Platform.SENSOR:
                await tt_sensor.async_setup_entry(self._hass, entry, entities.extend)
                for entity in entities:
                    entity.hass = self._hass
                    self._hass._entities[entity.entity_id] = entity
                    self._hass.entity_registry.register(entity.entity_id, entry.entry_id)
                    # Simulate the HA entity lifecycle: restore state and subscribe.
                    await entity.async_added_to_hass()
            elif platform == Platform.BUTTON:
                await tt_button.async_setup_entry(self._hass, entry, entities.extend)
                for entity in entities:
                    entity.hass = self._hass
                    self._hass._entities[entity.entity_id] = entity
                    self._hass.entity_registry.register(entity.entity_id, entry.entry_id)

    async def async_unload_platforms(self, entry: ConfigEntry, platforms) -> bool:
        return True

    def async_update_entry(self, entry: ConfigEntry, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(entry, key, value)


class IntegrationHass:
    """Minimal Home Assistant instance for integration tests."""

    def __init__(self) -> None:
        self.data: dict = {}
        self.services = _ServiceRegistry()
        self.bus = _EventBus()
        self.entity_registry = _EntityRegistry()
        self.states = MagicMock()
        self.states.get.return_value = None
        self._entities: dict = {}
        self.config_entries = _ConfigEntries(self)

    def get_entity(self, entity_id: str):
        return self._entities.get(entity_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_entity_registry(hass: IntegrationHass) -> None:
    """Redirect helpers.entity_registry.async_get to the integration hass stub."""
    _entity_registry_module.async_get = lambda _hass: hass.entity_registry


def _make_entry(entry_id: str = "entry1", name: str = "Water Plants") -> ConfigEntry:
    """Return a standard config entry suitable for most integration tests."""
    return ConfigEntry(
        entry_id=entry_id,
        data={"name": name},
        options={
            CONF_ACTIVE: True,
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_NOTIFICATION_INTERVAL: 2,
            CONF_TODO_LISTS: [],
            CONF_TODO_OFFSET_DAYS: 0,
            CONF_TAGS: "",
            CONF_ICON: "mdi:water",
        },
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestSetupEntry(unittest.IsolatedAsyncioTestCase):
    """async_setup_entry wires the coordinator and creates both entity types."""

    async def asyncSetUp(self) -> None:
        self.hass = IntegrationHass()
        _patch_entity_registry(self.hass)
        self.entry = _make_entry()
        await tt_init.async_setup_entry(self.hass, self.entry)

    async def test_coordinator_stored_in_hass_data(self) -> None:
        coordinator = self.hass.data.get(DOMAIN, {}).get("entry1")
        self.assertIsInstance(coordinator, TaskTrackerCoordinator)

    async def test_sensor_entity_created(self) -> None:
        sensor = self.hass.get_entity("sensor.task_tracker_water_plants")
        self.assertIsNotNone(sensor)

    async def test_button_entity_created(self) -> None:
        button = self.hass.get_entity("button.task_tracker_water_plants_mark_as_done")
        self.assertIsNotNone(button)

    async def test_sensor_initial_state_is_due(self) -> None:
        """With last_done at the epoch the task is always overdue → state is 'due'."""
        sensor = self.hass.get_entity("sensor.task_tracker_water_plants")
        self.assertEqual(sensor._attr_native_value, CONST_DUE)

    async def test_sensor_entry_name_matches_config(self) -> None:
        sensor = self.hass.get_entity("sensor.task_tracker_water_plants")
        self.assertEqual(sensor.entry_name, "Water Plants")

    async def test_sensor_task_interval_matches_config(self) -> None:
        sensor = self.hass.get_entity("sensor.task_tracker_water_plants")
        self.assertEqual(sensor.task_interval_value, 7)
        self.assertEqual(sensor.task_interval_type, CONF_DAY)


class TestMarkAsDoneViaCoordinator(unittest.IsolatedAsyncioTestCase):
    """Marking a task done via the coordinator updates the sensor state."""

    async def asyncSetUp(self) -> None:
        self.hass = IntegrationHass()
        _patch_entity_registry(self.hass)
        self.entry = _make_entry()
        await tt_init.async_setup_entry(self.hass, self.entry)
        self.sensor = self.hass.get_entity("sensor.task_tracker_water_plants")

    async def test_state_is_due_before_marking(self) -> None:
        self.assertEqual(self.sensor._attr_native_value, CONST_DUE)

    async def test_state_is_done_after_marking(self) -> None:
        await self.sensor.async_mark_as_done()
        await self.sensor.async_update()
        self.assertEqual(self.sensor._attr_native_value, CONST_DONE)

    async def test_coordinator_last_done_updated_to_today(self) -> None:
        await self.sensor.async_mark_as_done()
        self.assertEqual(self.sensor.coordinator.last_done, date.today())

    async def test_state_returns_to_due_when_last_done_reset(self) -> None:
        await self.sensor.async_mark_as_done()
        await self.sensor.async_update()
        self.assertEqual(self.sensor._attr_native_value, CONST_DONE)

        await self.sensor.coordinator.async_set_last_done_date(date(1970, 1, 1))
        await self.sensor.async_update()
        self.assertEqual(self.sensor._attr_native_value, CONST_DUE)


class TestSetLastDoneDateViaCoordinator(unittest.IsolatedAsyncioTestCase):
    """set_last_done_date propagates correctly through the coordinator to the sensor."""

    async def asyncSetUp(self) -> None:
        self.hass = IntegrationHass()
        _patch_entity_registry(self.hass)
        self.entry = _make_entry()
        await tt_init.async_setup_entry(self.hass, self.entry)
        self.sensor = self.hass.get_entity("sensor.task_tracker_water_plants")

    async def test_last_done_attribute_reflects_set_date(self) -> None:
        new_date = date(2024, 6, 15)
        await self.sensor.async_set_last_done_date(new_date)
        await self.sensor.async_update()
        self.assertEqual(
            self.sensor._attr_extra_state_attributes["last_done"],
            str(new_date),
        )

    async def test_due_date_recalculated_after_set_date(self) -> None:
        new_date = date(2024, 6, 15)
        await self.sensor.async_set_last_done_date(new_date)
        await self.sensor.async_update()
        # With a 7-day interval, due_date = 2024-06-22
        from datetime import timedelta
        expected_due = new_date + timedelta(days=7)
        self.assertEqual(
            self.sensor._attr_extra_state_attributes["due_date"],
            str(expected_due),
        )

    async def test_coordinator_last_done_is_updated(self) -> None:
        new_date = date(2023, 12, 1)
        await self.sensor.async_set_last_done_date(new_date)
        self.assertEqual(self.sensor.coordinator.last_done, new_date)


class TestButtonPressUpdatesSensorViaCoordinator(unittest.IsolatedAsyncioTestCase):
    """Pressing the button flows through the coordinator and changes sensor state."""

    async def asyncSetUp(self) -> None:
        self.hass = IntegrationHass()
        _patch_entity_registry(self.hass)
        self.entry = _make_entry()
        await tt_init.async_setup_entry(self.hass, self.entry)
        self.button = self.hass.get_entity("button.task_tracker_water_plants_mark_as_done")
        self.sensor = self.hass.get_entity("sensor.task_tracker_water_plants")

    async def test_pressing_button_sets_coordinator_last_done_to_today(self) -> None:
        self.assertNotEqual(self.sensor.coordinator.last_done, date.today())
        await self.button.async_press()
        self.assertEqual(self.sensor.coordinator.last_done, date.today())

    async def test_sensor_state_becomes_done_after_button_press(self) -> None:
        await self.button.async_press()
        await self.sensor.async_update()
        self.assertEqual(self.sensor._attr_native_value, CONST_DONE)

    async def test_button_and_sensor_share_same_coordinator(self) -> None:
        """Button and sensor for the same entry must use the same coordinator."""
        coordinator_from_hass = self.hass.data[DOMAIN]["entry1"]
        self.assertIs(self.sensor.coordinator, coordinator_from_hass)


class TestServiceRegistrationAndInvocation(unittest.IsolatedAsyncioTestCase):
    """Services are registered during async_setup and are callable end-to-end."""

    async def asyncSetUp(self) -> None:
        self.hass = IntegrationHass()
        _patch_entity_registry(self.hass)
        # Provide minimal stubs for the frontend registration that async_setup
        # performs — these are irrelevant to service-layer tests.
        self.hass.data["lovelace"] = MagicMock()
        self.hass.data["lovelace"].resource_mode = "yaml"  # != MODE_STORAGE → skip module registration
        self.hass.http = MagicMock()
        self.hass.http.async_register_static_paths = AsyncMock()

        await tt_init.async_setup(self.hass, {})
        self.entry = _make_entry()
        await tt_init.async_setup_entry(self.hass, self.entry)
        self.sensor = self.hass.get_entity("sensor.task_tracker_water_plants")

    async def test_mark_as_done_service_is_registered(self) -> None:
        self.assertIn((DOMAIN, SERVICE_MARK_AS_DONE), self.hass.services._handlers)

    async def test_set_last_done_date_service_is_registered(self) -> None:
        self.assertIn((DOMAIN, SERVICE_SET_LAST_DONE_DATE), self.hass.services._handlers)

    async def test_mark_as_done_service_updates_coordinator(self) -> None:
        entity_id = "sensor.task_tracker_water_plants"
        self.assertNotEqual(self.sensor.coordinator.last_done, date.today())

        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {CONF_ENTITY_ID: entity_id},
        )
        self.assertEqual(self.sensor.coordinator.last_done, date.today())

    async def test_set_last_done_date_service_updates_coordinator(self) -> None:
        entity_id = "sensor.task_tracker_water_plants"
        target_date = date(2024, 1, 10)

        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_SET_LAST_DONE_DATE,
            {CONF_ENTITY_ID: entity_id, CONF_DATE: target_date},
        )
        self.assertEqual(self.sensor.coordinator.last_done, target_date)

    async def test_mark_as_done_service_changes_sensor_state_to_done(self) -> None:
        entity_id = "sensor.task_tracker_water_plants"
        self.assertEqual(self.sensor._attr_native_value, CONST_DUE)

        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_MARK_AS_DONE,
            {CONF_ENTITY_ID: entity_id},
        )
        await self.sensor.async_update()
        self.assertEqual(self.sensor._attr_native_value, CONST_DONE)


class TestUnloadEntry(unittest.IsolatedAsyncioTestCase):
    """Unloading an entry removes its coordinator from hass.data."""

    async def test_coordinator_removed_on_unload(self) -> None:
        hass = IntegrationHass()
        _patch_entity_registry(hass)
        entry = _make_entry()
        await tt_init.async_setup_entry(hass, entry)
        self.assertIn("entry1", hass.data.get(DOMAIN, {}))

        result = await tt_init.async_unload_entry(hass, entry)

        self.assertTrue(result)
        self.assertNotIn("entry1", hass.data.get(DOMAIN, {}))

    async def test_second_entry_unaffected_by_first_unload(self) -> None:
        hass = IntegrationHass()
        _patch_entity_registry(hass)
        entry_a = _make_entry(entry_id="entry_a", name="Task A")
        entry_b = _make_entry(entry_id="entry_b", name="Task B")
        await tt_init.async_setup_entry(hass, entry_a)
        await tt_init.async_setup_entry(hass, entry_b)

        await tt_init.async_unload_entry(hass, entry_a)

        self.assertNotIn("entry_a", hass.data.get(DOMAIN, {}))
        self.assertIn("entry_b", hass.data.get(DOMAIN, {}))


class TestConfigFlowToSetupPipeline(unittest.IsolatedAsyncioTestCase):
    """Full pipeline: config-flow → ConfigEntry → async_setup_entry → sensor."""

    async def test_flow_result_produces_working_sensor(self) -> None:
        from task_tracker.config_flow import TaskTrackerConfigFlow

        # Step 1: run the config flow to obtain entry data/options.
        flow = TaskTrackerConfigFlow()
        flow.hass = MagicMock()
        flow.context = {"source": "user"}
        result = await flow.async_step_user(
            user_input={
                "name": "Clean Bathroom",
                CONF_TASK_INTERVAL_VALUE: 14,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            }
        )
        self.assertEqual(result["type"], "create_entry")

        # Step 2: build a ConfigEntry from the flow output and set it up.
        entry = ConfigEntry(
            entry_id="bathroom_entry",
            data=result["data"],
            options=result["options"],
        )
        hass = IntegrationHass()
        _patch_entity_registry(hass)
        await tt_init.async_setup_entry(hass, entry)

        # Step 3: verify the sensor reflects the configured interval.
        sensor = hass.get_entity("sensor.task_tracker_clean_bathroom")
        self.assertIsNotNone(sensor)
        self.assertEqual(sensor.task_interval_value, 14)
        self.assertEqual(sensor.task_interval_type, CONF_DAY)

    async def test_flow_result_sensor_starts_in_due_state(self) -> None:
        from task_tracker.config_flow import TaskTrackerConfigFlow

        flow = TaskTrackerConfigFlow()
        flow.hass = MagicMock()
        flow.context = {"source": "user"}
        result = await flow.async_step_user(
            user_input={
                "name": "Vacuum Floors",
                CONF_TASK_INTERVAL_VALUE: 7,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            }
        )
        entry = ConfigEntry(
            entry_id="vacuum_entry",
            data=result["data"],
            options=result["options"],
        )
        hass = IntegrationHass()
        _patch_entity_registry(hass)
        await tt_init.async_setup_entry(hass, entry)

        sensor = hass.get_entity("sensor.task_tracker_vacuum_floors")
        # Coordinator initializes last_done to 1970-01-01, so the task is always due.
        self.assertEqual(sensor._attr_native_value, CONST_DUE)

    async def test_options_flow_changes_are_reflected_in_sensor(self) -> None:
        """Updating options (e.g. interval) should be reflected when the sensor
        is re-created from the updated entry."""
        from task_tracker.config_flow import TaskTrackerConfigFlow
        from task_tracker.options_flow import TaskTrackerOptionsFlow

        # Create entry via config flow.
        flow = TaskTrackerConfigFlow()
        flow.hass = MagicMock()
        flow.context = {"source": "user"}
        result = await flow.async_step_user(
            user_input={
                "name": "Monthly Report",
                CONF_TASK_INTERVAL_VALUE: 30,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            }
        )
        entry = ConfigEntry(
            entry_id="report_entry",
            data=result["data"],
            options=result["options"],
        )

        # Update options via options flow (change interval to 14 days).
        options_flow = TaskTrackerOptionsFlow()
        options_flow.hass = MagicMock()
        options_flow.config_entry = entry
        options_result = await options_flow.async_step_init(
            user_input={
                CONF_ACTIVE: True,
                CONF_TASK_INTERVAL_VALUE: 14,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
                CONF_NOTIFICATION_INTERVAL: 1,
                CONF_ICON: "mdi:file",
                CONF_TAGS: "",
                CONF_TODO_LISTS: [],
                CONF_TODO_OFFSET_DAYS: 0,
            }
        )
        self.assertEqual(options_result["type"], "create_entry")
        updated_options = options_result["data"]

        # Build a fresh entry with the updated options and set it up.
        updated_entry = ConfigEntry(
            entry_id="report_entry",
            data=result["data"],
            options=updated_options,
        )
        hass = IntegrationHass()
        _patch_entity_registry(hass)
        await tt_init.async_setup_entry(hass, updated_entry)

        sensor = hass.get_entity("sensor.task_tracker_monthly_report")
        self.assertIsNotNone(sensor)
        self.assertEqual(sensor.task_interval_value, 14)


class TestMultipleEntries(unittest.IsolatedAsyncioTestCase):
    """Multiple config entries coexist without interfering with each other."""

    async def asyncSetUp(self) -> None:
        self.hass = IntegrationHass()
        _patch_entity_registry(self.hass)
        self.entry_a = _make_entry(entry_id="entry_a", name="Task Alpha")
        self.entry_b = _make_entry(entry_id="entry_b", name="Task Beta")
        await tt_init.async_setup_entry(self.hass, self.entry_a)
        await tt_init.async_setup_entry(self.hass, self.entry_b)

    async def test_both_coordinators_are_stored(self) -> None:
        domain_data = self.hass.data.get(DOMAIN, {})
        self.assertIn("entry_a", domain_data)
        self.assertIn("entry_b", domain_data)

    async def test_coordinators_are_independent_instances(self) -> None:
        domain_data = self.hass.data[DOMAIN]
        self.assertIsNot(domain_data["entry_a"], domain_data["entry_b"])

    async def test_marking_one_task_done_does_not_affect_other(self) -> None:
        sensor_a = self.hass.get_entity("sensor.task_tracker_task_alpha")
        sensor_b = self.hass.get_entity("sensor.task_tracker_task_beta")

        await sensor_a.async_mark_as_done()
        await sensor_a.async_update()
        await sensor_b.async_update()

        self.assertEqual(sensor_a._attr_native_value, CONST_DONE)
        self.assertEqual(sensor_b._attr_native_value, CONST_DUE)

    async def test_both_sensors_have_correct_entity_ids(self) -> None:
        self.assertIsNotNone(self.hass.get_entity("sensor.task_tracker_task_alpha"))
        self.assertIsNotNone(self.hass.get_entity("sensor.task_tracker_task_beta"))
