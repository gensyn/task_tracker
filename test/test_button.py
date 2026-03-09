import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.button import get_sensor


class TestButtonGetSensor(unittest.IsolatedAsyncioTestCase):

    async def test_returns_sensor_when_exactly_one_sensor_found(self):
        from task_tracker.sensor import TaskTrackerSensor
        mock_sensor = MagicMock(spec=TaskTrackerSensor)

        mock_entry = MagicMock()
        mock_entry.entity_id = "sensor.task_tracker_my_task"

        mock_registry = MagicMock()
        mock_hass = MagicMock()
        mock_hass.data = {"entity_components": {"sensor": MagicMock()}}
        mock_hass.data["entity_components"]["sensor"].get_entity.return_value = mock_sensor

        import homeassistant.helpers.entity_registry as entity_registry
        original_async_get = entity_registry.async_get
        original_async_entries = entity_registry.async_entries_for_device

        entity_registry.async_get = lambda hass: mock_registry
        entity_registry.async_entries_for_device = lambda reg, dev_id: [mock_entry]

        try:
            result = await get_sensor(mock_hass, "some_device_id")
            self.assertEqual(result, mock_sensor)
        finally:
            entity_registry.async_get = original_async_get
            entity_registry.async_entries_for_device = original_async_entries

    async def test_raises_when_no_sensors_found(self):
        mock_registry = MagicMock()
        mock_hass = MagicMock()

        import homeassistant.helpers.entity_registry as entity_registry
        original_async_get = entity_registry.async_get
        original_async_entries = entity_registry.async_entries_for_device

        entity_registry.async_get = lambda hass: mock_registry
        entity_registry.async_entries_for_device = lambda reg, dev_id: []

        try:
            with self.assertRaises(ValueError):
                await get_sensor(mock_hass, "some_device_id")
        finally:
            entity_registry.async_get = original_async_get
            entity_registry.async_entries_for_device = original_async_entries

    async def test_raises_when_multiple_sensors_found(self):
        mock_entry1 = MagicMock()
        mock_entry1.entity_id = "sensor.task_tracker_task1"
        mock_entry2 = MagicMock()
        mock_entry2.entity_id = "sensor.task_tracker_task2"

        mock_registry = MagicMock()
        mock_hass = MagicMock()

        import homeassistant.helpers.entity_registry as entity_registry
        original_async_get = entity_registry.async_get
        original_async_entries = entity_registry.async_entries_for_device

        entity_registry.async_get = lambda hass: mock_registry
        entity_registry.async_entries_for_device = lambda reg, dev_id: [mock_entry1, mock_entry2]

        try:
            with self.assertRaises(ValueError):
                await get_sensor(mock_hass, "some_device_id")
        finally:
            entity_registry.async_get = original_async_get
            entity_registry.async_entries_for_device = original_async_entries
