import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.config_flow import TaskTrackerConfigFlow
from task_tracker.const import (
    CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE, CONF_DAY, CONF_WEEK,
    CONF_REPEAT_MODE, CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_TYPE, CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH,
    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH, CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH,
    CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL, CONF_REPEAT_MONTH_DAY, CONF_REPEAT_NTH_OCCURRENCE,
    CONF_REPEAT_DAYS_BEFORE_END,
    CONF_MONDAY, CONF_WEDNESDAY,
)


def make_flow():
    flow = TaskTrackerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": "user"}
    return flow


class TestTaskTrackerConfigFlowStep1User(unittest.IsolatedAsyncioTestCase):
    """Tests for the first step (name + repeat mode)."""

    async def test_shows_form_when_no_input(self):
        flow = make_flow()
        result = await flow.async_step_user(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")

    async def test_repeat_after_routes_to_repeat_after_step(self):
        flow = make_flow()
        result = await flow.async_step_user(user_input={"name": "Test", CONF_REPEAT_MODE: CONF_REPEAT_AFTER})
        # Should show the repeat_after form next
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_after")

    async def test_repeat_every_routes_to_repeat_every_step(self):
        flow = make_flow()
        result = await flow.async_step_user(user_input={"name": "Test", CONF_REPEAT_MODE: CONF_REPEAT_EVERY})
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every")

    async def test_name_is_accumulated(self):
        flow = make_flow()
        await flow.async_step_user(user_input={"name": "Clean Kitchen", CONF_REPEAT_MODE: CONF_REPEAT_AFTER})
        self.assertEqual(flow._user_input["name"], "Clean Kitchen")


class TestTaskTrackerConfigFlowRepeatAfter(unittest.IsolatedAsyncioTestCase):
    """Tests for the repeat_after sub-flow."""

    async def _start(self, name="Clean Kitchen"):
        flow = make_flow()
        await flow.async_step_user(user_input={"name": name, CONF_REPEAT_MODE: CONF_REPEAT_AFTER})
        return flow

    async def test_shows_form_when_no_input(self):
        flow = await self._start()
        result = await flow.async_step_repeat_after(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_after")

    async def test_creates_entry_with_valid_input(self):
        flow = await self._start("Clean Kitchen")
        result = await flow.async_step_repeat_after(user_input={
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Clean Kitchen")
        self.assertEqual(result["data"]["name"], "Clean Kitchen")

    async def test_created_entry_has_interval_options(self):
        flow = await self._start("Water Plants")
        result = await flow.async_step_repeat_after(user_input={
            CONF_TASK_INTERVAL_VALUE: 3,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
        })
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["options"][CONF_TASK_INTERVAL_VALUE], 3)
        self.assertEqual(result["options"][CONF_REPEAT_MODE], CONF_REPEAT_AFTER)

    async def test_created_entry_clears_repeat_every_fields(self):
        flow = await self._start("Vacuum")
        result = await flow.async_step_repeat_after(user_input={
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_WEEK,
        })
        options = result["options"]
        self.assertIsNone(options[CONF_REPEAT_EVERY_TYPE])
        self.assertIsNone(options[CONF_REPEAT_WEEKDAY])


class TestTaskTrackerConfigFlowRepeatEvery(unittest.IsolatedAsyncioTestCase):
    """Tests for the repeat_every sub-flow."""

    async def _step1(self, name="Trash"):
        flow = make_flow()
        await flow.async_step_user(user_input={"name": name, CONF_REPEAT_MODE: CONF_REPEAT_EVERY})
        return flow

    async def test_shows_repeat_every_type_form(self):
        flow = await self._step1()
        result = await flow.async_step_repeat_every(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every")

    async def test_weekday_type_routes_to_weekday_step(self):
        flow = await self._step1()
        result = await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_weekday")

    async def test_day_of_month_type_routes_to_day_of_month_step(self):
        flow = await self._step1()
        result = await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_day_of_month")

    async def test_weekday_of_month_type_routes_to_weekday_of_month_step(self):
        flow = await self._step1()
        result = await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_weekday_of_month")

    async def test_weekday_step_creates_entry(self):
        flow = await self._step1("Take Out Trash")
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY}
        )
        result = await flow.async_step_repeat_every_weekday(user_input={
            CONF_REPEAT_WEEKDAY: CONF_WEDNESDAY,
            CONF_REPEAT_WEEKS_INTERVAL: 1,
        })
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Take Out Trash")
        options = result["options"]
        self.assertEqual(options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(options[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_WEEKDAY)
        self.assertEqual(options[CONF_REPEAT_WEEKDAY], CONF_WEDNESDAY)
        self.assertEqual(options[CONF_REPEAT_WEEKS_INTERVAL], 1)

    async def test_day_of_month_step_creates_entry(self):
        flow = await self._step1("Pay Rent")
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH}
        )
        result = await flow.async_step_repeat_every_day_of_month(user_input={
            CONF_REPEAT_MONTH_DAY: 1,
        })
        self.assertEqual(result["type"], "create_entry")
        options = result["options"]
        self.assertEqual(options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(options[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_DAY_OF_MONTH)
        self.assertEqual(options[CONF_REPEAT_MONTH_DAY], 1)

    async def test_weekday_of_month_step_creates_entry(self):
        flow = await self._step1("HOA Meeting")
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH}
        )
        result = await flow.async_step_repeat_every_weekday_of_month(user_input={
            CONF_REPEAT_WEEKDAY: CONF_MONDAY,
            CONF_REPEAT_NTH_OCCURRENCE: "2",
        })
        self.assertEqual(result["type"], "create_entry")
        options = result["options"]
        self.assertEqual(options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(options[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH)
        self.assertEqual(options[CONF_REPEAT_WEEKDAY], CONF_MONDAY)
        self.assertEqual(options[CONF_REPEAT_NTH_OCCURRENCE], "2")

    async def test_weekday_step_shows_form_on_no_input(self):
        flow = await self._step1()
        await flow.async_step_repeat_every(user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY})
        result = await flow.async_step_repeat_every_weekday(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_weekday")

    async def test_day_of_month_step_shows_form_on_no_input(self):
        flow = await self._step1()
        await flow.async_step_repeat_every(user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAY_OF_MONTH})
        result = await flow.async_step_repeat_every_day_of_month(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_day_of_month")

    async def test_weekday_of_month_step_shows_form_on_no_input(self):
        flow = await self._step1()
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH}
        )
        result = await flow.async_step_repeat_every_weekday_of_month(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_weekday_of_month")

    async def test_days_before_end_of_month_type_routes_to_correct_step(self):
        flow = await self._step1()
        result = await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_days_before_end_of_month")

    async def test_days_before_end_of_month_step_shows_form_on_no_input(self):
        flow = await self._step1()
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH}
        )
        result = await flow.async_step_repeat_every_days_before_end_of_month(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "repeat_every_days_before_end_of_month")

    async def test_days_before_end_of_month_step_creates_entry(self):
        flow = await self._step1("Pay Taxes")
        await flow.async_step_repeat_every(
            user_input={CONF_REPEAT_EVERY_TYPE: CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH}
        )
        result = await flow.async_step_repeat_every_days_before_end_of_month(user_input={
            CONF_REPEAT_DAYS_BEFORE_END: 3,
        })
        self.assertEqual(result["type"], "create_entry")
        options = result["options"]
        self.assertEqual(options[CONF_REPEAT_MODE], CONF_REPEAT_EVERY)
        self.assertEqual(options[CONF_REPEAT_EVERY_TYPE], CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH)
        self.assertEqual(options[CONF_REPEAT_DAYS_BEFORE_END], 3)


class TestTaskTrackerConfigFlowOptionsFlowFactory(unittest.IsolatedAsyncioTestCase):

    async def test_options_flow_is_returned(self):
        from task_tracker.options_flow import TaskTrackerOptionsFlow
        result = TaskTrackerConfigFlow.async_get_options_flow(MagicMock())
        self.assertIsInstance(result, TaskTrackerOptionsFlow)
