def empty_config_schema(domain):
    return lambda config: config


def entity_id(value):
    return value


def date(value):
    if isinstance(value, str):
        from datetime import date as _date  # pylint: disable=import-outside-toplevel
        return _date.fromisoformat(value)
    return value
