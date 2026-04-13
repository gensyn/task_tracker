import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

absolute_mock_path = str(Path(__file__).parent / "homeassistant_mock")
sys.path.insert(0, absolute_mock_path)

absolute_plugin_path = str(Path(__file__).parent.parent.parent.parent.absolute())
sys.path.insert(0, absolute_plugin_path)

from task_tracker.coordinator import TaskTrackerCoordinator
from task_tracker.sensor import TaskTrackerSensor
from task_tracker.const import (
    CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR,
    CONST_DUE, CONST_DUE_SOON, CONST_DONE, CONST_INACTIVE,
    CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH, CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH,
    CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY,
)


def make_sensor(
    entry_name="Test Task",
    task_interval_value=7,
    task_interval_type=CONF_DAY,
    notification_interval=1,
    todo_lists=None,
    due_soon_days=0,
    tags="",
    active=True,
    icon="mdi:calendar",
    entry_id="abc123",
    hass=None,
    active_override=None,
    task_interval_override=None,
    due_soon_override=None,
    repeat_mode=CONF_REPEAT_AFTER,
    repeat_every_type=None,
    repeat_weekday=None,
    repeat_weeks_interval=1,
    repeat_month_day=1,
    repeat_nth_occurrence="1",
    coordinator=None,
):
    if hass is None:
        hass = MagicMock()
    if coordinator is None:
        coordinator = TaskTrackerCoordinator(
            entry_id,
            repeat_mode=repeat_mode,
            repeat_every_type=repeat_every_type,
            repeat_weekday=repeat_weekday,
            repeat_weeks_interval=repeat_weeks_interval,
            repeat_month_day=repeat_month_day,
            repeat_nth_occurrence=repeat_nth_occurrence,
        )
    return TaskTrackerSensor(
        coordinator=coordinator,
        entry_name=entry_name,
        task_interval_value=task_interval_value,
        task_interval_type=task_interval_type,
        notification_interval=notification_interval,
        todo_lists=todo_lists if todo_lists is not None else [],
        due_soon_days=due_soon_days,
        tags=tags,
        active=active,
        icon=icon,
        entry_id=entry_id,
        hass=hass,
        active_override=active_override,
        task_interval_override=task_interval_override,
        due_soon_override=due_soon_override,
    )


class TestTaskTrackerSensorInit(unittest.TestCase):

    def test_init_sets_entry_name(self):
        sensor = make_sensor(entry_name="My Task")
        self.assertEqual(sensor.entry_name, "My Task")

    def test_init_sets_task_interval_value(self):
        sensor = make_sensor(task_interval_value=14)
        self.assertEqual(sensor.task_interval_value, 14)

    def test_init_sets_task_interval_type(self):
        sensor = make_sensor(task_interval_type=CONF_WEEK)
        self.assertEqual(sensor.task_interval_type, CONF_WEEK)

    def test_init_sets_active(self):
        sensor = make_sensor(active=False)
        self.assertFalse(sensor.active)

    def test_init_last_done_defaults_to_epoch(self):
        sensor = make_sensor()
        self.assertEqual(sensor.coordinator.last_done, date(1970, 1, 1))

    def test_init_splits_tags(self):
        sensor = make_sensor(tags="tag1, tag2; tag3")
        self.assertIn("tag1", sensor.tags)
        self.assertIn("tag2", sensor.tags)
        self.assertIn("tag3", sensor.tags)

    def test_init_empty_tags(self):
        sensor = make_sensor(tags="")
        self.assertEqual(sensor.tags, [])

    def test_init_entity_id_generated(self):
        sensor = make_sensor(entry_name="My Task")
        self.assertIn("my_task", sensor.entity_id)

    def test_init_unique_id(self):
        sensor = make_sensor(entry_id="xyz")
        self.assertEqual(sensor._attr_unique_id, "xyz_status")


class TestTaskTrackerSensorUpdate(unittest.IsolatedAsyncioTestCase):

    async def _run_update(self, sensor):
        with patch.object(sensor, "async_write_ha_state"):
            with patch.object(sensor, "async_sync_todo_list", new_callable=AsyncMock):
                await sensor.async_update()

    async def test_status_done_when_not_yet_due(self):
        sensor = make_sensor(task_interval_value=30)
        sensor.coordinator.last_done = date.today()
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DONE)

    async def test_status_due_when_overdue(self):
        sensor = make_sensor(task_interval_value=7)
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DUE)

    async def test_status_due_soon_when_within_threshold(self):
        sensor = make_sensor(task_interval_value=10, due_soon_days=3)
        sensor.coordinator.last_done = date.today()
        await self._run_update(sensor)
        # due_in will be 10, which is > 3, so state should be DONE
        self.assertEqual(sensor._attr_native_value, CONST_DONE)

    async def test_status_due_soon_within_days(self):
        from datetime import timedelta
        sensor = make_sensor(task_interval_value=7, due_soon_days=5)
        # Set last_done so that due_date is 3 days from now (within 5 day threshold)
        sensor.coordinator.last_done = date.today() - timedelta(days=4)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DUE_SOON)

    async def test_status_not_due_soon_when_threshold_is_zero(self):
        from datetime import timedelta
        sensor = make_sensor(task_interval_value=7, due_soon_days=0)
        sensor.coordinator.last_done = date.today() - timedelta(days=4)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DONE)

    async def test_status_due_overrides_due_soon(self):
        sensor = make_sensor(task_interval_value=7, due_soon_days=5)
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DUE)
        sensor = make_sensor(active=False, task_interval_value=7)
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_INACTIVE)

    async def test_due_date_calculated_in_days(self):
        sensor = make_sensor(task_interval_value=7, task_interval_type=CONF_DAY)
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        from datetime import timedelta
        self.assertEqual(sensor.due_date, date(2024, 1, 8))

    async def test_due_date_calculated_in_weeks(self):
        sensor = make_sensor(task_interval_value=2, task_interval_type=CONF_WEEK)
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2024, 1, 15))

    async def test_due_date_calculated_in_months(self):
        sensor = make_sensor(task_interval_value=1, task_interval_type=CONF_MONTH)
        sensor.coordinator.last_done = date(2024, 1, 15)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2024, 2, 15))

    async def test_due_date_calculated_in_years(self):
        sensor = make_sensor(task_interval_value=1, task_interval_type=CONF_YEAR)
        sensor.coordinator.last_done = date(2024, 1, 15)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2025, 1, 15))

    async def test_attributes_contain_last_done(self):
        sensor = make_sensor()
        sensor.coordinator.last_done = date(2024, 3, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_extra_state_attributes["last_done"], "2024-03-01")

    async def test_attributes_contain_due_date(self):
        sensor = make_sensor(task_interval_value=7)
        sensor.coordinator.last_done = date(2024, 3, 1)
        await self._run_update(sensor)
        self.assertIn("due_date", sensor._attr_extra_state_attributes)

    async def test_attributes_contain_due_in(self):
        sensor = make_sensor(task_interval_value=30)
        sensor.coordinator.last_done = date.today()
        await self._run_update(sensor)
        self.assertIn("due_in", sensor._attr_extra_state_attributes)
        self.assertGreater(sensor._attr_extra_state_attributes["due_in"], 0)

    async def test_attributes_contain_overdue_by(self):
        sensor = make_sensor(task_interval_value=7)
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertIn("overdue_by", sensor._attr_extra_state_attributes)
        self.assertGreater(sensor._attr_extra_state_attributes["overdue_by"], 0)

    async def test_sync_called_for_each_todo_list(self):
        sensor = make_sensor(todo_lists=["todo.list1", "todo.list2"])
        sensor.coordinator.last_done = date.today()
        with patch.object(sensor, "async_write_ha_state"):
            with patch.object(sensor, "async_sync_todo_list", new_callable=AsyncMock) as mock_sync:
                await sensor.async_update()
        self.assertEqual(mock_sync.call_count, 2)
        mock_sync.assert_any_call("todo.list1")
        mock_sync.assert_any_call("todo.list2")


class TestTaskTrackerSensorFilterStateChanges(unittest.TestCase):

    def _make_event_data(self, entity_id, old_state, new_state):
        return {
            "entity_id": entity_id,
            "old_state": MagicMock(state=old_state),
            "new_state": MagicMock(state=new_state),
        }

    def test_returns_true_for_relevant_entity_with_decreased_state(self):
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = self._make_event_data("todo.my_list", "5", "3")
        self.assertTrue(sensor._filter_state_changes(event_data))

    def test_returns_false_for_irrelevant_entity(self):
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = self._make_event_data("todo.other_list", "5", "3")
        self.assertFalse(sensor._filter_state_changes(event_data))

    def test_returns_false_when_state_increases(self):
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = self._make_event_data("todo.my_list", "3", "5")
        self.assertFalse(sensor._filter_state_changes(event_data))

    def test_returns_false_when_state_unchanged(self):
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = self._make_event_data("todo.my_list", "3", "3")
        self.assertFalse(sensor._filter_state_changes(event_data))

    def test_returns_false_when_old_state_missing(self):
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = {
            "entity_id": "todo.my_list",
            "old_state": None,
            "new_state": MagicMock(state="3"),
        }
        self.assertFalse(sensor._filter_state_changes(event_data))

    def test_returns_false_when_new_state_missing(self):
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = {
            "entity_id": "todo.my_list",
            "old_state": MagicMock(state="5"),
            "new_state": None,
        }
        self.assertFalse(sensor._filter_state_changes(event_data))

    def test_returns_true_for_multi_digit_decrease(self):
        """Numeric comparison must be used — string comparison gives wrong results.

        ``"5" < "10"`` is ``False`` lexicographically even though 5 < 10 as integers.
        If only string comparison is used this test would fail.
        """
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = self._make_event_data("todo.my_list", "10", "5")
        self.assertTrue(sensor._filter_state_changes(event_data))

    def test_returns_false_for_non_numeric_state(self):
        """Non-numeric todo list states (e.g. 'unavailable') should not trigger."""
        sensor = make_sensor(todo_lists=["todo.my_list"])
        event_data = self._make_event_data("todo.my_list", "unavailable", "unavailable")
        self.assertFalse(sensor._filter_state_changes(event_data))


class TestTaskTrackerSensorSyncTodoList(unittest.IsolatedAsyncioTestCase):

    async def test_adds_item_when_due_and_not_exists(self):
        sensor = make_sensor(task_interval_value=7, due_soon_days=0)
        sensor.coordinator.last_done = date(1970, 1, 1)
        sensor.due_in = 0
        sensor.due_date = date(1970, 1, 8)
        with patch.object(sensor, "async_get_item_from_todo_list", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_add_item_to_todo_list", new_callable=AsyncMock) as mock_add:
                await sensor.async_sync_todo_list("todo.list1")
        mock_add.assert_called_once_with("todo.list1")

    async def test_updates_item_when_due_and_exists(self):
        sensor = make_sensor(task_interval_value=7, due_soon_days=0)
        sensor.due_in = 0
        sensor.due_date = date(1970, 1, 8)
        existing = {"summary": "Test Task", "status": "needs_action"}
        with patch.object(sensor, "async_get_item_from_todo_list", new_callable=AsyncMock, return_value=existing):
            with patch.object(sensor, "async_update_item_in_todo_list", new_callable=AsyncMock) as mock_update:
                await sensor.async_sync_todo_list("todo.list1")
        mock_update.assert_called_once_with("todo.list1")

    async def test_removes_item_when_not_due_and_exists(self):
        sensor = make_sensor(task_interval_value=7, due_soon_days=0)
        sensor.due_in = 10
        sensor.due_date = date.today()
        existing = {"summary": "Test Task", "status": "needs_action"}
        with patch.object(sensor, "async_get_item_from_todo_list", new_callable=AsyncMock, return_value=existing):
            with patch.object(sensor, "async_remove_item_from_todo_list", new_callable=AsyncMock) as mock_remove:
                await sensor.async_sync_todo_list("todo.list1")
        mock_remove.assert_called_once_with("todo.list1")

    async def test_no_action_when_not_due_and_not_exists(self):
        sensor = make_sensor(task_interval_value=7, due_soon_days=0)
        sensor.due_in = 10
        sensor.due_date = date.today()
        with patch.object(sensor, "async_get_item_from_todo_list", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_add_item_to_todo_list", new_callable=AsyncMock) as mock_add:
                with patch.object(sensor, "async_remove_item_from_todo_list", new_callable=AsyncMock) as mock_remove:
                    await sensor.async_sync_todo_list("todo.list1")
        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    async def test_no_action_when_inactive_and_not_exists(self):
        sensor = make_sensor(active=False, task_interval_value=7, due_soon_days=0)
        sensor.due_in = 0
        with patch.object(sensor, "async_get_item_from_todo_list", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_add_item_to_todo_list", new_callable=AsyncMock) as mock_add:
                await sensor.async_sync_todo_list("todo.list1")
        mock_add.assert_not_called()

    async def test_removes_item_when_inactive_and_exists(self):
        sensor = make_sensor(active=False, task_interval_value=7, due_soon_days=0)
        sensor.due_in = 0
        existing = {"summary": "Test Task"}
        with patch.object(sensor, "async_get_item_from_todo_list", new_callable=AsyncMock, return_value=existing):
            with patch.object(sensor, "async_remove_item_from_todo_list", new_callable=AsyncMock) as mock_remove:
                await sensor.async_sync_todo_list("todo.list1")
        mock_remove.assert_called_once_with("todo.list1")


class TestTaskTrackerSensorMarkAsDone(unittest.IsolatedAsyncioTestCase):

    async def test_mark_as_done_sets_last_done_to_today(self):
        sensor = make_sensor()
        sensor.coordinator.last_done = date(1970, 1, 1)
        await sensor.async_mark_as_done()
        self.assertEqual(sensor.coordinator.last_done, date.today())

    async def test_mark_as_done_triggers_update(self):
        sensor = make_sensor()
        with patch.object(sensor, "async_schedule_update_ha_state") as mock_schedule:
            await sensor.async_mark_as_done()
        mock_schedule.assert_called_once_with(force_refresh=True)


class TestTaskTrackerSensorSetLastDoneDate(unittest.IsolatedAsyncioTestCase):

    async def test_set_last_done_date_updates_last_done(self):
        sensor = make_sensor()
        sensor.coordinator.last_done = date(1970, 1, 1)
        new_date = date(2024, 6, 15)
        await sensor.async_set_last_done_date(new_date)
        self.assertEqual(sensor.coordinator.last_done, new_date)

    async def test_set_last_done_date_triggers_update(self):
        sensor = make_sensor()
        with patch.object(sensor, "async_schedule_update_ha_state") as mock_schedule:
            await sensor.async_set_last_done_date(date(2024, 1, 1))
        mock_schedule.assert_called_once_with(force_refresh=True)


class TestTaskTrackerSensorActiveOverride(unittest.IsolatedAsyncioTestCase):

    async def _run_update(self, sensor):
        with patch.object(sensor, "async_write_ha_state"):
            with patch.object(sensor, "async_sync_todo_list", new_callable=AsyncMock):
                await sensor.async_update()

    async def test_active_override_on_makes_task_active(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "on"
        hass.states.get.return_value = override_state
        sensor = make_sensor(active=False, active_override="input_boolean.my_switch")
        sensor.hass = hass
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertNotEqual(sensor._attr_native_value, CONST_INACTIVE)

    async def test_active_override_off_makes_task_inactive(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "off"
        hass.states.get.return_value = override_state
        sensor = make_sensor(active=True, active_override="input_boolean.my_switch")
        sensor.hass = hass
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_INACTIVE)

    async def test_active_override_unavailable_falls_back_to_config(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "unavailable"
        hass.states.get.return_value = override_state
        sensor = make_sensor(active=True, active_override="input_boolean.my_switch")
        sensor.hass = hass
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertNotEqual(sensor._attr_native_value, CONST_INACTIVE)

    async def test_active_override_none_does_not_override(self):
        sensor = make_sensor(active=False, active_override=None)
        sensor.coordinator.last_done = date(1970, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_INACTIVE)


class TestTaskTrackerSensorTaskIntervalOverride(unittest.IsolatedAsyncioTestCase):

    async def _run_update(self, sensor):
        with patch.object(sensor, "async_write_ha_state"):
            with patch.object(sensor, "async_sync_todo_list", new_callable=AsyncMock):
                await sensor.async_update()

    async def test_task_interval_override_changes_due_date(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "30"
        hass.states.get.return_value = override_state
        sensor = make_sensor(task_interval_value=7,
                             task_interval_override="input_number.my_interval")
        sensor.hass = hass
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2024, 1, 31))

    async def test_task_interval_override_uses_days(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "14"
        hass.states.get.return_value = override_state
        sensor = make_sensor(task_interval_value=7, task_interval_type=CONF_WEEK,
                             task_interval_override="input_number.my_interval")
        sensor.hass = hass
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        # Override forces CONF_DAY: 14 days = Jan 15
        self.assertEqual(sensor.due_date, date(2024, 1, 15))

    async def test_task_interval_override_minimum_is_one(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "0"
        hass.states.get.return_value = override_state
        sensor = make_sensor(task_interval_value=7,
                             task_interval_override="input_number.my_interval")
        sensor.hass = hass
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2024, 1, 2))

    async def test_task_interval_override_unavailable_falls_back_to_config(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "unavailable"
        hass.states.get.return_value = override_state
        sensor = make_sensor(task_interval_value=7,
                             task_interval_override="input_number.my_interval")
        sensor.hass = hass
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2024, 1, 8))

    async def test_task_interval_override_none_does_not_override(self):
        sensor = make_sensor(task_interval_value=7, task_interval_override=None)
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, date(2024, 1, 8))


class TestTaskTrackerSensorDueSoonOverride(unittest.IsolatedAsyncioTestCase):

    async def _run_update(self, sensor):
        with patch.object(sensor, "async_write_ha_state"):
            with patch.object(sensor, "async_sync_todo_list", new_callable=AsyncMock):
                await sensor.async_update()

    async def test_due_soon_override_changes_attributes(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "5"
        hass.states.get.return_value = override_state
        sensor = make_sensor(due_soon_days=0,
                             due_soon_override="input_number.my_offset")
        sensor.hass = hass
        sensor.coordinator.last_done = date.today()
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_extra_state_attributes["due_soon_days"], 5)

    async def test_due_soon_override_unavailable_falls_back_to_config(self):
        hass = MagicMock()
        override_state = MagicMock()
        override_state.state = "unavailable"
        hass.states.get.return_value = override_state
        sensor = make_sensor(due_soon_days=3,
                             due_soon_override="input_number.my_offset")
        sensor.hass = hass
        sensor.coordinator.last_done = date.today()
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_extra_state_attributes["due_soon_days"], 3)

    async def test_due_soon_override_none_does_not_override(self):
        sensor = make_sensor(due_soon_days=3, due_soon_override=None)
        sensor.coordinator.last_done = date.today()
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_extra_state_attributes["due_soon_days"], 3)


class TestTaskTrackerSensorAddedToHass(unittest.IsolatedAsyncioTestCase):

    def _make_hass(self):
        hass = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=MagicMock())
        hass.states.get = MagicMock(return_value=None)
        return hass

    async def test_async_update_called_immediately(self):
        """async_update should always be called directly without deferral."""
        hass = self._make_hass()
        sensor = make_sensor(hass=hass)

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=None):
                with patch.object(sensor, "async_update", new_callable=AsyncMock) as mock_update:
                    sensor.hass = hass
                    sensor.async_on_remove = MagicMock()
                    await sensor.async_added_to_hass()

        mock_update.assert_called_once()

    async def test_async_update_called_regardless_of_hass_state(self):
        """async_update should be called even when hass is not in running state."""
        hass = self._make_hass()
        hass.state = "not_running"
        sensor = make_sensor(hass=hass)

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=None):
                with patch.object(sensor, "async_update", new_callable=AsyncMock) as mock_update:
                    sensor.hass = hass
                    sensor.async_on_remove = MagicMock()
                    await sensor.async_added_to_hass()

        mock_update.assert_called_once()

    async def test_restores_last_done_from_state(self):
        """Last done date should be restored from previous state attributes."""
        hass = self._make_hass()
        sensor = make_sensor(hass=hass)

        last_state = MagicMock()
        last_state.attributes = {"last_done": "2024-05-10"}

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=last_state):
                with patch.object(sensor, "async_update", new_callable=AsyncMock):
                    sensor.hass = hass
                    sensor.async_on_remove = MagicMock()
                    await sensor.async_added_to_hass()

        self.assertEqual(sensor.coordinator.last_done, date(2024, 5, 10))

    async def test_todo_list_state_change_listener_registered(self):
        """A state-change listener for todo lists should be subscribed."""
        hass = self._make_hass()
        sensor = make_sensor(hass=hass, todo_lists=["todo.my_list"])

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=None):
                with patch.object(sensor, "async_update", new_callable=AsyncMock):
                    sensor.hass = hass
                    sensor.async_on_remove = MagicMock()
                    await sensor.async_added_to_hass()

        hass.bus.async_listen.assert_called()

    async def test_no_event_homeassistant_started_listener_registered(self):
        """No listener for EVENT_HOMEASSISTANT_STARTED should be registered."""
        hass = self._make_hass()
        hass.bus.async_listen_once = MagicMock()
        sensor = make_sensor(hass=hass)

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock, return_value=None):
            with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=None):
                with patch.object(sensor, "async_update", new_callable=AsyncMock):
                    sensor.hass = hass
                    sensor.async_on_remove = MagicMock()
                    await sensor.async_added_to_hass()

        hass.bus.async_listen_once.assert_not_called()


class TestTaskTrackerSensorRepeatMode(unittest.IsolatedAsyncioTestCase):
    """Tests for the repeat_mode feature (repeat_after vs repeat_every)."""

    async def _run_update(self, sensor):
        with patch.object(sensor, "async_write_ha_state"):
            with patch.object(sensor, "async_sync_todo_list", new_callable=AsyncMock):
                await sensor.async_update()

    # --- repeat_after (default) ---

    async def test_repeat_after_mark_as_done_sets_last_done_to_today(self):
        """In repeat_after mode, mark_as_done sets last_done to today."""
        sensor = make_sensor(repeat_mode=CONF_REPEAT_AFTER, task_interval_value=7)
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        await sensor.coordinator.async_mark_as_done()
        self.assertEqual(sensor.coordinator.last_done, date.today())

    async def test_repeat_after_is_default(self):
        """repeat_mode defaults to repeat_after."""
        sensor = make_sensor()
        self.assertEqual(sensor.coordinator.repeat_mode, CONF_REPEAT_AFTER)

    async def test_repeat_after_propagated_to_coordinator(self):
        """repeat_after mode is written to the coordinator on init."""
        sensor = make_sensor(repeat_mode=CONF_REPEAT_AFTER)
        self.assertEqual(sensor.coordinator.repeat_mode, CONF_REPEAT_AFTER)

    # --- repeat_every ---

    async def test_repeat_every_mark_as_done_sets_last_done_to_due_date(self):
        """In repeat_every mode, mark_as_done sets last_done to the current due date.

        When the task is due soon (next occurrence is a few days in the future),
        last_done is advanced to that future date so the schedule moves forward
        by exactly one occurrence.
        """
        from datetime import timedelta
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY, task_interval_value=7)
        # last_done = 3 days ago → due_date = 4 days from now (future / due_soon)
        sensor.coordinator.last_done = date.today() - timedelta(days=3)
        await self._run_update(sensor)
        expected_due = sensor.coordinator.last_done + timedelta(days=7)
        self.assertEqual(sensor.due_date, expected_due)
        await sensor.coordinator.async_mark_as_done()
        # last_done should be the due_date (future), not today
        self.assertEqual(sensor.coordinator.last_done, expected_due)

    async def test_repeat_every_maintains_schedule_when_completed_early(self):
        """Completing a task early should not shift the schedule in repeat_every mode."""
        from datetime import timedelta
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY, task_interval_value=7)
        # due_date = 4 days from now
        sensor.coordinator.last_done = date.today() - timedelta(days=3)
        await self._run_update(sensor)
        expected_due = sensor.coordinator.last_done + timedelta(days=7)
        self.assertEqual(sensor.due_date, expected_due)
        # complete it early (due_date is still in the future)
        # mark_as_done sets last_done = expected_due (one step forward)
        await sensor.coordinator.async_mark_as_done()
        self.assertEqual(sensor.coordinator.last_done, expected_due)
        # Recalculate: next due = expected_due + 7
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, expected_due + timedelta(days=7))

    async def test_repeat_every_maintains_schedule_when_completed_late(self):
        """Completing an overdue task advances last_done by exactly one occurrence."""
        from datetime import timedelta
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY, task_interval_value=7)
        # due yesterday: last_done was 8 days ago
        sensor.coordinator.last_done = date.today() - timedelta(days=8)
        await self._run_update(sensor)
        expected_overdue_due = sensor.coordinator.last_done + timedelta(days=7)
        self.assertEqual(sensor.due_date, expected_overdue_due)  # = yesterday
        await sensor.coordinator.async_mark_as_done()
        # last_done is set to the current due date (yesterday), one step forward
        self.assertEqual(sensor.coordinator.last_done, expected_overdue_due)
        # next due = yesterday + 7 = 6 days from now
        await self._run_update(sensor)
        self.assertEqual(sensor.due_date, expected_overdue_due + timedelta(days=7))

    async def test_repeat_every_propagated_to_coordinator(self):
        """repeat_every mode is written to the coordinator on init."""
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY)
        self.assertEqual(sensor.coordinator.repeat_mode, CONF_REPEAT_EVERY)

    async def test_repeat_mode_in_state_attributes(self):
        """repeat_mode is included in the entity state attributes."""
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY)
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(
            sensor._attr_extra_state_attributes["repeat_mode"],
            CONF_REPEAT_EVERY,
        )

    async def test_repeat_after_mode_in_state_attributes(self):
        """repeat_after mode is correctly reflected in state attributes."""
        sensor = make_sensor(repeat_mode=CONF_REPEAT_AFTER)
        sensor.coordinator.last_done = date(2024, 1, 1)
        await self._run_update(sensor)
        self.assertEqual(
            sensor._attr_extra_state_attributes["repeat_mode"],
            CONF_REPEAT_AFTER,
        )

    async def test_repeat_every_sensor_mark_as_done_skipped_when_done(self):
        """sensor.async_mark_as_done does nothing when the task state is DONE."""
        from datetime import timedelta
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY, task_interval_value=7)
        # Set last_done so due_date is 30 days from now (DONE state)
        sensor.coordinator.last_done = date.today() + timedelta(days=23)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DONE)
        original_last_done = sensor.coordinator.last_done
        await sensor.async_mark_as_done()
        # last_done must not have changed
        self.assertEqual(sensor.coordinator.last_done, original_last_done)

    async def test_repeat_every_sensor_mark_as_done_skipped_when_inactive(self):
        """sensor.async_mark_as_done does nothing when the task is inactive."""
        from datetime import timedelta
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY, task_interval_value=7, active=False)
        sensor.coordinator.last_done = date.today() - timedelta(days=8)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_INACTIVE)
        original_last_done = sensor.coordinator.last_done
        await sensor.async_mark_as_done()
        self.assertEqual(sensor.coordinator.last_done, original_last_done)

    async def test_repeat_every_sensor_mark_as_done_proceeds_when_due(self):
        """sensor.async_mark_as_done calls the coordinator when the task is DUE."""
        from datetime import timedelta
        sensor = make_sensor(repeat_mode=CONF_REPEAT_EVERY, task_interval_value=7)
        sensor.coordinator.last_done = date.today() - timedelta(days=8)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DUE)
        original_last_done = sensor.coordinator.last_done
        await sensor.async_mark_as_done()
        # last_done must have advanced
        self.assertGreater(sensor.coordinator.last_done, original_last_done)

    async def test_repeat_every_sensor_mark_as_done_proceeds_when_due_soon(self):
        """sensor.async_mark_as_done calls the coordinator when the task is DUE_SOON."""
        from datetime import timedelta
        sensor = make_sensor(
            repeat_mode=CONF_REPEAT_EVERY,
            task_interval_value=7,
            due_soon_days=5,
        )
        # due in 3 days → DUE_SOON
        sensor.coordinator.last_done = date.today() - timedelta(days=4)
        await self._run_update(sensor)
        self.assertEqual(sensor._attr_native_value, CONST_DUE_SOON)
        original_last_done = sensor.coordinator.last_done
        await sensor.async_mark_as_done()
        # last_done must have advanced
        self.assertGreater(sensor.coordinator.last_done, original_last_done)


# ---------------------------------------------------------------------------
# Calendar-based due date calculation tests for repeat_every
# ---------------------------------------------------------------------------

class TestCalcNextWeekday(unittest.TestCase):
    """Tests for TaskTrackerCoordinator._calc_next_weekday."""

    def _sensor(self):
        return make_sensor()

    def test_next_monday_from_monday(self):
        """When last_done is already on the target weekday, advance by full interval."""
        sensor = self._sensor()
        # 2024-01-01 is a Monday
        result = sensor.coordinator._calc_next_weekday(date(2024, 1, 1), CONF_MONDAY, 1)
        self.assertEqual(result, date(2024, 1, 8))

    def test_next_wednesday_from_monday(self):
        sensor = self._sensor()
        # 2024-01-01 is Monday; next Wednesday is Jan 3 (+ 0 extra weeks)
        result = sensor.coordinator._calc_next_weekday(date(2024, 1, 1), CONF_WEDNESDAY, 1)
        self.assertEqual(result, date(2024, 1, 3))

    def test_next_monday_from_tuesday(self):
        sensor = self._sensor()
        # 2024-01-02 is Tuesday; next Monday is Jan 8
        result = sensor.coordinator._calc_next_weekday(date(2024, 1, 2), CONF_MONDAY, 1)
        self.assertEqual(result, date(2024, 1, 8))

    def test_biweekly_wednesday_from_wednesday(self):
        sensor = self._sensor()
        # 2024-01-03 is Wednesday; biweekly → Jan 17
        result = sensor.coordinator._calc_next_weekday(date(2024, 1, 3), CONF_WEDNESDAY, 2)
        self.assertEqual(result, date(2024, 1, 17))

    def test_biweekly_wednesday_from_thursday(self):
        sensor = self._sensor()
        # 2024-01-04 is Thursday; next Wednesday is Jan 10; + 1 more week = Jan 17
        result = sensor.coordinator._calc_next_weekday(date(2024, 1, 4), CONF_WEDNESDAY, 2)
        self.assertEqual(result, date(2024, 1, 17))

    def test_next_sunday_from_epoch(self):
        sensor = self._sensor()
        # 1970-01-01 is Thursday; next Sunday is Jan 4
        result = sensor.coordinator._calc_next_weekday(date(1970, 1, 1), CONF_SUNDAY, 1)
        self.assertEqual(result, date(1970, 1, 4))


class TestCalcNextDayOfMonth(unittest.TestCase):
    """Tests for TaskTrackerCoordinator._calc_next_day_of_month."""

    def _sensor(self):
        return make_sensor()

    def test_same_month_when_day_is_ahead(self):
        sensor = self._sensor()
        result = sensor.coordinator._calc_next_day_of_month(date(2024, 1, 15), 20)
        self.assertEqual(result, date(2024, 1, 20))

    def test_next_month_when_day_already_passed(self):
        sensor = self._sensor()
        result = sensor.coordinator._calc_next_day_of_month(date(2024, 1, 20), 20)
        self.assertEqual(result, date(2024, 2, 20))

    def test_next_month_when_day_is_before(self):
        sensor = self._sensor()
        result = sensor.coordinator._calc_next_day_of_month(date(2024, 1, 31), 5)
        self.assertEqual(result, date(2024, 2, 5))

    def test_clamped_to_short_month(self):
        sensor = self._sensor()
        # Day 31 in February: clamp to Feb 29 (2024 is a leap year)
        result = sensor.coordinator._calc_next_day_of_month(date(2024, 1, 31), 31)
        self.assertEqual(result, date(2024, 2, 29))

    def test_day_1_from_jan_31(self):
        sensor = self._sensor()
        result = sensor.coordinator._calc_next_day_of_month(date(2024, 1, 30), 31)
        self.assertEqual(result, date(2024, 1, 31))


class TestGetNthWeekdayOfMonth(unittest.TestCase):
    """Tests for TaskTrackerCoordinator._get_nth_weekday_of_month."""

    def _coordinator(self):
        return make_sensor().coordinator

    def test_1st_monday_of_jan_2024(self):
        # 2024-01-01 is Monday → 1st Monday = Jan 1
        result = self._coordinator()._get_nth_weekday_of_month(2024, 1, 0, 1)
        self.assertEqual(result, date(2024, 1, 1))

    def test_2nd_monday_of_jan_2024(self):
        result = self._coordinator()._get_nth_weekday_of_month(2024, 1, 0, 2)
        self.assertEqual(result, date(2024, 1, 8))

    def test_last_monday_of_jan_2024(self):
        # Jan 2024 has 5 Mondays: 1,8,15,22,29 → last = Jan 29
        result = self._coordinator()._get_nth_weekday_of_month(2024, 1, 0, -1)
        self.assertEqual(result, date(2024, 1, 29))

    def test_5th_monday_does_not_exist_in_some_months(self):
        # Feb 2024 has 4 Mondays; 5th doesn't exist
        result = self._coordinator()._get_nth_weekday_of_month(2024, 2, 0, 5)
        self.assertIsNone(result)

    def test_2nd_monday_of_march_2024(self):
        # 2024-03-01 is Friday; first Monday is Mar 4; 2nd = Mar 11
        result = self._coordinator()._get_nth_weekday_of_month(2024, 3, 0, 2)
        self.assertEqual(result, date(2024, 3, 11))


class TestCalcNextWeekdayOfMonth(unittest.TestCase):
    """Tests for TaskTrackerCoordinator._calc_next_weekday_of_month."""

    def _sensor(self):
        return make_sensor()

    def test_2nd_monday_of_next_month(self):
        sensor = self._sensor()
        # last=2024-01-15; 2nd Monday of Jan = Jan 8 (already past) → Feb 12
        result = sensor.coordinator._calc_next_weekday_of_month(date(2024, 1, 15), CONF_MONDAY, "2")
        self.assertEqual(result, date(2024, 2, 12))

    def test_1st_wednesday_of_same_month(self):
        sensor = self._sensor()
        # last=2024-01-01; 1st Wednesday of Jan = Jan 3 (ahead)
        result = sensor.coordinator._calc_next_weekday_of_month(date(2024, 1, 1), CONF_WEDNESDAY, "1")
        self.assertEqual(result, date(2024, 1, 3))

    def test_last_monday_of_next_month_when_current_passed(self):
        sensor = self._sensor()
        # last=2024-01-29; last Monday of Jan = Jan 29 (same day, not strictly greater) → Feb last Monday = Feb 26
        result = sensor.coordinator._calc_next_weekday_of_month(date(2024, 1, 29), CONF_MONDAY, "last")
        self.assertEqual(result, date(2024, 2, 26))

    def test_last_monday_of_same_month_still_ahead(self):
        sensor = self._sensor()
        # last=2024-01-15; last Monday of Jan = Jan 29 (ahead of Jan 15)
        result = sensor.coordinator._calc_next_weekday_of_month(date(2024, 1, 15), CONF_MONDAY, "last")
        self.assertEqual(result, date(2024, 1, 29))


class TestCalcNextDaysBeforeEndOfMonth(unittest.TestCase):
    """Tests for TaskTrackerCoordinator._calc_next_days_before_end_of_month."""

    def _coordinator(self):
        return make_sensor().coordinator

    def test_last_day_of_month_when_days_before_is_zero(self):
        # 0 days before end = last day; Jan has 31 days → Jan 31
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 1, 15), 0)
        self.assertEqual(result, date(2024, 1, 31))

    def test_second_to_last_day_of_month(self):
        # 1 day before end of Jan = Jan 30
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 1, 15), 1)
        self.assertEqual(result, date(2024, 1, 30))

    def test_three_days_before_end_of_month(self):
        # 3 days before end of Jan = Jan 28
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 1, 1), 3)
        self.assertEqual(result, date(2024, 1, 28))

    def test_advances_to_next_month_when_target_already_passed(self):
        # 0 days before end; last = Jan 31 (the target itself) → must advance to Feb
        # Feb 2024 is a leap year: last day = Feb 29
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 1, 31), 0)
        self.assertEqual(result, date(2024, 2, 29))

    def test_advances_to_next_month_when_target_same_as_last(self):
        # 1 day before end of Jan = Jan 30; last = Jan 30 → advance; 2023 non-leap:
        # Feb has 28 days → target = Feb 27
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2023, 1, 30), 1)
        self.assertEqual(result, date(2023, 2, 27))

    def test_last_day_varies_by_month_length(self):
        # 0 days before end of Feb 2024 (leap year: 29 days) = Feb 29
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 2, 1), 0)
        self.assertEqual(result, date(2024, 2, 29))

    def test_large_days_before_end_clamped_to_first(self):
        # 40 days before end of January (31 days): 31 - 40 = -9 → clamped to day 1
        # candidate = Jan 1, NOT > last (Jan 1 == Jan 1) → next month Feb
        # Feb 2024: 29 - 40 = -11 → clamped to 1 → Feb 1
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 1, 1), 40)
        self.assertEqual(result, date(2024, 2, 1))

    def test_last_day_of_december(self):
        # 0 days before end of Dec = Dec 31
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 12, 1), 0)
        self.assertEqual(result, date(2024, 12, 31))

    def test_rolls_over_year_boundary(self):
        # 0 days before end; last = Dec 31 → next target = Jan 31 of the next year
        result = self._coordinator()._calc_next_days_before_end_of_month(date(2024, 12, 31), 0)
        self.assertEqual(result, date(2025, 1, 31))
