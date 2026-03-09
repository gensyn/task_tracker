ConfigFlowResult = dict


class ConfigEntry:
    def __init__(self, entry_id="test_id", version=1, minor_version=2, data=None, options=None, title=""):
        self.entry_id = entry_id
        self.version = version
        self.minor_version = minor_version
        self.data = data or {}
        self.options = options or {}
        self.title = title


class ConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if domain is not None:
            cls.DOMAIN = domain

    def async_show_form(self, step_id=None, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id}

    def async_create_entry(self, title=None, data=None, options=None):
        result = {"type": "create_entry", "title": title, "data": data or {}}
        if options is not None:
            result["options"] = options
        return result


class OptionsFlowWithReload:
    hass = None
    config_entry = None

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, data=None):
        return {"type": "create_entry", "data": data or {}}

    def add_suggested_values_to_schema(self, schema, values):
        return schema
