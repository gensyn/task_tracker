def async_get_blueprints(hass):
    return getattr(hass, "automation_blueprints", None)
