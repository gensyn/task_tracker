"""Platform for button integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from logging import getLogger

from .const import DOMAIN, CONST_UNKNOWN
from .sensor import TaskTrackerSensor

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
        sensor: TaskTrackerSensor = await get_sensor(self.hass, self.device_entry.id)
        await sensor.async_mark_as_done()


async def get_sensor(hass, device_id: str) -> TaskTrackerSensor:
    """Get the sensor."""
    entity_reg = entity_registry.async_get(hass)
    entries = entity_registry.async_entries_for_device(entity_reg, device_id)
    sensors = [entry.entity_id for entry in entries if entry.entity_id.startswith(Platform.SENSOR)]
    if len(sensors) != 1:
        raise ValueError(f"Expected exactly one sensor for device_id {device_id}, found {len(sensors)}")
    # cannot use hass.states.get(sensors[0]) here because we need the entity object, not just the state
    return hass.data["entity_components"][Platform.SENSOR].get_entity(sensors[0])
