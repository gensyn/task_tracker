def generate_entity_id(format_str, value, hass=None):
    return format_str.replace("{}", value)
