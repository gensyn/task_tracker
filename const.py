"""Constants for the Task Tracker integration."""
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import CONF_NAME, CONF_ENTITY_ID, CONF_ICON, CONF_OPTIONS, CONF_MODE
from homeassistant.helpers.selector import selector

DOMAIN = "task_tracker"
CONF_TASK_FREQUENCY_VALUE = "task_frequency_value"
CONF_TASK_FREQUENCY_TYPE = "task_frequency_type"
CONF_NOTIFICATION_FREQUENCY = "notification_frequency"
CONF_DROPDOWN = "dropdown"
CONF_TAGS = "tags"
CONF_ACTIVE = "active"
CONF_SELECT = "select"
CONF_DAY = "day"
CONF_WEEK = "week"
CONF_MONTH = "month"
CONF_YEAR = "year"

CONST_TODO = "todo"
CONST_DONE = "done"
CONST_INACTIVE = "inactive"
CONST_UNKNOWN = "unknown"

URL_BASE = "/task_tracker"
TASK_TRACKER_CARDS = [
    {
        "name": "Task Tracker Card",
        "filename": "task-tracker-card.js",
        "version": "0.0.1",
    }
]

SERVICE_MARK_AS_DONE = "mark_as_done"
SERVICE_SET_LAST_DONE_DATE = "set_last_done_date"

SERVICE_MARK_AS_DONE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)

SERVICE_SET_LAST_DONE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required("year"): int,
        vol.Required("month"): int,
        vol.Required("day"): int,
    }
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_TASK_FREQUENCY_VALUE, default=7): int,
        vol.Required(CONF_TASK_FREQUENCY_TYPE, default=CONF_DAY): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR],
                CONF_MODE: CONF_DROPDOWN,
            }
        }),
        vol.Optional(CONF_NOTIFICATION_FREQUENCY, default=1): int,
        vol.Optional(CONF_TAGS): str,
        vol.Optional(CONF_ICON, default="mdi:calendar-question"): str,
        vol.Optional(CONF_ACTIVE, default=True): bool,
    }
)
STEP_INIT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TASK_FREQUENCY_VALUE, default=7): int,
        vol.Required(CONF_TASK_FREQUENCY_TYPE): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR],
                CONF_MODE: CONF_DROPDOWN,
            }
        }),
        vol.Optional(CONF_NOTIFICATION_FREQUENCY, default=1): int,
        vol.Optional(CONF_TAGS): str,
        vol.Optional(CONF_ICON): str,
        vol.Optional(CONF_ACTIVE): bool,
    }
)