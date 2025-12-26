"""Platform for sensor integration."""
from __future__ import annotations

import re
from datetime import timedelta, datetime, date
from logging import getLogger

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STARTED, \
    CONF_ICON
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify
from .const import DOMAIN, CONF_TASK_FREQUENCY_VALUE, CONF_NOTIFICATION_FREQUENCY, CONF_TAGS, CONF_ACTIVE, CONF_WEEK, \
    CONF_MONTH, CONF_YEAR, CONST_TODO, CONST_INACTIVE, CONST_DONE, CONF_TASK_FREQUENCY_TYPE

LOGGER = getLogger(__name__)


def setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    pass


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigType,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from a config entry."""
    data: dict = entry.data
    options: dict = entry.options
    async_add_entities(
        [TaskTrackerSensor(data[CONF_NAME], options[CONF_TASK_FREQUENCY_VALUE], options[CONF_TASK_FREQUENCY_TYPE],
                           options[CONF_NOTIFICATION_FREQUENCY], options[CONF_TAGS],
                           options[CONF_ACTIVE], options[CONF_ICON], hass)])


class TaskTrackerSensor(SensorEntity, RestoreEntity):
    """Representation of a DockerSensor."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, entry_name: str, task_frequency_value: int, task_frequency_type: str,
                 notification_frequency: int, tags: str, active: bool, icon: str,
                 hass: HomeAssistant) -> None:
        """Initialize the sensor with a service name."""
        self.name: str = entry_name
        self.task_frequency_value: int = task_frequency_value
        self.task_frequency_type: int = task_frequency_type
        self.notification_frequency: int = notification_frequency
        self.last_done: date = date(1970, 1, 1)
        tags_list = re.split(r'[;, ]+', tags)
        self.tags: list = [assignee.strip() for assignee in tags_list if assignee]
        self.active: bool = active
        self.icon: str = icon
        self.hass: HomeAssistant = hass

        device_id = f"task_tracker_{slugify(entry_name)}"
        self._attr_name = f"{self.name}"
        self._attr_unique_id = f"{device_id}"
        self.entity_id = generate_entity_id("sensor.{}", device_id, hass=self.hass)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer="Gensyn",
            model="Task Tracker",
            name=self.name,
        )

    async def async_added_to_hass(self) -> None:
        """Restore last known state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_native_value = last_state.state
            last_done = last_state.attributes.get("last_done", "1970-01-01")
            self.last_done = datetime.strptime(last_done, "%Y-%m-%d").date()

        if self.hass.state == CoreState.running:
            await self.async_update()
        else:
            # Delay the first update until Home Assistant is fully started so startup is not blocked
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self.async_update
            )

    async def async_update(self, _=None) -> None:
        self._attr_native_value = CONST_DONE

        days_since_last: int = (date.today() - self.last_done).days

        if self.task_frequency_type == CONF_WEEK:
            due_date = self.last_done + timedelta(weeks=self.task_frequency_value)
        elif self.task_frequency_type == CONF_MONTH:
            due_date = date(self.last_done.year + (self.last_done.month + self.task_frequency_value - 1) // 12,
                            (self.last_done.month + self.task_frequency_value - 1) % 12 + 1,
                            self.last_done.day)
        elif self.task_frequency_type == CONF_YEAR:
            due_date = date(self.last_done.year + self.task_frequency_value, self.last_done.month, self.last_done.day)
        else:
            due_date = self.last_done + timedelta(days=self.task_frequency_value)

        due_in: int = (due_date - date.today()).days if due_date > date.today() else 0
        overdue_by: int = (date.today() - due_date).days if due_date < date.today() else 0

        if not self.active:
            self._attr_native_value = CONST_INACTIVE
        elif due_in == 0:
            self._attr_native_value = CONST_TODO

        self._attr_extra_state_attributes: dict[str, str | int | list] = {
            "task_frequency_value": self.task_frequency_value,
            "task_frequency_type": self.task_frequency_type,
            "notification_frequency": self.notification_frequency,
            "last_done": str(self.last_done),
            "due_date": str(due_date),
            "due_in": due_in,
            "overdue_by": overdue_by,
            "tags": self.tags,
            "icon": self.icon,
        }
        self.async_write_ha_state()

    async def async_mark_as_done(self) -> None:
        """Mark the task as done for today."""
        self.last_done = date.today()
        await self.async_update()

    async def async_set_last_done_date(self, year: int, month: int, day: int) -> None:
        """Set the last done date."""
        self.last_done = date(year, month, day)
        await self.async_update()
