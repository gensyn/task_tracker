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
from homeassistant.const import CONF_NAME, CONF_ICON, CONF_ENTITY_ID, EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, EventStateChangedData, callback
from homeassistant.exceptions import ServiceValidationError, HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import slugify
from homeassistant.util.dt import UTC

from .const import DOMAIN, CONF_TASK_INTERVAL_VALUE, CONF_NOTIFICATION_INTERVAL, CONF_TAGS, CONF_ACTIVE, CONF_WEEK, \
    CONF_MONTH, CONF_YEAR, CONST_DUE, CONST_DUE_SOON, CONST_INACTIVE, CONST_DONE, CONF_TASK_INTERVAL_TYPE, \
    CONF_DUE_SOON_DAYS, CONF_TODO_LISTS, CONF_DAY, CONF_ACTIVE_OVERRIDE, CONF_TASK_INTERVAL_OVERRIDE, \
    CONF_DUE_SOON_OVERRIDE
from .coordinator import TaskTrackerCoordinator

LOGGER = getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from a config entry."""
    coordinator: TaskTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = entry.data
    options = entry.options
    async_add_entities(
        [TaskTrackerSensor(coordinator, data[CONF_NAME], options[CONF_TASK_INTERVAL_VALUE],
                           options[CONF_TASK_INTERVAL_TYPE],
                           options[CONF_NOTIFICATION_INTERVAL], options[CONF_TODO_LISTS],
                           options[CONF_DUE_SOON_DAYS], options[CONF_TAGS],
                           options[CONF_ACTIVE], options[CONF_ICON], entry.entry_id, hass,
                           options.get(CONF_ACTIVE_OVERRIDE),
                           options.get(CONF_TASK_INTERVAL_OVERRIDE),
                           options.get(CONF_DUE_SOON_OVERRIDE))])


class TaskTrackerSensor(RestoreSensor, SensorEntity):
    """Representation of a TaskTrackerSensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "status"

    def __init__(self, coordinator: TaskTrackerCoordinator, entry_name: str,
                 task_interval_value: int, task_interval_type: str,
                 notification_interval: int, todo_lists: list[str], due_soon_days: int, tags: str, active: bool,
                 icon: str, entry_id: str, hass: HomeAssistant,
                 active_override: str | None = None,
                 task_interval_override: str | None = None,
                 due_soon_override: str | None = None) -> None:
        """Initialize the sensor with a service name."""
        self.coordinator = coordinator
        self.task_interval_value: int = task_interval_value
        self.task_interval_type: str = task_interval_type
        self.notification_interval: int = notification_interval
        self.todo_lists: list[str] = todo_lists
        self.due_soon_days: int = due_soon_days
        self.entry_id = entry_id
        self.entry_name = entry_name
        tags_list = re.split(r'[;, ]+', tags)
        self.tags: list[str] = [tag.strip() for tag in tags_list if tag]
        self.active: bool = active
        self.icon: str = icon
        self.due_date: date = date(1970, 1, 1)
        self.due_in: int = 0
        self.mark_as_done_scheduled: Callable[[], None] | None = None
        self.active_override: str | None = active_override
        self.task_interval_override: str | None = task_interval_override
        self.due_soon_override: str | None = due_soon_override
        # Effective values after applying overrides; initialised to configured values
        self._effective_active: bool = active
        self._effective_due_soon_days: int = due_soon_days

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

        # Register coordinator listener so state changes are reflected in HA.
        # Registered here (not just in async_added_to_hass) so that tests which
        # call async_mark_as_done / async_set_last_done_date without adding the
        # entity to hass also trigger the update callback.
        self.async_on_remove(
            self.coordinator.async_add_listener(
                lambda: self.async_schedule_update_ha_state(force_refresh=True)
            )
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
            # Restore last_done into the coordinator — it is the single source of truth.
            self.coordinator.last_done = datetime.strptime(last_done, "%Y-%m-%d").date()

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

        # Subscribe to override entity state changes
        if any([self.active_override, self.task_interval_override, self.due_soon_override]):
            @callback
            def _async_override_state_changed(_event: Any) -> None:
                self.async_schedule_update_ha_state(force_refresh=True)

            self.async_on_remove(
                self.hass.bus.async_listen(
                    EVENT_STATE_CHANGED,
                    _async_override_state_changed,
                    self._filter_override_changes,
                )
            )

        await self.async_update()

    def _resolve_active_override(self) -> bool:
        """Return the effective ``active`` value after applying any override entity."""
        if self.active_override:
            override_state = self.hass.states.get(self.active_override)
            if override_state is not None and override_state.state not in ("unavailable", "unknown"):
                return override_state.state == "on"
        return self.active

    def _resolve_task_interval_override(self) -> tuple[int, str]:
        """Return the effective (interval_value, interval_type) after applying any override entity.

        When an override entity is active the interval type is always ``CONF_DAY``; the
        override represents a number of days regardless of the configured interval type.
        """
        if self.task_interval_override:
            override_state = self.hass.states.get(self.task_interval_override)
            if override_state is not None and override_state.state not in ("unavailable", "unknown"):
                try:
                    return max(1, int(float(override_state.state))), CONF_DAY
                except (ValueError, TypeError):
                    pass
        return self.task_interval_value, self.task_interval_type

    def _resolve_due_soon_override(self) -> int:
        """Return the effective due soon days after applying any override entity."""
        if self.due_soon_override:
            override_state = self.hass.states.get(self.due_soon_override)
            if override_state is not None and override_state.state not in ("unavailable", "unknown"):
                try:
                    return max(0, int(float(override_state.state)))
                except (ValueError, TypeError):
                    pass
        return self.due_soon_days

    def _calculate_due_date(self, interval_value: int, interval_type: str) -> date:
        """Return the due date computed from *last_done* and the given interval."""
        if interval_type == CONF_WEEK:
            return self.coordinator.last_done + relativedelta(weeks=interval_value)
        if interval_type == CONF_MONTH:
            return self.coordinator.last_done + relativedelta(months=interval_value)
        if interval_type == CONF_YEAR:
            return self.coordinator.last_done + relativedelta(years=interval_value)
        return self.coordinator.last_done + relativedelta(days=interval_value)

    async def async_update(self) -> None:
        """Recalculate state, attributes, and sync all configured todo lists."""
        self._attr_native_value = CONST_DONE

        effective_active = self._resolve_active_override()
        effective_task_interval_value, effective_task_interval_type = self._resolve_task_interval_override()
        effective_due_soon_days = self._resolve_due_soon_override()

        self.due_date = self._calculate_due_date(effective_task_interval_value, effective_task_interval_type)
        self.due_in: int = (self.due_date - date.today()).days if self.due_date > date.today() else 0
        overdue_by: int = (date.today() - self.due_date).days if self.due_date < date.today() else 0

        if not effective_active:
            self._attr_native_value = CONST_INACTIVE
        elif self.due_in == 0:
            self._attr_native_value = CONST_DUE
        elif self.due_in <= effective_due_soon_days:
            self._attr_native_value = CONST_DUE_SOON

        self._effective_active: bool = effective_active
        self._effective_due_soon_days: int = effective_due_soon_days

        self._attr_extra_state_attributes: dict[str, str | int | list] = {
            "last_done": str(self.coordinator.last_done),
            "due_date": str(self.due_date),
            "due_in": self.due_in,
            "overdue_by": overdue_by,
            "task_interval_value": effective_task_interval_value,
            "task_interval_type": effective_task_interval_type,
            "icon": self.icon,
            "tags": self.tags,
            "todo_lists": self.todo_lists,
            "due_soon_days": effective_due_soon_days,
            "notification_interval": self.notification_interval,
        }
        for todo_list in self.todo_lists:
            await self.async_sync_todo_list(todo_list)

    @callback
    def _filter_state_changes(self, event_data: EventStateChangedData) -> bool:
        """Listen only for events regarding todo list entities of our task.

        Also filter out events where the number of open items did not decrease.
        Todo list states are integer strings (e.g. "5"), so an explicit int()
        conversion is required — pure string comparison gives wrong results for
        multi-digit counts (e.g. ``"5" < "10"`` is ``False`` lexicographically).
        """
        if event_data["entity_id"] not in self.todo_lists:
            return False
        old_state = event_data.get("old_state")
        new_state = event_data.get("new_state")
        if not old_state or not new_state:
            return False
        try:
            return int(new_state.state) < int(old_state.state)
        except (ValueError, TypeError):
            return False

    @callback
    def _filter_override_changes(self, event_data: EventStateChangedData) -> bool:
        """Listen only for state changes in override entities."""
        override_entities = {e for e in
                             [self.active_override, self.task_interval_override, self.due_soon_override] if e}
        return event_data["entity_id"] in override_entities

    async def async_todo_list_changed(self, event: Any) -> None:
        """Handle a todo list state-change event.

        Cancels any previously scheduled deferred update, then waits 5 seconds
        before acting — giving the user a chance to undo an accidental completion.
        """
        if self.mark_as_done_scheduled:
            self.mark_as_done_scheduled()
        # allow 5 seconds for the user to change their mind - it might have been a misclick
        self.mark_as_done_scheduled = async_call_later(
            self.hass,
            5,
            partial(self.async_todo_list_changed_deferred, event)
        )

    async def async_todo_list_changed_deferred(self, event: Any, _) -> None:
        """Mark task as done if the todo item was completed within the last 5 minutes."""
        todo_list = event.data[CONF_ENTITY_ID]
        existing_item = await self.async_get_item_from_todo_list(todo_list)
        if existing_item is None:
            # the item does not exist, so no action is needed
            return
        completed_string = existing_item.get("completed")
        if completed_string:
            try:
                completed = datetime.strptime(completed_string, "%Y-%m-%dT%H:%M:%S.%f%z")
            except ValueError:
                LOGGER.warning(
                    "Could not parse completed timestamp %r for task %s; skipping mark-as-done",
                    completed_string,
                    self.entry_name,
                )
                return
            if datetime.now(UTC) - completed < timedelta(minutes=5):
                # the item was marked as done, so we need to update our last_done date
                await self.async_mark_as_done()

    async def async_sync_todo_list(self, todo_list: str) -> None:
        """Add, update, or remove this task's item in *todo_list* as appropriate."""
        existing_item: dict | None = await self.async_get_item_from_todo_list(todo_list)

        if self._effective_active and self.due_in <= self._effective_due_soon_days:
            # there is supposed to be an item in the todo list
            if existing_item is None:
                # The item does not exist, so we need to add it
                await self.async_add_item_to_todo_list(todo_list)
                return
            # the item exists but the status and due date might be wrong
            # even if the current status and due date are correct, it is easiest to just update the item
            await self.async_update_item_in_todo_list(todo_list)
        else:
            # there is NOT supposed to be an item in the todo list
            if existing_item is None:
                # The item does not exist, so no action is needed
                return
            # The item exists, so we need to remove it
            await self.async_remove_item_from_todo_list(todo_list)

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
        await self.coordinator.async_mark_as_done()

    async def async_set_last_done_date(self, new_date: date) -> None:
        """Set the last done date."""
        await self.coordinator.async_set_last_done_date(new_date)
