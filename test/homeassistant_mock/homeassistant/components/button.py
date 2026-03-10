class ButtonEntity:
    hass = None
    device_entry = None
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_translation_key = None
    _attr_unique_id = None
    _attr_device_info = None

    async def async_press(self):
        pass
