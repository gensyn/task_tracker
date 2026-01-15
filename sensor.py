"""Platform for sensor integration."""
from __future__ import annotations

import re
from datetime import timedelta, datetime, date
from functools import partial
from logging import getLogger
from typing import Any, Callable

from dateutil.relativedelta import relativedelta

from homeassistant.components.sensor import (
    SensorEntity, RestoreSensor,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STARTED, CONF_ICON, CONF_ENTITY_ID, EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, CoreState, EventStateChangedData, callback
from homeassistant.exceptions import ServiceValidationError, HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import slugify
from homeassistant.util.dt import UTC
from .const import DOMAIN, CONF_TASK_INTERVAL_VALUE, CONF_NOTIFICATION_INTERVAL, CONF_TAGS, CONF_ACTIVE, CONF_WEEK, \
    CONF_MONTH, CONF_YEAR, CONST_DUE, CONST_INACTIVE, CONST_DONE, CONF_TASK_INTERVAL_TYPE, CONF_TODO_OFFSET_DAYS, \
    CONF_TODO_LISTS, CONF_DAY

LOGGER = getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from a config entry."""
    data = entry.data
    options = entry.options
    async_add_entities(
        [TaskTrackerSensor(data[CONF_NAME], options[CONF_TASK_INTERVAL_VALUE], options[CONF_TASK_INTERVAL_TYPE],
                           options[CONF_NOTIFICATION_INTERVAL], options[CONF_TODO_LISTS],
                           options[CONF_TODO_OFFSET_DAYS], options[CONF_TAGS],
                           options[CONF_ACTIVE], options[CONF_ICON], entry.entry_id, hass)])


class TaskTrackerSensor(RestoreSensor, SensorEntity):
    """Representation of a TaskTrackerSensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "status"

    def __init__(self, entry_name: str, task_interval_value: int, task_interval_type: str,
                 notification_interval: int, todo_lists: list[str], todo_offset_days: int, tags: str, active: bool,
                 icon: str, entry_id: str, hass: HomeAssistant) -> None:
        """Initialize the sensor with a service name."""
        self.task_interval_value: int = task_interval_value
        self.task_interval_type: str = task_interval_type
        self.notification_interval: int = notification_interval
        self.todo_lists: list[str] = todo_lists
        self.todo_offset_days: int = todo_offset_days
        self.entry_id = entry_id
        self.entry_name = entry_name
        self.last_done: date = date(1970, 1, 1)
        tags_list = re.split(r'[;, ]+', tags)
        self.tags: list = [tag.strip() for tag in tags_list if tag]
        self.active: bool = active
        self.icon: str = icon
        self.due_date: date = date(1970, 1, 1)
        self.due_in: int = 0
        self.mark_as_done_scheduled: Callable[[], None] | None = None

        device_id = f"{DOMAIN}_{self.entry_id}"
        self._attr_name = None
        self._attr_unique_id = f"{self.entry_id}_status"
        self.entity_id = generate_entity_id("sensor.task_tracker_{}", slugify(entry_name), hass=hass)
        self._attr_native_value = "due"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer="Gensyn",
            model="Task Tracker",
            name=entry_name,
        )

    async def async_added_to_hass(self) -> None:
        """Restore last known state on startup."""
        await super().async_added_to_hass()
        last_sensor_state = await self.async_get_last_sensor_data()
        if last_sensor_state is not None:
            self._attr_native_value = last_sensor_state.native_value
        last_state = await self.async_get_last_state()
        if last_state is not None:
            last_done = last_state.attributes.get("last_done", "1970-01-01")
            self.last_done = datetime.strptime(last_done, "%Y-%m-%d").date()

            self._attr_extra_state_attributes: dict[str, str | int | list] = {
                "last_done": last_done,
            }

        # Subscribe to todo list state changes
        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_STATE_CHANGED,
                self.async_todo_list_changed,
                self._filter_state_changes
            )
        )

        if self.hass.state == CoreState.running:
            await self.async_update()
        else:
            # Delay the first update until Home Assistant is fully started so startup is not blocked
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self.async_update
            )

    async def async_update(self, _=None) -> None:
        self._attr_native_value = CONST_DONE

        if self.task_interval_type == CONF_WEEK:
            self.due_date = self.last_done + relativedelta(weeks=self.task_interval_value)
        elif self.task_interval_type == CONF_MONTH:
            self.due_date = self.last_done + relativedelta(months=self.task_interval_value)
        elif self.task_interval_type == CONF_YEAR:
            self.due_date = self.last_done + relativedelta(years=self.task_interval_value)
        else:
            self.due_date = self.last_done + relativedelta(days=self.task_interval_value)

        self.due_in: int = (self.due_date - date.today()).days if self.due_date > date.today() else 0
        overdue_by: int = (date.today() - self.due_date).days if self.due_date < date.today() else 0

        if not self.active:
            self._attr_native_value = CONST_INACTIVE
        elif self.due_in == 0:
            self._attr_native_value = CONST_DUE

        self._attr_extra_state_attributes: dict[str, str | int | list] = {
            "last_done": str(self.last_done),
            "due_date": str(self.due_date),
            "due_in": self.due_in,
            "overdue_by": overdue_by,
            "task_interval_value": self.task_interval_value,
            "task_interval_type": self.task_interval_type,
            "icon": self.icon,
            "tags": self.tags,
            "todo_lists": self.todo_lists,
            "todo_offset_days": self.todo_offset_days,
            "notification_interval": self.notification_interval,
        }
        self.async_write_ha_state()
        for todo_list in self.todo_lists:
            await self.async_sync_todo_list(todo_list)

    @callback
    def _filter_state_changes(self, event_data: EventStateChangedData) -> bool:
        """Listen only for events regarding todo list entities of our task.
        Also filter out events where the number of open items did not decrease."""
        return event_data["entity_id"] in self.todo_lists and event_data.get("old_state") and event_data.get(
            "new_state") and event_data["new_state"].state < event_data["old_state"].state

    async def async_todo_list_changed(self, event: Any) -> None:
        if self.mark_as_done_scheduled:
            self.mark_as_done_scheduled()
        # allow 5 seconds for the user to change their mind - it might have been a misclick
        self.mark_as_done_scheduled = async_call_later(
            self.hass,
            5,
            partial(self.async_todo_list_changed_deferred, event)
        )

    async def async_todo_list_changed_deferred(self, event: Any, _) -> None:
        todo_list = event.data[CONF_ENTITY_ID]
        existing_item = await self.async_get_item_from_todo_list(todo_list)
        if existing_item is None:
            # the item does not exist, so no action is needed
            return
        completed_string = existing_item.get("completed")
        if completed_string:
            completed = datetime.strptime(completed_string, "%Y-%m-%dT%H:%M:%S.%f%z")
            if datetime.now(UTC) - completed < timedelta(minutes=5):
                # the item was marked as done, so we need to update our last_done date
                await self.async_mark_as_done()

    async def async_sync_todo_list(self, todo_list: str) -> None:
        existing_item: dict | None = await self.async_get_item_from_todo_list(todo_list)

        if self.active and self.due_in <= self.todo_offset_days:
            # there is supposed to be an item in the todo list
            if existing_item is None:
                # The item does not exist, so we need to add it
                await self.async_add_item_to_todo_list(todo_list)
                return
            else:
                # the item exists but the status and due date might be wrong
                # even if the current status and due date are correct, it is easiest to just update the item
                await self.async_update_item_in_todo_list(todo_list)
        else:
            # there is NOT supposed to be an item in the todo list
            if existing_item is None:
                # The item does not exist, so no action is needed
                return
            else:
                # The item exists, so we need to remove it
                await self.async_remove_item_from_todo_list(todo_list)
                return

    async def async_add_item_to_todo_list(self, todo_list: str) -> None:
        """Add the item to the todo list."""
        await self.async_call_service("add_item", {
            CONF_ENTITY_ID: todo_list,
            "item": self.entry_name,
            "due_date": self.due_date
        })

    async def async_remove_item_from_todo_list(self, todo_list: str) -> None:
        """Remove the item from the todo list."""
        await self.async_call_service("remove_item", {
            CONF_ENTITY_ID: todo_list,
            "item": self.entry_name,
        })

    async def async_update_item_in_todo_list(self, todo_list: str) -> None:
        """Update the item in the todo list."""
        await self.async_call_service("update_item", {
            CONF_ENTITY_ID: todo_list,
            "item": self.entry_name,
            "status": "needs_action",
            "due_date": self.due_date,
        })

    async def async_get_item_from_todo_list(self, todo_list: str) -> dict | None:
        """Get the todo item from the todo list."""
        response = await self.async_call_service("get_items", {
            CONF_ENTITY_ID: todo_list,
            "status": ["needs_action", "completed"],
        }, blocking=True, response=True)

        if not response:
            return None

        for item in response.get(todo_list, {}).get("items", []):
            if item.get("summary") == self.entry_name:
                return item
        return None

    async def async_call_service(self, service: str, service_data: dict[str, Any], blocking: bool = False,
                                 response: bool = False) -> dict | None:
        """Call a todo-service."""
        try:
            return await self.hass.services.async_call(
                domain="todo",
                service=service,
                service_data=service_data,
                blocking=blocking,
                return_response=response,
            )
        except (ServiceValidationError, HomeAssistantError) as err:
            LOGGER.error("Failed to call service \"todo.%s\": %s", service, err)
            raise

    async def async_mark_as_done(self) -> None:
        """Mark the task as done for today."""
        self.last_done = date.today()
        await self.async_update()

    async def async_set_last_done_date(self, new_date: date) -> None:
        """Set the last done date."""
        self.last_done = new_date
        await self.async_update()
