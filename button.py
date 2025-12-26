"""Platform for sensor integration."""
from __future__ import annotations

from logging import getLogger

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify
from .const import DOMAIN, CONST_UNKNOWN
from .sensor import TaskTrackerSensor

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
    async_add_entities([TaskTrackerButton(entry.data[CONF_NAME], hass)])


class TaskTrackerButton(ButtonEntity):
    """Representation of a generic DockerButton."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_native_value = CONST_UNKNOWN

    def __init__(self, entry_name: str, hass: HomeAssistant) -> None:
        """Initialize the button."""
        self.device_id = f"task_tracker_{slugify(entry_name)}"
        self.name = entry_name.capitalize()
        self.hass = hass
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer="Gensyn",
            model="Task Tracker",
            name=self.name,
        )
        self._attr_name = f"{self.name} Mark as done"
        self._attr_unique_id = f"{self.device_id}_mark_as_done"
        self.entity_id = generate_entity_id("button.{}_mark_as_done", f"{self.device_id}", hass=self.hass)

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
