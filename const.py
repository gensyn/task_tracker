"""Constants for the Task Tracker integration."""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID, CONF_ICON, CONF_OPTIONS, CONF_MODE
from homeassistant.helpers.selector import selector

DOMAIN = "task_tracker"
CONF_TASK_INTERVAL_VALUE = "task_interval_value"
CONF_TASK_INTERVAL_TYPE = "task_interval_type"
CONF_NOTIFICATION_INTERVAL = "notification_interval"
CONF_TODO_LISTS = "todo_lists"
CONF_TODO_OFFSET_DAYS = "todo_offset_days"
CONF_DROPDOWN = "dropdown"
CONF_TAGS = "tags"
CONF_ACTIVE = "active"
CONF_SELECT = "select"
CONF_DAY = "day"
CONF_WEEK = "week"
CONF_MONTH = "month"
CONF_YEAR = "year"
CONF_DATE = "date"
CONF_VALUE = "value"
CONF_LABEL = "label"


CONST_DUE = "due"
CONST_DONE = "done"
CONST_INACTIVE = "inactive"
CONST_UNKNOWN = "unknown"

URL_BASE = "/task_tracker"
TASK_TRACKER_CARDS = [
    {
        "name": "Task Tracker Card",
        "filename": "task-tracker-card.js",
        "version": "1.0.0",
    }
]

SERVICE_MARK_AS_DONE = "mark_as_done"
SERVICE_SET_LAST_DONE_DATE = "set_last_done_date"

SERVICE_MARK_AS_DONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
    }
)

SERVICE_SET_LAST_DONE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_DATE): cv.date,
    }
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_TASK_INTERVAL_VALUE, default=7): int,
        vol.Required(CONF_TASK_INTERVAL_TYPE, default=CONF_DAY): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR],
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "task_interval",
            }
        })
    }
)
