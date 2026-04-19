"""Constants for the Task Tracker integration."""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID, CONF_OPTIONS, CONF_MODE
from homeassistant.helpers.selector import selector

DOMAIN = "task_tracker"
CONF_TASK_INTERVAL_VALUE = "task_interval_value"
CONF_TASK_INTERVAL_TYPE = "task_interval_type"
CONF_NOTIFICATION_INTERVAL = "notification_interval"
CONF_TODO_LISTS = "todo_lists"
CONF_DUE_SOON_DAYS = "due_soon_days"
CONF_DROPDOWN = "dropdown"
CONF_TAGS = "tags"
CONF_ACTIVE = "active"
CONF_ACTIVE_OVERRIDE = "active_override"
CONF_TASK_INTERVAL_OVERRIDE = "task_interval_override"
CONF_DUE_SOON_OVERRIDE = "due_soon_override"
CONF_SELECT = "select"
CONF_DAY = "day"
CONF_WEEK = "week"
CONF_MONTH = "month"
CONF_YEAR = "year"
CONF_DATE = "date"
CONF_VALUE = "value"
CONF_LABEL = "label"
CONF_SHOW_PANEL = "show_panel"
CONF_REPEAT_MODE = "repeat_mode"
CONF_REPEAT_AFTER = "repeat_after"
CONF_REPEAT_EVERY = "repeat_every"

# Repeat-every sub-type constants
CONF_REPEAT_EVERY_TYPE = "repeat_every_type"
CONF_REPEAT_EVERY_WEEKDAY = "repeat_every_weekday"                                 # every N weeks on a weekday
CONF_REPEAT_EVERY_DAY_OF_MONTH = "repeat_every_day_of_month"                      # Nth day of the month
CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH = "repeat_every_weekday_of_month"              # Nth weekday of the month
CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH = "repeat_every_days_before_end_of_month"  # N days before month end

# Field names for repeat_every schedule details
CONF_REPEAT_WEEKDAY = "repeat_weekday"              # which weekday (monday … sunday)
CONF_REPEAT_WEEKS_INTERVAL = "repeat_weeks_interval"  # how many weeks between occurrences
CONF_REPEAT_MONTH_DAY = "repeat_month_day"          # day 1-31 of the month
CONF_REPEAT_NTH_OCCURRENCE = "repeat_nth_occurrence"  # "1","2","3","4","last"
CONF_REPEAT_DAYS_BEFORE_END = "repeat_days_before_end"  # days before month end (0 = last day)
CONF_REPEAT_MONTHS_INTERVAL = "repeat_months_interval"  # how many months between occurrences (>=1)

# Weekday value constants
CONF_MONDAY = "monday"
CONF_TUESDAY = "tuesday"
CONF_WEDNESDAY = "wednesday"
CONF_THURSDAY = "thursday"
CONF_FRIDAY = "friday"
CONF_SATURDAY = "saturday"
CONF_SUNDAY = "sunday"

CONST_DUE = "due"
CONST_DUE_SOON = "due_soon"
CONST_DONE = "done"
CONST_INACTIVE = "inactive"
CONST_UNKNOWN = "unknown"

URL_BASE = "/task_tracker"
TASK_TRACKER_CARDS = [
    {
        "name": "Task Tracker Card",
        "filename": "task-tracker-card.js",
        "version": "2.0.0",
    }
]
TASK_TRACKER_PANEL = {
    "webcomponent_name": "task-tracker-panel",
    "frontend_url_path": "task-tracker",
    "filename": "task-tracker-panel.js",
    "sidebar_title": "Task Tracker",
    "sidebar_icon": "mdi:calendar-check",
}

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
        vol.Required(CONF_REPEAT_MODE, default=CONF_REPEAT_AFTER): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_REPEAT_AFTER, CONF_REPEAT_EVERY],
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "repeat_mode",
            }
        }),
    }
)
