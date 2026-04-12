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
    CONF_TAGS, CONF_TODO_LISTS, CONF_DUE_SOON_DAYS, CONF_DUE_SOON_OVERRIDE,
    CONF_NOTIFICATION_INTERVAL, CONF_DAY,
    CONF_REPEAT_MODE, CONF_REPEAT_AFTER,
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
        # Mock doesn't mutate entry, so only the first migration step (1.1→1.2) runs.
        # The 1.2→1.3 step is covered by test_migrates_version_1_2_to_1_3.
        self.assertEqual(mock_hass.config_entries.async_update_entry.call_count, 1)
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
        self.assertEqual(new_options["todo_offset_days"], 0)
        self.assertEqual(new_options[CONF_NOTIFICATION_INTERVAL], 2)

    async def test_migrates_version_1_2_to_1_3(self):
        entry = ConfigEntry(
            entry_id="test",
            version=1,
            minor_version=2,
            options={
                CONF_ACTIVE: True,
                CONF_TASK_INTERVAL_VALUE: 7,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
                "todo_offset_days": 3,
                "todo_offset_override": "input_number.my_offset",
                CONF_TODO_LISTS: [],
                CONF_NOTIFICATION_INTERVAL: 1,
            },
        )

        mock_hass = MagicMock()

        result = await async_migrate_entry(mock_hass, entry)

        self.assertTrue(result)
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
        self.assertEqual(call_kwargs["version"], 1)
        self.assertEqual(call_kwargs["minor_version"], 3)
        new_options = call_kwargs["options"]
        self.assertEqual(new_options[CONF_DUE_SOON_DAYS], 3)
        self.assertEqual(new_options[CONF_DUE_SOON_OVERRIDE], "input_number.my_offset")
        self.assertNotIn("todo_offset_days", new_options)
        self.assertNotIn("todo_offset_override", new_options)

    async def test_migrates_version_1_2_to_1_3_without_override(self):
        entry = ConfigEntry(
            entry_id="test",
            version=1,
            minor_version=2,
            options={
                CONF_ACTIVE: True,
                CONF_TASK_INTERVAL_VALUE: 7,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
                "todo_offset_days": 0,
                CONF_TODO_LISTS: [],
                CONF_NOTIFICATION_INTERVAL: 1,
            },
        )

        mock_hass = MagicMock()

        result = await async_migrate_entry(mock_hass, entry)

        self.assertTrue(result)
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
        new_options = call_kwargs["options"]
        self.assertEqual(new_options[CONF_DUE_SOON_DAYS], 0)
        self.assertIsNone(new_options[CONF_DUE_SOON_OVERRIDE])

    async def test_migrates_version_1_3_to_1_4(self):
        entry = ConfigEntry(
            entry_id="test",
            version=1,
            minor_version=3,
            options={
                CONF_ACTIVE: True,
                CONF_TASK_INTERVAL_VALUE: 7,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
                CONF_DUE_SOON_DAYS: 0,
                CONF_TODO_LISTS: [],
                CONF_NOTIFICATION_INTERVAL: 1,
            },
        )

        mock_hass = MagicMock()

        result = await async_migrate_entry(mock_hass, entry)

        self.assertTrue(result)
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
        self.assertEqual(call_kwargs["version"], 1)
        self.assertEqual(call_kwargs["minor_version"], 4)
        new_options = call_kwargs["options"]
        # repeat_mode defaults to repeat_after to preserve existing behaviour
        self.assertEqual(new_options[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_migrates_version_1_3_to_1_4_preserves_existing_repeat_mode(self):
        """If repeat_mode is already present it should not be overwritten."""
        from task_tracker.const import CONF_REPEAT_EVERY
        entry = ConfigEntry(
            entry_id="test",
            version=1,
            minor_version=3,
            options={
                CONF_ACTIVE: True,
                CONF_TASK_INTERVAL_VALUE: 7,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
                CONF_DUE_SOON_DAYS: 0,
                CONF_TODO_LISTS: [],
                CONF_NOTIFICATION_INTERVAL: 1,
                CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
            },
        )

        mock_hass = MagicMock()

        result = await async_migrate_entry(mock_hass, entry)

        self.assertTrue(result)
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
        new_options = call_kwargs["options"]
        self.assertEqual(new_options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)

    async def test_returns_true_for_current_version(self):
        entry = ConfigEntry(version=1, minor_version=5)
        mock_hass = MagicMock()
        result = await async_migrate_entry(mock_hass, entry)
        self.assertTrue(result)

    async def test_migrates_version_1_4_to_1_5_adds_repeat_every_fields(self):
        """1.4→1.5 should backfill repeat_every schedule fields to None."""
        from task_tracker.const import (
            CONF_REPEAT_EVERY_TYPE, CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL,
            CONF_REPEAT_MONTH_DAY, CONF_REPEAT_NTH_OCCURRENCE,
        )
        entry = ConfigEntry(
            entry_id="test",
            version=1,
            minor_version=4,
            options={
                CONF_ACTIVE: True,
                CONF_TASK_INTERVAL_VALUE: 7,
                CONF_TASK_INTERVAL_TYPE: CONF_DAY,
                CONF_DUE_SOON_DAYS: 0,
                CONF_TODO_LISTS: [],
                CONF_NOTIFICATION_INTERVAL: 1,
                CONF_REPEAT_MODE: CONF_REPEAT_AFTER,
            },
        )

        mock_hass = MagicMock()

        result = await async_migrate_entry(mock_hass, entry)

        self.assertTrue(result)
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
        self.assertEqual(call_kwargs["version"], 1)
        self.assertEqual(call_kwargs["minor_version"], 5)
        new_options = call_kwargs["options"]
        self.assertIsNone(new_options[CONF_REPEAT_EVERY_TYPE])
        self.assertIsNone(new_options[CONF_REPEAT_WEEKDAY])
        self.assertIsNone(new_options[CONF_REPEAT_WEEKS_INTERVAL])
        self.assertIsNone(new_options[CONF_REPEAT_MONTH_DAY])
        self.assertIsNone(new_options[CONF_REPEAT_NTH_OCCURRENCE])

    async def test_returns_false_for_future_major_version(self):
        entry = ConfigEntry(version=2, minor_version=1)
        mock_hass = MagicMock()
        result = await async_migrate_entry(mock_hass, entry)
        self.assertFalse(result)

    async def test_returns_false_for_future_minor_version(self):
        entry = ConfigEntry(version=1, minor_version=6)
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

