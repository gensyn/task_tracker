class SensorEntity:
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_translation_key = None
    _attr_native_value = None
    _attr_extra_state_attributes = None
    _attr_device_info = None
    _attr_name = None
    _attr_unique_id = None
    hass = None
    entity_id = None

    def async_write_ha_state(self):
        pass

    def async_on_remove(self, cb):
        pass


class RestoreSensor:
    async def async_added_to_hass(self):
        pass

    async def async_get_last_sensor_data(self):
        return None

    async def async_get_last_state(self):
        return None
