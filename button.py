"""Platform for button integration."""
from __future__ import annotations

from logging import getLogger

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import TaskTrackerCoordinator

LOGGER = getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from a config entry."""
    async_add_entities([TaskTrackerButton(entry.data[CONF_NAME], entry.entry_id, hass)])


class TaskTrackerButton(ButtonEntity):
    """Button to complete a task."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "mark_as_done"

    def __init__(self, entry_name: str, entry_id: str, hass: HomeAssistant) -> None:
        """Initialize the button."""
        self._entry_id = entry_id
        self.device_id = f"{DOMAIN}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer="Gensyn",
            model="Task Tracker",
            name=entry_name,
        )
        self._attr_unique_id = f"{entry_id}_mark_as_done"
        self.entity_id = generate_entity_id("button.task_tracker_{}_mark_as_done", slugify(entry_name), hass=hass)

    async def async_press(self) -> None:
        coordinator: TaskTrackerCoordinator = self.hass.data[DOMAIN][self._entry_id]
        await coordinator.async_mark_as_done()

