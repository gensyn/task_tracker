"""The Task Tracker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ICON, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError, HomeAssistantError
from homeassistant.helpers import entity_registry
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN, CONF_TASK_INTERVAL_VALUE, CONF_DAY, CONF_TASK_INTERVAL_TYPE, CONF_NOTIFICATION_INTERVAL, \
    CONF_TODO_OFFSET_DAYS, CONF_TAGS, CONF_ACTIVE, CONF_YEAR, CONF_MONTH, CONF_TODO_LISTS, SERVICE_MARK_AS_DONE, \
    SERVICE_MARK_AS_DONE_SCHEMA, SERVICE_SET_LAST_DONE_DATE, SERVICE_SET_LAST_DONE_DATE_SCHEMA, CONF_DATE
from .frontend import TaskTrackerCardRegistration
from .sensor import TaskTrackerSensor

_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration and schedule a single daily midnight update for all entities."""
    # Schedule only once for the integration
    domain_data = hass.data.setdefault(DOMAIN, {})
    if "midnight_unsub" in domain_data:
        return True

    async def _midnight_update(_) -> None:
        """Update all entities belonging to this integration at midnight."""
        task_entity_ids = []
        registry = entity_registry.async_get(hass)
        for entry in hass.config_entries.async_entries(DOMAIN):
            entries = entity_registry.async_entries_for_config_entry(registry, entry.entry_id)
            for e in entries:
                if e.entity_id.startswith("sensor."):
                    task_entity_ids.append(e.entity_id)
        await async_update_entities(task_entity_ids, hass)
        _LOGGER.debug("Midnight update ran for %s entities", len(task_entity_ids))

    unsub = async_track_time_change(hass, _midnight_update, hour=0, minute=0, second=0)
    domain_data["midnight_unsub"] = unsub

    async def async_mark_as_done(service_call: ServiceCall):
        s = await get_sensor(hass, service_call.data[CONF_ENTITY_ID])
        await s.async_mark_as_done()

    async def async_set_last_done_date(service_call: ServiceCall):
        s = await get_sensor(hass, service_call.data[CONF_ENTITY_ID])
        await s.async_set_last_done_date(service_call.data[CONF_DATE])

    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_AS_DONE,
        async_mark_as_done,
        schema=SERVICE_MARK_AS_DONE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LAST_DONE_DATE,
        async_set_last_done_date,
        schema=SERVICE_SET_LAST_DONE_DATE_SCHEMA,
    )

    cards = TaskTrackerCardRegistration(hass)
    await cards.async_register()

    return True

async def async_update_entities(entity_ids: list[str], hass: HomeAssistant) -> dict | None:
    """Update the entity."""
    try:
        return await hass.services.async_call(
            domain="homeassistant",
            service="update_entity",
            service_data={"entity_id": entity_ids},
            blocking=False,
        )
    except (ServiceValidationError, HomeAssistantError) as err:
        _LOGGER.error("Failed to update entities %s: %s", ", ".join(entity_ids), err)
        raise


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Task Tracker from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry."""

    if entry.version > 1 or entry.minor_version > 2:
        # This means the user has downgraded from a later version
        return False

    if entry.version == 1 and entry.minor_version == 1:
        # 1.1 Migrate config_entry to changed options structure
        new_version = 1
        new_minor_version = 2
        new_options = {
            CONF_ACTIVE: True,
            CONF_TASK_INTERVAL_VALUE: entry.options["task_frequency"],
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_ICON: entry.options[CONF_ICON],
            CONF_TAGS: entry.options["assignees"],
            CONF_TODO_LISTS: [],
            CONF_TODO_OFFSET_DAYS: 0,
            CONF_NOTIFICATION_INTERVAL: entry.options["notification_frequency"],
        }

        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
            version=new_version,
            minor_version=new_minor_version,
        )
    return True


async def get_sensor(hass, entity_id: str) -> TaskTrackerSensor:
    """Get the sensor."""
    s = hass.data["entity_components"][Platform.SENSOR].get_entity(entity_id)
    if s is None:
        raise ValueError(f"Could not find {entity_id}")
    return s
