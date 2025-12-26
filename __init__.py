"""The Task Tracker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN
from .frontend import TaskTrackerCardRegistration
from .sensor import TaskTrackerSensor

_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)

type TaskTrackerConfigEntry = ConfigEntry[MyApi]  # noqa: F821


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration and schedule a single daily midnight update for all entities."""
    # Schedule only once for the integration
    domain_data = hass.data.setdefault(DOMAIN, {})
    if "midnight_unsub" in domain_data:
        return True

    async def _midnight_update(_) -> None:
        """Update all entities belonging to this integration at midnight."""
        try:
            count = 0
            registry = entity_registry.async_get(hass)
            for entry in hass.config_entries.async_entries(DOMAIN):
                entries = entity_registry.async_entries_for_config_entry(registry, entry.entry_id)
                for e in entries:
                    if not e.entity_id.startswith("sensor."):
                        continue
                    count += 1
                    await hass.data["entity_components"][Platform.SENSOR].get_entity(e.entity_id).async_update()
            _LOGGER.debug(f"Midnight update ran for {count} entities")
        except Exception:
            _LOGGER.exception("Failed to run daily entity update")

    unsub = async_track_time_change(hass, _midnight_update, hour=0, minute=0, second=0)
    domain_data["midnight_unsub"] = unsub

    async def async_mark_as_done(service_call: str):
        s = await get_sensor(hass, service_call.data["entity_id"])
        await s.async_mark_as_done()

    async def async_set_last_done_date(service_call: str):
        s = await get_sensor(hass, service_call.data["entity_id"])
        await s.async_set_last_done_date(service_call.data["year"], service_call.data["month"], service_call.data["day"])

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_MARK_AS_DONE,
        async_mark_as_done,
        schema=const.SERVICE_MARK_AS_DONE_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_SET_LAST_DONE_DATE,
        async_set_last_done_date,
        schema=const.SERVICE_SET_LAST_DONE_DATE_SCHEMA,
    )

    cards = TaskTrackerCardRegistration(hass)
    await cards.async_register()

    return True

async def async_setup_entry(hass: HomeAssistant, entry: TaskTrackerConfigEntry) -> bool:
    """Set up Task Tracker from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: TaskTrackerConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

async def get_sensor(hass, entity_id: str) -> TaskTrackerSensor:
    """Get the sensor."""
    s = hass.data["entity_components"][Platform.SENSOR].get_entity(entity_id)
    if s is None:
        raise ValueError(f"Could not find {entity_id}")
    return s
