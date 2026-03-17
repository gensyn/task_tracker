import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.config_flow import TaskTrackerConfigFlow
from task_tracker.const import CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE, CONF_DAY


def make_flow():
    flow = TaskTrackerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": "user"}
    return flow


class TestTaskTrackerConfigFlowAsyncStepUser(unittest.IsolatedAsyncioTestCase):

    async def test_shows_form_when_no_input(self):
        flow = make_flow()
        result = await flow.async_step_user(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")

    async def test_creates_entry_with_valid_input(self):
        flow = make_flow()
        user_input = {
            "name": "Clean Kitchen",
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        }
        result = await flow.async_step_user(user_input=user_input)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Clean Kitchen")
        self.assertEqual(result["data"]["name"], "Clean Kitchen")

    async def test_created_entry_has_options(self):
        flow = make_flow()
        user_input = {
            "name": "Water Plants",
            CONF_TASK_INTERVAL_VALUE: 3,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        }
        result = await flow.async_step_user(user_input=user_input)
        self.assertEqual(result["type"], "create_entry")
        self.assertIn("options", result)
        self.assertEqual(result["options"][CONF_TASK_INTERVAL_VALUE], 3)

    async def test_options_flow_is_returned(self):
        from task_tracker.options_flow import TaskTrackerOptionsFlow
        result = TaskTrackerConfigFlow.async_get_options_flow(MagicMock())
        self.assertIsInstance(result, TaskTrackerOptionsFlow)
