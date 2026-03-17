def async_get(hass):
    return getattr(hass, "entity_registry", None)


def async_entries_for_device(registry, device_id):
    return []


def async_entries_for_config_entry(registry, entry_id):
    return []
