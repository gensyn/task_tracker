import sys
import unittest
from pathlib import Path

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.options_flow import validate_options
from homeassistant.const import CONF_ICON
from task_tracker.const import (
    CONF_ACTIVE, CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE,
    CONF_TAGS, CONF_TODO_LISTS, CONF_DUE_SOON_DAYS, CONF_NOTIFICATION_INTERVAL, CONF_DAY,
    CONF_ACTIVE_OVERRIDE, CONF_TASK_INTERVAL_OVERRIDE, CONF_DUE_SOON_OVERRIDE,
    CONF_REPEAT_MODE, CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_TYPE, CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH,
    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH,
    CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL, CONF_REPEAT_MONTH_DAY, CONF_REPEAT_NTH_OCCURRENCE,
    CONF_MONDAY, CONF_WEDNESDAY,
)

# Shared minimal base for repeat_after tests (same as before)
_BASE_REPEAT_AFTER = {
    CONF_TASK_INTERVAL_VALUE: 7,
    CONF_TASK_INTERVAL_TYPE: CONF_DAY,
}

# Shared minimal base for repeat_every tests
_BASE_REPEAT_EVERY_WEEKDAY = {
    CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY,
    CONF_REPEAT_WEEKDAY: CONF_WEDNESDAY,
    CONF_REPEAT_WEEKS_INTERVAL: 1,
}


class TestValidateOptionsRepeatAfter(unittest.IsolatedAsyncioTestCase):
    """Tests for validate_options in repeat_after mode (existing behaviour)."""

    async def test_active_defaults_to_true(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertTrue(result[CONF_ACTIVE])

    async def test_active_false_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_ACTIVE: False})
        self.assertFalse(result[CONF_ACTIVE])

    async def test_task_interval_value_minimum_is_one(self):
        result = await validate_options({CONF_TASK_INTERVAL_VALUE: 0, CONF_TASK_INTERVAL_TYPE: CONF_DAY})
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 1)

    async def test_task_interval_value_negative_becomes_one(self):
        result = await validate_options({CONF_TASK_INTERVAL_VALUE: -5, CONF_TASK_INTERVAL_TYPE: CONF_DAY})
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 1)

    async def test_task_interval_value_positive_preserved(self):
        result = await validate_options({CONF_TASK_INTERVAL_VALUE: 14, CONF_TASK_INTERVAL_TYPE: CONF_DAY})
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 14)

    async def test_task_interval_type_defaults_to_day(self):
        result = await validate_options({CONF_TASK_INTERVAL_VALUE: 7})
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], CONF_DAY)

    async def test_task_interval_type_preserved(self):
        result = await validate_options({CONF_TASK_INTERVAL_VALUE: 7, CONF_TASK_INTERVAL_TYPE: "week"})
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], "week")

    async def test_icon_defaults_to_calendar_question(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertEqual(result[CONF_ICON], "mdi:calendar-question")

    async def test_icon_gets_mdi_prefix(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_ICON: "calendar"})
        self.assertEqual(result[CONF_ICON], "mdi:calendar")

    async def test_icon_not_double_prefixed(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_ICON: "mdi:calendar"})
        self.assertEqual(result[CONF_ICON], "mdi:calendar")

    async def test_tags_defaults_to_empty_string(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertEqual(result[CONF_TAGS], "")

    async def test_tags_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_TAGS: "tag1,tag2"})
        self.assertEqual(result[CONF_TAGS], "tag1,tag2")

    async def test_todo_lists_defaults_to_empty_list(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertEqual(result[CONF_TODO_LISTS], [])

    async def test_todo_lists_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_TODO_LISTS: ["todo.list1"]})
        self.assertEqual(result[CONF_TODO_LISTS], ["todo.list1"])

    async def test_due_soon_days_defaults_to_zero(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertEqual(result[CONF_DUE_SOON_DAYS], 0)

    async def test_due_soon_days_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_DUE_SOON_DAYS: 3})
        self.assertEqual(result[CONF_DUE_SOON_DAYS], 3)

    async def test_notification_interval_minimum_is_one(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_NOTIFICATION_INTERVAL: 0})
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 1)

    async def test_notification_interval_negative_becomes_one(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_NOTIFICATION_INTERVAL: -3})
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 1)

    async def test_notification_interval_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_NOTIFICATION_INTERVAL: 5})
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 5)

    async def test_all_options_preserved(self):
        result = await validate_options({
            CONF_ACTIVE: False,
            CONF_TASK_INTERVAL_VALUE: 14,
            CONF_TASK_INTERVAL_TYPE: "week",
            CONF_ICON: "mdi:clock",
            CONF_TAGS: "tag1, tag2",
            CONF_TODO_LISTS: ["todo.list1"],
            CONF_DUE_SOON_DAYS: 3,
            CONF_NOTIFICATION_INTERVAL: 2,
        })
        self.assertFalse(result[CONF_ACTIVE])
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 14)
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], "week")
        self.assertEqual(result[CONF_ICON], "mdi:clock")
        self.assertEqual(result[CONF_TAGS], "tag1, tag2")
        self.assertEqual(result[CONF_TODO_LISTS], ["todo.list1"])
        self.assertEqual(result[CONF_DUE_SOON_DAYS], 3)
        self.assertEqual(result[CONF_NOTIFICATION_INTERVAL], 2)

    async def test_active_override_defaults_to_none(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertIsNone(result[CONF_ACTIVE_OVERRIDE])

    async def test_active_override_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_ACTIVE_OVERRIDE: "input_boolean.my_switch"})
        self.assertEqual(result[CONF_ACTIVE_OVERRIDE], "input_boolean.my_switch")

    async def test_active_override_empty_string_becomes_none(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_ACTIVE_OVERRIDE: ""})
        self.assertIsNone(result[CONF_ACTIVE_OVERRIDE])

    async def test_task_interval_override_defaults_to_none(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertIsNone(result[CONF_TASK_INTERVAL_OVERRIDE])

    async def test_task_interval_override_preserved(self):
        result = await validate_options({
            **_BASE_REPEAT_AFTER,
            CONF_TASK_INTERVAL_OVERRIDE: "input_number.my_interval",
        })
        self.assertEqual(result[CONF_TASK_INTERVAL_OVERRIDE], "input_number.my_interval")

    async def test_task_interval_override_empty_string_becomes_none(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_TASK_INTERVAL_OVERRIDE: ""})
        self.assertIsNone(result[CONF_TASK_INTERVAL_OVERRIDE])

    async def test_due_soon_override_defaults_to_none(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertIsNone(result[CONF_DUE_SOON_OVERRIDE])

    async def test_due_soon_override_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_DUE_SOON_OVERRIDE: "input_number.my_offset"})
        self.assertEqual(result[CONF_DUE_SOON_OVERRIDE], "input_number.my_offset")

    async def test_due_soon_override_empty_string_becomes_none(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_DUE_SOON_OVERRIDE: ""})
        self.assertIsNone(result[CONF_DUE_SOON_OVERRIDE])

    async def test_repeat_mode_defaults_to_repeat_after(self):
        result = await validate_options({**_BASE_REPEAT_AFTER})
        self.assertEqual(result[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_repeat_mode_repeat_after_preserved(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_REPEAT_MODE: CONF_REPEAT_AFTER})
        self.assertEqual(result[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_repeat_mode_invalid_value_defaults_to_repeat_after(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_REPEAT_MODE: "invalid_mode"})
        self.assertEqual(result[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_repeat_mode_empty_string_defaults_to_repeat_after(self):
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_REPEAT_MODE: ""})
        self.assertEqual(result[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_repeat_after_clears_repeat_every_fields(self):
        """repeat_after entries must have all repeat_every fields set to None."""
        result = await validate_options({**_BASE_REPEAT_AFTER, CONF_REPEAT_MODE: CONF_REPEAT_AFTER})
        self.assertIsNone(result[CONF_REPEAT_EVERY_TYPE])
        self.assertIsNone(result[CONF_REPEAT_WEEKDAY])
        self.assertIsNone(result[CONF_REPEAT_WEEKS_INTERVAL])
        self.assertIsNone(result[CONF_REPEAT_MONTH_DAY])
        self.assertIsNone(result[CONF_REPEAT_NTH_OCCURRENCE])


class TestValidateOptionsRepeatEvery(unittest.IsolatedAsyncioTestCase):
    """Tests for validate_options in repeat_every mode."""

    async def test_repeat_mode_repeat_every_preserved(self):
        result = await validate_options({**_BASE_REPEAT_EVERY_WEEKDAY})
        self.assertEqual(result[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)

    async def test_repeat_every_type_preserved(self):
        result = await validate_options({**_BASE_REPEAT_EVERY_WEEKDAY})
        self.assertEqual(result[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_WEEKDAY)

    async def test_repeat_weekday_preserved(self):
        result = await validate_options({**_BASE_REPEAT_EVERY_WEEKDAY})
        self.assertEqual(result[CONF_REPEAT_WEEKDAY], CONF_WEDNESDAY)

    async def test_repeat_weeks_interval_preserved(self):
        result = await validate_options({**_BASE_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL: 2})
        self.assertEqual(result[CONF_REPEAT_WEEKS_INTERVAL], 2)

    async def test_repeat_weeks_interval_minimum_is_one(self):
        result = await validate_options({**_BASE_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL: 0})
        self.assertEqual(result[CONF_REPEAT_WEEKS_INTERVAL], 1)

    async def test_repeat_month_day_preserved(self):
        result = await validate_options({
            CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
            CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH,
            CONF_REPEAT_MONTH_DAY: 15,
        })
        self.assertEqual(result[CONF_REPEAT_MONTH_DAY], 15)

    async def test_repeat_month_day_minimum_is_one(self):
        result = await validate_options({
            CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
            CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH,
            CONF_REPEAT_MONTH_DAY: 0,
        })
        self.assertEqual(result[CONF_REPEAT_MONTH_DAY], 1)

    async def test_repeat_month_day_maximum_is_31(self):
        result = await validate_options({
            CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
            CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH,
            CONF_REPEAT_MONTH_DAY: 50,
        })
        self.assertEqual(result[CONF_REPEAT_MONTH_DAY], 31)

    async def test_repeat_nth_occurrence_preserved(self):
        for value in ("1", "2", "3", "4", "last"):
            result = await validate_options({
                CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
                CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH,
                CONF_REPEAT_WEEKDAY: CONF_MONDAY,
                CONF_REPEAT_NTH_OCCURRENCE: value,
            })
            self.assertEqual(result[CONF_REPEAT_NTH_OCCURRENCE], value)

    async def test_repeat_nth_occurrence_invalid_defaults_to_first(self):
        result = await validate_options({
            CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
            CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH,
            CONF_REPEAT_WEEKDAY: CONF_MONDAY,
            CONF_REPEAT_NTH_OCCURRENCE: "99",
        })
        self.assertEqual(result[CONF_REPEAT_NTH_OCCURRENCE], "1")

    async def test_repeat_every_uses_default_interval_for_compat(self):
        """repeat_every entries should still have task_interval fields set to safe defaults."""
        result = await validate_options({**_BASE_REPEAT_EVERY_WEEKDAY})
        self.assertEqual(result[CONF_TASK_INTERVAL_VALUE], 7)
        self.assertEqual(result[CONF_TASK_INTERVAL_TYPE], CONF_DAY)
        self.assertIsNone(result[CONF_TASK_INTERVAL_OVERRIDE])

