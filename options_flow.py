"""Options flow for the Task Tracker integration."""
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_ICON, CONF_MODE
from homeassistant.helpers.selector import selector

from .const import (
    CONF_TASK_INTERVAL_VALUE, CONF_NOTIFICATION_INTERVAL, CONF_TAGS, CONF_ACTIVE,
    CONF_TASK_INTERVAL_TYPE, CONF_DUE_SOON_DAYS, CONF_SELECT, CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR,
    CONF_DROPDOWN, CONF_TODO_LISTS, CONF_ACTIVE_OVERRIDE, CONF_TASK_INTERVAL_OVERRIDE, CONF_DUE_SOON_OVERRIDE,
    CONF_OPTIONS, CONF_REPEAT_MODE, CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_TYPE, CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH,
    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH, CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH,
    CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL, CONF_REPEAT_MONTH_DAY, CONF_REPEAT_NTH_OCCURRENCE,
    CONF_REPEAT_DAYS_BEFORE_END,
    CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY,
)

_WEEKDAYS = [CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY]
_NTH_OCCURRENCES = ["1", "2", "3", "4", "last"]

# Step 1 (init) – common task settings that apply regardless of repeat mode
_STEP_INIT_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ACTIVE): bool,
        vol.Optional(CONF_ACTIVE_OVERRIDE): selector({
            "entity": {
                "domain": "input_boolean",
            }
        }),
        vol.Required(CONF_REPEAT_MODE, default=CONF_REPEAT_AFTER): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_REPEAT_AFTER, CONF_REPEAT_EVERY],
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "repeat_mode",
            }
        }),
        vol.Optional(CONF_ICON, default="mdi:calendar-question"): str,
        vol.Optional(CONF_TAGS): str,
        vol.Optional(CONF_TODO_LISTS): selector({
            "entity": {
                "domain": "todo",
                "multiple": True,
            }
        }),
        vol.Optional(CONF_DUE_SOON_DAYS, default=0): int,
        vol.Optional(CONF_DUE_SOON_OVERRIDE): selector({
            "entity": {
                "domain": "input_number",
            }
        }),
        vol.Optional(CONF_NOTIFICATION_INTERVAL, default=1): int,
    }
)

# Step 2a – repeat_after interval settings
_STEP_REPEAT_AFTER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TASK_INTERVAL_VALUE, default=7): int,
        vol.Required(CONF_TASK_INTERVAL_TYPE): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR],
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "task_interval",
            }
        }),
        vol.Optional(CONF_TASK_INTERVAL_OVERRIDE): selector({
            "entity": {
                "domain": "input_number",
            }
        }),
    }
)

# Step 2b – repeat_every sub-type selection
_STEP_REPEAT_EVERY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPEAT_EVERY_TYPE): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [
                    CONF_REPEAT_EVERY_WEEKDAY,
                    CONF_REPEAT_EVERY_DAY_OF_MONTH,
                    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH,
                    CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH,
                ],
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "repeat_every_type",
            }
        }),
    }
)

# Step 3b-1 – every N weeks on a weekday
_STEP_REPEAT_EVERY_WEEKDAY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPEAT_WEEKDAY, default=CONF_MONDAY): selector({
            CONF_SELECT: {
                CONF_OPTIONS: _WEEKDAYS,
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "weekday",
            }
        }),
        vol.Required(CONF_REPEAT_WEEKS_INTERVAL, default=1): int,
    }
)

# Step 3b-2 – every Nth day of the month
_STEP_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPEAT_MONTH_DAY, default=1): int,
    }
)

# Step 3b-3 – every Nth weekday of the month
_STEP_REPEAT_EVERY_WEEKDAY_OF_MONTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPEAT_WEEKDAY, default=CONF_MONDAY): selector({
            CONF_SELECT: {
                CONF_OPTIONS: _WEEKDAYS,
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "weekday",
            }
        }),
        vol.Required(CONF_REPEAT_NTH_OCCURRENCE, default="1"): selector({
            CONF_SELECT: {
                CONF_OPTIONS: _NTH_OCCURRENCES,
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "nth_occurrence",
            }
        }),
    }
)

# Step 3b-4 – N days before the last of the month
_STEP_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPEAT_DAYS_BEFORE_END, default=0): int,
    }
)


class TaskTrackerOptionsFlow(OptionsFlowWithReload):
    """Handle options for an existing Task Tracker config entry."""

    def __init__(self) -> None:
        """Initialise; accumulate user input across steps."""
        super().__init__()
        self._accumulated_options: dict[str, Any] = {}

    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1 – common settings and repeat mode selection."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_INIT_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)

        if user_input[CONF_REPEAT_MODE] == CONF_REPEAT_EVERY:
            return await self.async_step_repeat_every()
        return await self.async_step_repeat_after()

    async def async_step_repeat_after(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2a – interval settings for repeat_after mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_after",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_AFTER_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_repeat_every(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2b – select the repeat_every schedule sub-type."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        etype = user_input[CONF_REPEAT_EVERY_TYPE]

        if etype == CONF_REPEAT_EVERY_DAY_OF_MONTH:
            return await self.async_step_repeat_every_day_of_month()
        if etype == CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH:
            return await self.async_step_repeat_every_weekday_of_month()
        if etype == CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH:
            return await self.async_step_repeat_every_days_before_end_of_month()
        return await self.async_step_repeat_every_weekday()

    async def async_step_repeat_every_weekday(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-1 – every N weeks on a specific weekday."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_weekday",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_WEEKDAY_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_repeat_every_day_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-2 – every Nth day of the month."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_day_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_repeat_every_weekday_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-3 – every Nth weekday of the month."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_weekday_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_WEEKDAY_OF_MONTH_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_repeat_every_days_before_end_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-4 – N days before the last of the month."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_days_before_end_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)


async def validate_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalise and validate raw accumulated user input from the options flow."""
    if user_input.get(CONF_ACTIVE) is None:
        user_input[CONF_ACTIVE] = True

    if not user_input.get(CONF_ICON):
        user_input[CONF_ICON] = "mdi:calendar-question"

    if not user_input[CONF_ICON].startswith("mdi:"):
        user_input[CONF_ICON] = f"mdi:{user_input[CONF_ICON]}"

    if not user_input.get(CONF_TAGS):
        user_input[CONF_TAGS] = ""

    if user_input.get(CONF_TODO_LISTS) is None:
        user_input[CONF_TODO_LISTS] = []

    if user_input.get(CONF_DUE_SOON_DAYS) is None:
        user_input[CONF_DUE_SOON_DAYS] = 0

    if user_input.get(CONF_NOTIFICATION_INTERVAL, 0) < 1:
        user_input[CONF_NOTIFICATION_INTERVAL] = 1

    repeat_mode = user_input.get(CONF_REPEAT_MODE, CONF_REPEAT_AFTER)
    if repeat_mode not in (CONF_REPEAT_AFTER, CONF_REPEAT_EVERY):
        repeat_mode = CONF_REPEAT_AFTER

    # Common fields present in all options entries
    result: dict[str, Any] = {
        CONF_ACTIVE: user_input[CONF_ACTIVE],
        CONF_ACTIVE_OVERRIDE: user_input.get(CONF_ACTIVE_OVERRIDE) or None,
        CONF_REPEAT_MODE: repeat_mode,
        CONF_ICON: user_input[CONF_ICON],
        CONF_TAGS: user_input[CONF_TAGS],
        CONF_TODO_LISTS: user_input[CONF_TODO_LISTS],
        CONF_DUE_SOON_DAYS: user_input[CONF_DUE_SOON_DAYS],
        CONF_DUE_SOON_OVERRIDE: user_input.get(CONF_DUE_SOON_OVERRIDE) or None,
        CONF_NOTIFICATION_INTERVAL: user_input[CONF_NOTIFICATION_INTERVAL],
    }

    if repeat_mode == CONF_REPEAT_AFTER:
        interval_value = user_input.get(CONF_TASK_INTERVAL_VALUE, 7)
        if interval_value is None or interval_value < 1:
            interval_value = 1
        result.update({
            CONF_TASK_INTERVAL_VALUE: interval_value,
            CONF_TASK_INTERVAL_TYPE: user_input.get(CONF_TASK_INTERVAL_TYPE) or CONF_DAY,
            CONF_TASK_INTERVAL_OVERRIDE: user_input.get(CONF_TASK_INTERVAL_OVERRIDE) or None,
            CONF_REPEAT_EVERY_TYPE: None,
            CONF_REPEAT_WEEKDAY: None,
            CONF_REPEAT_WEEKS_INTERVAL: None,
            CONF_REPEAT_MONTH_DAY: None,
            CONF_REPEAT_NTH_OCCURRENCE: None,
            CONF_REPEAT_DAYS_BEFORE_END: None,
        })
    else:  # repeat_every
        weeks_interval = user_input.get(CONF_REPEAT_WEEKS_INTERVAL, 1)
        if weeks_interval is None or weeks_interval < 1:
            weeks_interval = 1
        month_day = user_input.get(CONF_REPEAT_MONTH_DAY, 1)
        if month_day is None or month_day < 1:
            month_day = 1
        month_day = min(31, month_day)
        nth_occurrence = user_input.get(CONF_REPEAT_NTH_OCCURRENCE, "1")
        if nth_occurrence not in _NTH_OCCURRENCES:
            nth_occurrence = "1"
        days_before_end = user_input.get(CONF_REPEAT_DAYS_BEFORE_END, 0)
        if days_before_end is None or days_before_end < 0:
            days_before_end = 0
        result.update({
            # Keep interval fields with safe defaults for backward compat
            CONF_TASK_INTERVAL_VALUE: 7,
            CONF_TASK_INTERVAL_TYPE: CONF_DAY,
            CONF_TASK_INTERVAL_OVERRIDE: None,
            CONF_REPEAT_EVERY_TYPE: user_input.get(CONF_REPEAT_EVERY_TYPE),
            CONF_REPEAT_WEEKDAY: user_input.get(CONF_REPEAT_WEEKDAY),
            CONF_REPEAT_WEEKS_INTERVAL: weeks_interval,
            CONF_REPEAT_MONTH_DAY: month_day,
            CONF_REPEAT_NTH_OCCURRENCE: nth_occurrence,
            CONF_REPEAT_DAYS_BEFORE_END: days_before_end,
        })

    return result
