"""The Task Tracker integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ICON, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError, HomeAssistantError
from homeassistant.helpers import entity_registry, config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_TASK_INTERVAL_VALUE, CONF_DAY, CONF_TASK_INTERVAL_TYPE, CONF_NOTIFICATION_INTERVAL, \
    CONF_DUE_SOON_DAYS, CONF_DUE_SOON_OVERRIDE, CONF_TAGS, CONF_ACTIVE, CONF_TODO_LISTS, SERVICE_MARK_AS_DONE, \
    SERVICE_MARK_AS_DONE_SCHEMA, SERVICE_SET_LAST_DONE_DATE, SERVICE_SET_LAST_DONE_DATE_SCHEMA, CONF_DATE, \
    CONF_SHOW_PANEL, CONF_REPEAT_MODE, CONF_REPEAT_AFTER
from .coordinator import TaskTrackerCoordinator
from .frontend import TaskTrackerCardRegistration

_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_SHOW_PANEL, default=True): bool,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _get_coordinator(hass: HomeAssistant, entity_id: str) -> TaskTrackerCoordinator:
    """Return the coordinator for *entity_id*, raising ValueError if not found."""
    reg = entity_registry.async_get(hass)
    entry = reg.async_get(entity_id)
    if entry is None or entry.config_entry_id is None:
        raise ValueError(f"Could not find config entry for {entity_id}")
    coordinator = hass.data.get(DOMAIN, {}).get(entry.config_entry_id)
    if coordinator is None:
        raise ValueError(
            f"Task Tracker integration not loaded for {entity_id}; "
            "the config entry may still be setting up"
        )
    return coordinator


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
        coordinator = _get_coordinator(hass, service_call.data[CONF_ENTITY_ID])
        await coordinator.async_mark_as_done()

    async def async_set_last_done_date(service_call: ServiceCall):
        coordinator = _get_coordinator(hass, service_call.data[CONF_ENTITY_ID])
        await coordinator.async_set_last_done_date(service_call.data[CONF_DATE])

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

    show_panel = config.get(DOMAIN, {}).get(CONF_SHOW_PANEL, True)

    cards = TaskTrackerCardRegistration(hass)
    await cards.async_register(show_panel=show_panel)

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
    coordinator = TaskTrackerCoordinator(entry.entry_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    result = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    if result:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return result


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry."""

    if entry.version > 1 or entry.minor_version > 4:
        # This means the user has downgraded from a later version
        return False

    if entry.version == 1 and entry.minor_version == 1:
        # 1.1 Migrate config_entry to changed options structure
        new_options = {
            CONF_ACTIVE: True,
            CONF_TASK_INTERVAL_VALUE: entry.options["task_frequency"],
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_ICON: entry.options[CONF_ICON],
            CONF_TAGS: entry.options["assignees"],
            CONF_TODO_LISTS: [],
            "todo_offset_days": 0,
            CONF_NOTIFICATION_INTERVAL: entry.options["notification_frequency"],
        }

        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
            version=1,
            minor_version=2,
        )

    if entry.version == 1 and entry.minor_version == 2:
        # 1.2 Rename todo_offset_days -> due_soon_days and todo_offset_override -> due_soon_override
        new_options = dict(entry.options)
        new_options[CONF_DUE_SOON_DAYS] = new_options.pop("todo_offset_days", 0)
        due_soon_override = new_options.pop("todo_offset_override", None)
        new_options[CONF_DUE_SOON_OVERRIDE] = due_soon_override

        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
            version=1,
            minor_version=3,
        )

    if entry.version == 1 and entry.minor_version == 3:
        # 1.3 Add repeat_mode option (default: repeat_after to preserve existing behaviour)
        new_options = dict(entry.options)
        new_options.setdefault(CONF_REPEAT_MODE, CONF_REPEAT_AFTER)

        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
            version=1,
            minor_version=4,
        )

    return True
