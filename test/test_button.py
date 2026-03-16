import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.button import TaskTrackerButton
from task_tracker.const import DOMAIN
from task_tracker.coordinator import TaskTrackerCoordinator


class TestTaskTrackerButtonPress(unittest.IsolatedAsyncioTestCase):

    async def test_press_calls_coordinator_mark_as_done(self):
        coordinator = MagicMock(spec=TaskTrackerCoordinator)
        coordinator.async_mark_as_done = AsyncMock()

        button = TaskTrackerButton("My Task", "entry1", MagicMock())
        button.hass = MagicMock()
        button.hass.data = {DOMAIN: {"entry1": coordinator}}

        await button.async_press()

        coordinator.async_mark_as_done.assert_called_once()

    async def test_press_uses_correct_entry_id(self):
        coordinator_a = MagicMock(spec=TaskTrackerCoordinator)
        coordinator_a.async_mark_as_done = AsyncMock()
        coordinator_b = MagicMock(spec=TaskTrackerCoordinator)
        coordinator_b.async_mark_as_done = AsyncMock()

        button = TaskTrackerButton("Task B", "entry_b", MagicMock())
        button.hass = MagicMock()
        button.hass.data = {DOMAIN: {"entry_a": coordinator_a, "entry_b": coordinator_b}}

        await button.async_press()

        coordinator_b.async_mark_as_done.assert_called_once()
        coordinator_a.async_mark_as_done.assert_not_called()

