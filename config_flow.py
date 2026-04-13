"""Config flow for the Task Tracker integration."""

from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MODE
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from typing import Any
import voluptuous as vol

from .const import (
    DOMAIN, STEP_USER_DATA_SCHEMA, CONF_REPEAT_MODE, CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_TASK_INTERVAL_VALUE, CONF_TASK_INTERVAL_TYPE, CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR,
    CONF_SELECT, CONF_DROPDOWN, CONF_OPTIONS,
    CONF_REPEAT_EVERY_TYPE, CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH,
    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH, CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH,
    CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL, CONF_REPEAT_MONTH_DAY, CONF_REPEAT_NTH_OCCURRENCE,
    CONF_REPEAT_DAYS_BEFORE_END,
    CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY,
)
from .options_flow import TaskTrackerOptionsFlow, validate_options

_LOGGER = logging.getLogger(__name__)

_WEEKDAYS = [CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY]
_NTH_OCCURRENCES = ["1", "2", "3", "4", "last"]

# Step 2a – repeat_after: interval configuration
_STEP_REPEAT_AFTER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TASK_INTERVAL_VALUE, default=7): int,
        vol.Required(CONF_TASK_INTERVAL_TYPE, default=CONF_DAY): selector({
            CONF_SELECT: {
                CONF_OPTIONS: [CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR],
                CONF_MODE: CONF_DROPDOWN,
                "translation_key": "task_interval",
            }
        }),
    }
)

# Step 2b – repeat_every: schedule sub-type selection
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


class TaskTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Task Tracker."""

    VERSION = 1
    MINOR_VERSION = 6

    def __init__(self) -> None:
        """Initialise; accumulate user input across steps."""
        super().__init__()
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1 – name and repeat mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors={})

        self._user_input.update(user_input)

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
                data_schema=_STEP_REPEAT_AFTER_SCHEMA,
                errors={},
            )

        self._user_input.update(user_input)
        name = self._user_input[CONF_NAME]
        options = await validate_options(self._user_input)
        return self.async_create_entry(title=name, data={CONF_NAME: name}, options=options)

    async def async_step_repeat_every(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2b – select the repeat_every schedule sub-type."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every",
                data_schema=_STEP_REPEAT_EVERY_SCHEMA,
                errors={},
            )

        self._user_input.update(user_input)
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
                data_schema=_STEP_REPEAT_EVERY_WEEKDAY_SCHEMA,
                errors={},
            )

        self._user_input.update(user_input)
        name = self._user_input[CONF_NAME]
        options = await validate_options(self._user_input)
        return self.async_create_entry(title=name, data={CONF_NAME: name}, options=options)

    async def async_step_repeat_every_day_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-2 – every Nth day of the month."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_day_of_month",
                data_schema=_STEP_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA,
                errors={},
            )

        self._user_input.update(user_input)
        name = self._user_input[CONF_NAME]
        options = await validate_options(self._user_input)
        return self.async_create_entry(title=name, data={CONF_NAME: name}, options=options)

    async def async_step_repeat_every_weekday_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-3 – every Nth weekday of the month."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_weekday_of_month",
                data_schema=_STEP_REPEAT_EVERY_WEEKDAY_OF_MONTH_SCHEMA,
                errors={},
            )

        self._user_input.update(user_input)
        name = self._user_input[CONF_NAME]
        options = await validate_options(self._user_input)
        return self.async_create_entry(title=name, data={CONF_NAME: name}, options=options)

    async def async_step_repeat_every_days_before_end_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-4 – N days before the last of the month."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_days_before_end_of_month",
                data_schema=_STEP_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA,
                errors={},
            )

        self._user_input.update(user_input)
        name = self._user_input[CONF_NAME]
        options = await validate_options(self._user_input)
        return self.async_create_entry(title=name, data={CONF_NAME: name}, options=options)

    @staticmethod
    @callback
    def async_get_options_flow(
            _config_entry: ConfigEntry,
    ) -> TaskTrackerOptionsFlow:
        """Create the options flow."""
        return TaskTrackerOptionsFlow()
