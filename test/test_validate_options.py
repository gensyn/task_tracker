import sys
import unittest
from pathlib import Path

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.options_flow import validate_options
from task_tracker.const import (
    CONF_ACTIVE, CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE, CONF_ICON,
    CONF_TAGS, CONF_TODO_LISTS, CONF_TODO_OFFSET_DAYS, CONF_NOTIFICATION_INTERVAL, CONF_DAY,
    CONF_ACTIVE_OVERRIDE, CONF_TASK_INTERVAL_OVERRIDE, CONF_TODO_OFFSET_OVERRIDE,
)


class TestValidateOptions(unittest.IsolatedAsyncioTestCase):

    async def test_active_defaults_to_true(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertTrue(result[CONF_ACTIVE])

    async def test_active_false_preserved(self):
        result = await validate_options({
            CONF_ACTIVE: False,
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertFalse(result[CONF_ACTIVE])

    async def test_task_interval_value_minimum_is_one(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 0,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 1)

    async def test_task_interval_value_negative_becomes_one(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: -5,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 1)

    async def test_task_interval_value_positive_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 14,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 14)

    async def test_task_interval_type_defaults_to_day(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], CONF_DAY)

    async def test_task_interval_type_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: "week",
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], "week")

    async def test_icon_defaults_to_calendar_question(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_ICON], "mdi:calendar-question")

    async def test_icon_gets_mdi_prefix(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_ICON: "calendar",
        })
        self.assertEqual(result[CONF_ICON], "mdi:calendar")

    async def test_icon_not_double_prefixed(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_ICON: "mdi:calendar",
        })
        self.assertEqual(result[CONF_ICON], "mdi:calendar")

    async def test_tags_defaults_to_empty_string(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_TAGS], "")

    async def test_tags_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TAGS: "tag1,tag2",
        })
        self.assertEqual(result[CONF_TAGS], "tag1,tag2")

    async def test_todo_lists_defaults_to_empty_list(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_TODO_LISTS], [])

    async def test_todo_lists_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TODO_LISTS: ["todo.list1", "todo.list2"],
        })
        self.assertEqual(result[CONF_TODO_LISTS], ["todo.list1", "todo.list2"])

    async def test_todo_offset_days_defaults_to_zero(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result[CONF_TODO_OFFSET_DAYS], 0)

    async def test_todo_offset_days_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TODO_OFFSET_DAYS: 3,
        })
        self.assertEqual(result[CONF_TODO_OFFSET_DAYS], 3)

    async def test_notification_interval_minimum_is_one(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_NOTIFICATION_INTERVAL: 0,
        })
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 1)

    async def test_notification_interval_negative_becomes_one(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_NOTIFICATION_INTERVAL: -3,
        })
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 1)

    async def test_notification_interval_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_NOTIFICATION_INTERVAL: 5,
        })
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 5)

    async def test_all_options_preserved(self):
        result = await validate_options({
            CONF_ACTIVE: False,
            CONF_TASK_INTERVAL_VALUE: 14,
            CONF_TASK_INTERVAL_TYPE: "week",
            CONF_ICON: "mdi:clock",
            CONF_TAGS: "tag1, tag2",
            CONF_TODO_LISTS: ["todo.list1"],
            CONF_TODO_OFFSET_DAYS: 3,
            CONF_NOTIFICATION_INTERVAL: 2,
        })
        self.assertFalse(result[CONF_ACTIVE])
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 14)
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], "week")
        self.assertEqual(result[CONF_ICON], "mdi:clock")
        self.assertEqual(result[CONF_TAGS], "tag1, tag2")
        self.assertEqual(result[CONF_TODO_LISTS], ["todo.list1"])
        self.assertEqual(result[CONF_TODO_OFFSET_DAYS], 3)
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 2)

    async def test_active_override_defaults_to_none(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertIsNone(result[CONF_ACTIVE_OVERRIDE])

    async def test_active_override_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_ACTIVE_OVERRIDE: "input_boolean.my_switch",
        })
        self.assertEqual(result[CONF_ACTIVE_OVERRIDE], "input_boolean.my_switch")

    async def test_active_override_empty_string_becomes_none(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_ACTIVE_OVERRIDE: "",
        })
        self.assertIsNone(result[CONF_ACTIVE_OVERRIDE])

    async def test_task_interval_override_defaults_to_none(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertIsNone(result[CONF_TASK_INTERVAL_OVERRIDE])

    async def test_task_interval_override_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TASK_INTERVAL_OVERRIDE: "input_number.my_interval",
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_OVERRIDE], "input_number.my_interval")

    async def test_task_interval_override_empty_string_becomes_none(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TASK_INTERVAL_OVERRIDE: "",
        })
        self.assertIsNone(result[CONF_TASK_INTERVAL_OVERRIDE])

    async def test_todo_offset_override_defaults_to_none(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertIsNone(result[CONF_TODO_OFFSET_OVERRIDE])

    async def test_todo_offset_override_preserved(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TODO_OFFSET_OVERRIDE: "input_number.my_offset",
        })
        self.assertEqual(result[CONF_TODO_OFFSET_OVERRIDE], "input_number.my_offset")

    async def test_todo_offset_override_empty_string_becomes_none(self):
        result = await validate_options({
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TODO_OFFSET_OVERRIDE: "",
        })
        self.assertIsNone(result[CONF_TODO_OFFSET_OVERRIDE])
