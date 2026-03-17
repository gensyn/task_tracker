import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ICON

from task_tracker import async_migrate_entry, _get_coordinator
from task_tracker.const import (
    CONF_ACTIVE, CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE,
    CONF_TAGS, CONF_TODO_LISTS, CONF_TODO_OFFSET_DAYS, CONF_NOTIFICATION_INTERVAL, CONF_DAY,
    DOMAIN,
)
from task_tracker.coordinator import TaskTrackerCoordinator


class TestAsyncMigrateEntry(unittest.IsolatedAsyncioTestCase):

    async def test_migrates_version_1_1_to_1_2(self):
        entry = ConfigEntry(
            entry_id="test",
            version=1,
            minor_version=1,
            options={
                "task_frequency": 7,
                "icon": "mdi:calendar",
                "assignees": "user1",
                "notification_frequency": 2,
            },
        )

        mock_hass = MagicMock()

        result = await async_migrate_entry(mock_hass, entry)

        self.assertTrue(result)
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
        self.assertEqual(call_kwargs["version"], 1)
        self.assertEqual(call_kwargs["minor_version"], 2)
        new_options = call_kwargs["options"]
        self.assertTrue(new_options[CONF_ACTIVE])
        self.assertEqual(new_options[CONF_TASK_INTERVAL_VALUE], 7)
        self.assertEqual(new_options[CONF_TASK_INTERVAL_TYPE], CONF_DAY)
        self.assertEqual(new_options[CONF_ICON], "mdi:calendar")
        self.assertEqual(new_options[CONF_TAGS], "user1")
        self.assertEqual(new_options[CONF_TODO_LISTS], [])
        self.assertEqual(new_options[CONF_TODO_OFFSET_DAYS], 0)
        self.assertEqual(new_options[CONF_NOTIFICATION_INTERVAL], 2)

    async def test_returns_true_for_current_version(self):
        entry = ConfigEntry(version=1, minor_version=2)
        mock_hass = MagicMock()
        result = await async_migrate_entry(mock_hass, entry)
        self.assertTrue(result)

    async def test_returns_false_for_future_major_version(self):
        entry = ConfigEntry(version=2, minor_version=1)
        mock_hass = MagicMock()
        result = await async_migrate_entry(mock_hass, entry)
        self.assertFalse(result)

    async def test_returns_false_for_future_minor_version(self):
        entry = ConfigEntry(version=1, minor_version=3)
        mock_hass = MagicMock()
        result = await async_migrate_entry(mock_hass, entry)
        self.assertFalse(result)


class TestGetCoordinator(unittest.IsolatedAsyncioTestCase):

    def _make_hass(self, coordinator, config_entry_id="entry1"):
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {config_entry_id: coordinator}}
        import homeassistant.helpers.entity_registry as entity_registry
        mock_reg_entry = MagicMock()
        mock_reg_entry.config_entry_id = config_entry_id
        entity_registry.async_get = lambda hass: MagicMock(
            async_get=lambda entity_id: mock_reg_entry
        )
        return mock_hass

    def test_returns_coordinator_when_found(self):
        coordinator = TaskTrackerCoordinator("entry1")
        mock_hass = self._make_hass(coordinator)
        result = _get_coordinator(mock_hass, "sensor.task_tracker_my_task")
        self.assertEqual(result, coordinator)

    def test_raises_when_entity_not_in_registry(self):
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {}}
        import homeassistant.helpers.entity_registry as entity_registry
        entity_registry.async_get = lambda hass: MagicMock(async_get=lambda entity_id: None)
        with self.assertRaises(ValueError):
            _get_coordinator(mock_hass, "sensor.task_tracker_nonexistent")

    def test_raises_when_coordinator_not_in_hass_data(self):
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {}}
        import homeassistant.helpers.entity_registry as entity_registry
        mock_reg_entry = MagicMock()
        mock_reg_entry.config_entry_id = "entry_missing"
        entity_registry.async_get = lambda hass: MagicMock(
            async_get=lambda entity_id: mock_reg_entry
        )
        with self.assertRaises(ValueError):
            _get_coordinator(mock_hass, "sensor.task_tracker_my_task")

