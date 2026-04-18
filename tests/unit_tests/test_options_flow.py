"""Unit tests for TaskTrackerOptionsFlow."""
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from homeassistant.config_entries import ConfigEntry

from task_tracker.options_flow import TaskTrackerOptionsFlow
from homeassistant.const import CONF_ICON

from task_tracker.const import (
    CONF_ACTIVE, CONF_TAGS, CONF_TODO_LISTS,
    CONF_DUE_SOON_DAYS, CONF_DUE_SOON_OVERRIDE, CONF_NOTIFICATION_INTERVAL,
    CONF_ACTIVE_OVERRIDE,
    CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE, CONF_DAY,
    CONF_REPEAT_MODE, CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_TYPE,
    CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH,
    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH, CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH,
    CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL, CONF_REPEAT_MONTH_DAY,
    CONF_REPEAT_NTH_OCCURRENCE, CONF_REPEAT_DAYS_BEFORE_END,
    CONF_MONDAY, CONF_WEDNESDAY,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repeat_after_entry(**extra_options):
    """Return a ConfigEntry that represents a repeat_after task."""
    opts = {
        CONF_ACTIVE: True,
        CONF_REPEAT_MODE: CONF_REPEAT_AFTER,
        CONF_TASK_INTERVAL_VALUE: 7,
        CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        CONF_ICON: "mdi:calendar",
        CONF_TAGS: "",
        CONF_TODO_LISTS: [],
        CONF_DUE_SOON_DAYS: 0,
        CONF_NOTIFICATION_INTERVAL: 1,
        **extra_options,
    }
    return ConfigEntry(options=opts)


def _make_repeat_every_entry(repeat_every_type: str, **extra_options):
    """Return a ConfigEntry that represents a repeat_every task of the given sub-type."""
    from task_tracker.const import CONF_REPEAT_MONTH
    opts = {
        CONF_ACTIVE: True,
        CONF_REPEAT_MODE: CONF_REPEAT_EVERY,
        CONF_REPEAT_EVERY_TYPE: repeat_every_type,
        CONF_ICON: "mdi:calendar",
        CONF_TAGS: "",
        CONF_TODO_LISTS: [],
        CONF_DUE_SOON_DAYS: 0,
        CONF_NOTIFICATION_INTERVAL: 1,
        CONF_REPEAT_WEEKDAY: CONF_MONDAY,
        CONF_REPEAT_WEEKS_INTERVAL: 1,
        CONF_REPEAT_MONTH_DAY: 1,
        CONF_REPEAT_NTH_OCCURRENCE: "1",
        CONF_REPEAT_DAYS_BEFORE_END: 0,
        CONF_REPEAT_MONTH: 1,
        **extra_options,
    }
    return ConfigEntry(options=opts)


def _make_flow(config_entry: ConfigEntry) -> TaskTrackerOptionsFlow:
    flow = TaskTrackerOptionsFlow()
    flow.config_entry = config_entry
    return flow


# ---------------------------------------------------------------------------
# Tests: async_step_init routing
# ---------------------------------------------------------------------------

class TestOptionsFlowInitRouting(unittest.IsolatedAsyncioTestCase):
    """async_step_init should branch on the stored repeat_mode."""

    async def test_repeat_after_routes_to_options_repeat_after(self):
        """For repeat_after entries the combined options_repeat_after form is shown."""
        flow = _make_flow(_make_repeat_after_entry())
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_after")

    async def test_repeat_every_weekday_skips_init_form(self):
        """For repeat_every_weekday entries the init form is bypassed."""
        flow = _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_WEEKDAY))
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_weekday")

    async def test_repeat_every_day_of_month_skips_init_form(self):
        flow = _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_DAY_OF_MONTH))
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_day_of_month")

    async def test_repeat_every_weekday_of_month_skips_init_form(self):
        flow = _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH))
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_weekday_of_month")

    async def test_repeat_every_days_before_end_skips_init_form(self):
        flow = _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH))
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_days_before_end_of_month")

    async def test_repeat_every_unknown_subtype_falls_back_to_weekday_step(self):
        """An unrecognised repeat_every_type falls back to the weekday step."""
        flow = _make_flow(_make_repeat_every_entry("unknown_type"))
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_weekday")

    async def test_repeat_mode_and_type_pre_seeded_for_weekday(self):
        """repeat_mode and repeat_every_type should be in accumulated options before combined step."""
        flow = _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_WEEKDAY))
        await flow.async_step_init(user_input=None)
        self.assertEqual(flow._accumulated_options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(flow._accumulated_options[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_WEEKDAY)

    async def test_repeat_mode_and_type_pre_seeded_for_day_of_month(self):
        flow = _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_DAY_OF_MONTH))
        await flow.async_step_init(user_input=None)
        self.assertEqual(flow._accumulated_options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(flow._accumulated_options[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_DAY_OF_MONTH)


# ---------------------------------------------------------------------------
# Tests: repeat_after combined options step
# ---------------------------------------------------------------------------

class TestOptionsFlowRepeatAfterCombined(unittest.IsolatedAsyncioTestCase):
    """The repeat_after options flow uses a single combined step (options_repeat_after)."""

    def _make_flow(self):
        return _make_flow(_make_repeat_after_entry())

    async def test_init_routes_to_options_repeat_after(self):
        flow = self._make_flow()
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_after")

    async def test_shows_form_on_no_input(self):
        flow = self._make_flow()
        result = await flow.async_step_options_repeat_after(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_after")

    async def test_creates_entry_with_all_fields(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_AFTER
        result = await flow.async_step_options_repeat_after(user_input={
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
            CONF_TASK_INTERVAL_VALUE: 14,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result["type"], "create_entry")
        opts = result["data"]
        self.assertEqual(opts[CONF_TASK_INTERVAL_VALUE], 14)
        self.assertEqual(opts[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_repeat_mode_pre_seeded_from_init(self):
        """init pre-seeds CONF_REPEAT_MODE so validate_options sees it."""
        flow = self._make_flow()
        await flow.async_step_init(user_input=None)
        self.assertEqual(flow._accumulated_options[CONF_REPEAT_MODE], CONF_REPEAT_AFTER)


# ---------------------------------------------------------------------------
# Tests: validation in non-combined options steps (repeat_every sub-type
# validation in the options flow)
# ---------------------------------------------------------------------------

class TestOptionsFlowRepeatEveryDayOfMonthValidation(unittest.IsolatedAsyncioTestCase):
    """Validation tests for async_step_repeat_every_day_of_month in options flow."""

    async def _start(self):
        """Set up a flow with repeat_every/day_of_month accumulated options."""
        flow = _make_flow(_make_repeat_after_entry())
        flow._accumulated_options[CONF_ACTIVE] = True
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_ICON] = "mdi:calendar"
        flow._accumulated_options[CONF_TAGS] = ""
        flow._accumulated_options[CONF_TODO_LISTS] = []
        flow._accumulated_options[CONF_DUE_SOON_DAYS] = 0
        flow._accumulated_options[CONF_NOTIFICATION_INTERVAL] = 1
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH}
        )
        return flow

    async def test_rejects_month_day_zero(self):
        flow = await self._start()
        result = await flow.async_step_repeat_every_day_of_month(
            user_input={CONF_REPEAT_MONTH_DAY: 0}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"].get(CONF_REPEAT_MONTH_DAY), "invalid_month_day")

    async def test_rejects_month_day_above_31(self):
        flow = await self._start()
        result = await flow.async_step_repeat_every_day_of_month(
            user_input={CONF_REPEAT_MONTH_DAY: 32}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"].get(CONF_REPEAT_MONTH_DAY), "invalid_month_day")


class TestOptionsFlowRepeatEveryDaysBeforeEndValidation(unittest.IsolatedAsyncioTestCase):
    """Validation tests for async_step_repeat_every_days_before_end_of_month in options flow."""

    async def _start(self):
        flow = _make_flow(_make_repeat_after_entry())
        flow._accumulated_options[CONF_ACTIVE] = True
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_ICON] = "mdi:calendar"
        flow._accumulated_options[CONF_TAGS] = ""
        flow._accumulated_options[CONF_TODO_LISTS] = []
        flow._accumulated_options[CONF_DUE_SOON_DAYS] = 0
        flow._accumulated_options[CONF_NOTIFICATION_INTERVAL] = 1
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH}
        )
        return flow

    async def test_rejects_negative(self):
        flow = await self._start()
        result = await flow.async_step_repeat_every_days_before_end_of_month(
            user_input={CONF_REPEAT_DAYS_BEFORE_END: -1}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"].get(CONF_REPEAT_DAYS_BEFORE_END), "invalid_days_before_end")

    async def test_rejects_above_30(self):
        flow = await self._start()
        result = await flow.async_step_repeat_every_days_before_end_of_month(
            user_input={CONF_REPEAT_DAYS_BEFORE_END: 31}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"].get(CONF_REPEAT_DAYS_BEFORE_END), "invalid_days_before_end")


# ---------------------------------------------------------------------------
# Tests: combined options step – repeat_every_weekday
# ---------------------------------------------------------------------------

class TestOptionsRepeatEveryWeekday(unittest.IsolatedAsyncioTestCase):

    def _make_flow(self):
        return _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_WEEKDAY))

    async def test_shows_form_on_no_input(self):
        flow = self._make_flow()
        result = await flow.async_step_options_repeat_every_weekday(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_weekday")

    async def test_creates_entry_with_mode_specific_fields(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_WEEKDAY
        result = await flow.async_step_options_repeat_every_weekday(user_input={
            CONF_REPEAT_WEEKDAY: CONF_WEDNESDAY,
            CONF_REPEAT_WEEKS_INTERVAL: 2,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:broom",
            CONF_TAGS: "cleaning",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 3,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "create_entry")
        opts = result["data"]
        self.assertEqual(opts[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(opts[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_WEEKDAY)
        self.assertEqual(opts[CONF_REPEAT_WEEKDAY], CONF_WEDNESDAY)
        self.assertEqual(opts[CONF_REPEAT_WEEKS_INTERVAL], 2)
        self.assertEqual(opts[CONF_DUE_SOON_DAYS], 3)
        self.assertEqual(opts[CONF_TAGS], "cleaning")

    async def test_repeat_mode_not_changeable(self):
        """repeat_mode must remain CONF_REPEAT_EVERY even if not in the form."""
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_WEEKDAY
        result = await flow.async_step_options_repeat_every_weekday(user_input={
            CONF_REPEAT_WEEKDAY: CONF_MONDAY,
            CONF_REPEAT_WEEKS_INTERVAL: 1,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["data"][CONF_REPEAT_MODE], CONF_REPEAT_EVERY)

    async def test_routed_from_init(self):
        """init for a weekday entry should land on options_repeat_every_weekday."""
        flow = self._make_flow()
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["step_id"], "options_repeat_every_weekday")


# ---------------------------------------------------------------------------
# Tests: combined options step – repeat_every_day_of_month
# ---------------------------------------------------------------------------

class TestOptionsRepeatEveryDayOfMonth(unittest.IsolatedAsyncioTestCase):

    def _make_flow(self):
        return _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_DAY_OF_MONTH))

    async def test_shows_form_on_no_input(self):
        flow = self._make_flow()
        result = await flow.async_step_options_repeat_every_day_of_month(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_day_of_month")

    async def test_creates_entry_with_correct_options(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAY_OF_MONTH
        result = await flow.async_step_options_repeat_every_day_of_month(user_input={
            CONF_REPEAT_MONTH_DAY: 15,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 2,
        })
        self.assertEqual(result["type"], "create_entry")
        opts = result["data"]
        self.assertEqual(opts[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_DAY_OF_MONTH)
        self.assertEqual(opts[CONF_REPEAT_MONTH_DAY], 15)
        self.assertEqual(opts[CONF_NOTIFICATION_INTERVAL], 2)

    async def test_rejects_month_day_zero(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAY_OF_MONTH
        result = await flow.async_step_options_repeat_every_day_of_month(user_input={
            CONF_REPEAT_MONTH_DAY: 0,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_MONTH_DAY, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_MONTH_DAY], "invalid_month_day")

    async def test_rejects_month_day_above_31(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAY_OF_MONTH
        result = await flow.async_step_options_repeat_every_day_of_month(user_input={
            CONF_REPEAT_MONTH_DAY: 32,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_MONTH_DAY, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_MONTH_DAY], "invalid_month_day")

    async def test_routed_from_init(self):
        flow = self._make_flow()
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["step_id"], "options_repeat_every_day_of_month")


# ---------------------------------------------------------------------------
# Tests: combined options step – repeat_every_weekday_of_month
# ---------------------------------------------------------------------------

class TestOptionsRepeatEveryWeekdayOfMonth(unittest.IsolatedAsyncioTestCase):

    def _make_flow(self):
        return _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH))

    async def test_shows_form_on_no_input(self):
        flow = self._make_flow()
        result = await flow.async_step_options_repeat_every_weekday_of_month(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_weekday_of_month")

    async def test_creates_entry_with_correct_options(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH
        result = await flow.async_step_options_repeat_every_weekday_of_month(user_input={
            CONF_REPEAT_WEEKDAY: CONF_MONDAY,
            CONF_REPEAT_NTH_OCCURRENCE: "2",
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "create_entry")
        opts = result["data"]
        self.assertEqual(opts[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH)
        self.assertEqual(opts[CONF_REPEAT_WEEKDAY], CONF_MONDAY)
        self.assertEqual(opts[CONF_REPEAT_NTH_OCCURRENCE], "2")

    async def test_routed_from_init(self):
        flow = self._make_flow()
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["step_id"], "options_repeat_every_weekday_of_month")


# ---------------------------------------------------------------------------
# Tests: combined options step – repeat_every_days_before_end_of_month
# ---------------------------------------------------------------------------

class TestOptionsRepeatEveryDaysBeforeEndOfMonth(unittest.IsolatedAsyncioTestCase):

    def _make_flow(self):
        return _make_flow(_make_repeat_every_entry(CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH))

    async def test_shows_form_on_no_input(self):
        flow = self._make_flow()
        result = await flow.async_step_options_repeat_every_days_before_end_of_month(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_days_before_end_of_month")

    async def test_creates_entry_with_correct_options(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH
        result = await flow.async_step_options_repeat_every_days_before_end_of_month(user_input={
            CONF_REPEAT_DAYS_BEFORE_END: 5,
            CONF_ACTIVE: False,
            CONF_ICON: "mdi:cash",
            CONF_TAGS: "finance",
            CONF_TODO_LISTS: ["todo.my_list"],
            CONF_DUE_SOON_DAYS: 7,
            CONF_NOTIFICATION_INTERVAL: 3,
        })
        self.assertEqual(result["type"], "create_entry")
        opts = result["data"]
        self.assertEqual(opts[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH)
        self.assertEqual(opts[CONF_REPEAT_DAYS_BEFORE_END], 5)
        self.assertFalse(opts[CONF_ACTIVE])
        self.assertEqual(opts[CONF_DUE_SOON_DAYS], 7)
        self.assertEqual(opts[CONF_TAGS], "finance")

    async def test_routed_from_init(self):
        flow = self._make_flow()
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["step_id"], "options_repeat_every_days_before_end_of_month")

    async def test_common_fields_persisted(self):
        """Active, icon, tags, todo-lists, due_soon, and notification_interval are saved."""
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH
        result = await flow.async_step_options_repeat_every_days_before_end_of_month(user_input={
            CONF_REPEAT_DAYS_BEFORE_END: 0,
            CONF_ACTIVE: True,
            CONF_ACTIVE_OVERRIDE: "input_boolean.toggle",
            CONF_ICON: "mdi:star",
            CONF_TAGS: "tag1,tag2",
            CONF_TODO_LISTS: ["todo.list_a"],
            CONF_DUE_SOON_DAYS: 2,
            CONF_DUE_SOON_OVERRIDE: "input_number.threshold",
            CONF_NOTIFICATION_INTERVAL: 5,
        })
        opts = result["data"]
        self.assertTrue(opts[CONF_ACTIVE])
        self.assertEqual(opts[CONF_ACTIVE_OVERRIDE], "input_boolean.toggle")
        self.assertIn("star", opts[CONF_ICON])
        self.assertEqual(opts[CONF_TAGS], "tag1,tag2")
        self.assertEqual(opts[CONF_TODO_LISTS], ["todo.list_a"])
        self.assertEqual(opts[CONF_DUE_SOON_DAYS], 2)
        self.assertEqual(opts[CONF_DUE_SOON_OVERRIDE], "input_number.threshold")
        self.assertEqual(opts[CONF_NOTIFICATION_INTERVAL], 5)

    async def test_rejects_days_before_end_negative(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH
        result = await flow.async_step_options_repeat_every_days_before_end_of_month(user_input={
            CONF_REPEAT_DAYS_BEFORE_END: -1,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_DAYS_BEFORE_END, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_DAYS_BEFORE_END], "invalid_days_before_end")

    async def test_rejects_days_before_end_above_30(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH
        result = await flow.async_step_options_repeat_every_days_before_end_of_month(user_input={
            CONF_REPEAT_DAYS_BEFORE_END: 31,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_DAYS_BEFORE_END, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_DAYS_BEFORE_END], "invalid_days_before_end")


# ---------------------------------------------------------------------------
# Tests: repeat_every_specific_date in options flow
# ---------------------------------------------------------------------------

class TestOptionsFlowRepeatEverySpecificDateInit(unittest.IsolatedAsyncioTestCase):
    """async_step_init routing for repeat_every_specific_date entries."""

    async def test_specific_date_subtype_routes_to_correct_options_step(self):
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE, CONF_REPEAT_MONTH
        entry = _make_repeat_every_entry(
            CONF_REPEAT_EVERY_SPECIFIC_DATE,
            **{CONF_REPEAT_MONTH: 3, CONF_REPEAT_MONTH_DAY: 15}
        )
        flow = _make_flow(entry)
        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_specific_date")


class TestOptionsFlowRepeatEverySpecificDateCombined(unittest.IsolatedAsyncioTestCase):
    """Tests for async_step_options_repeat_every_specific_date."""

    def _make_flow(self):
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE, CONF_REPEAT_MONTH
        entry = _make_repeat_every_entry(
            CONF_REPEAT_EVERY_SPECIFIC_DATE,
            **{CONF_REPEAT_MONTH: 3, CONF_REPEAT_MONTH_DAY: 15}
        )
        return _make_flow(entry)

    async def test_shows_form_on_no_input(self):
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_SPECIFIC_DATE
        result = await flow.async_step_options_repeat_every_specific_date(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "options_repeat_every_specific_date")

    async def test_creates_entry_with_valid_input(self):
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE, CONF_REPEAT_MONTH
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_SPECIFIC_DATE
        result = await flow.async_step_options_repeat_every_specific_date(user_input={
            CONF_REPEAT_MONTH: 6,
            CONF_REPEAT_MONTH_DAY: 20,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "create_entry")
        opts = result["data"]
        self.assertEqual(opts[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_SPECIFIC_DATE)
        self.assertEqual(opts[CONF_REPEAT_MONTH], 6)
        self.assertEqual(opts[CONF_REPEAT_MONTH_DAY], 20)

    async def test_rejects_invalid_month_zero(self):
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE, CONF_REPEAT_MONTH
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_SPECIFIC_DATE
        result = await flow.async_step_options_repeat_every_specific_date(user_input={
            CONF_REPEAT_MONTH: 0,
            CONF_REPEAT_MONTH_DAY: 15,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_MONTH, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_MONTH], "invalid_month")

    async def test_rejects_invalid_month_above_twelve(self):
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE, CONF_REPEAT_MONTH
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_SPECIFIC_DATE
        result = await flow.async_step_options_repeat_every_specific_date(user_input={
            CONF_REPEAT_MONTH: 13,
            CONF_REPEAT_MONTH_DAY: 1,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_MONTH, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_MONTH], "invalid_month")

    async def test_rejects_invalid_day_above_31(self):
        from task_tracker.const import CONF_REPEAT_EVERY_SPECIFIC_DATE, CONF_REPEAT_MONTH
        flow = self._make_flow()
        flow._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
        flow._accumulated_options[CONF_REPEAT_EVERY_TYPE] = CONF_REPEAT_EVERY_SPECIFIC_DATE
        result = await flow.async_step_options_repeat_every_specific_date(user_input={
            CONF_REPEAT_MONTH: 3,
            CONF_REPEAT_MONTH_DAY: 32,
            CONF_ACTIVE: True,
            CONF_ICON: "mdi:calendar",
            CONF_TAGS: "",
            CONF_TODO_LISTS: [],
            CONF_DUE_SOON_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_REPEAT_MONTH_DAY, result.get("errors", {}))
        self.assertEqual(result["errors"][CONF_REPEAT_MONTH_DAY], "invalid_month_day")
