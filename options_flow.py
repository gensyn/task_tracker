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
    CONF_REPEAT_EVERY_SPECIFIC_DATE,
    CONF_REPEAT_WEEKDAY, CONF_REPEAT_WEEKS_INTERVAL, CONF_REPEAT_MONTH_DAY, CONF_REPEAT_NTH_OCCURRENCE,
    CONF_REPEAT_DAYS_BEFORE_END, CONF_REPEAT_MONTH,
    CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY,
)

_WEEKDAYS = [CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY, CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY]
_NTH_OCCURRENCES = ["1", "2", "3", "4", "last"]



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
                    CONF_REPEAT_EVERY_SPECIFIC_DATE,
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

# Step 3b-5 – specific month and day every year
_STEP_REPEAT_EVERY_SPECIFIC_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPEAT_MONTH, default=1): int,
        vol.Required(CONF_REPEAT_MONTH_DAY, default=1): int,
    }
)

# ---------------------------------------------------------------------------
# Common optional fields shared by all combined options steps.
# Split into "head" (active/active_override – always shown first) and "tail"
# (icon, tags, … – shown after the mode-specific fields).
# ---------------------------------------------------------------------------
_REPEAT_EVERY_HEAD_OPTIONS: dict = {
    vol.Optional(CONF_ACTIVE): bool,
    vol.Optional(CONF_ACTIVE_OVERRIDE): selector({
        "entity": {
            "domain": "input_boolean",
        }
    }),
}

_REPEAT_EVERY_TAIL_OPTIONS: dict = {
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

# Combined options steps for repeat_after mode.
# Field order: active / active_override → interval fields → remaining common fields.
_STEP_OPTIONS_REPEAT_AFTER_SCHEMA = vol.Schema({
    **_REPEAT_EVERY_HEAD_OPTIONS,
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
    **_REPEAT_EVERY_TAIL_OPTIONS,
})

# Combined options steps for repeat_every modes.
# Field order: active / active_override → mode-specific fields → remaining common fields.
_STEP_OPTIONS_REPEAT_EVERY_WEEKDAY_SCHEMA = vol.Schema({
    **_REPEAT_EVERY_HEAD_OPTIONS,
    vol.Required(CONF_REPEAT_WEEKDAY, default=CONF_MONDAY): selector({
        CONF_SELECT: {
            CONF_OPTIONS: _WEEKDAYS,
            CONF_MODE: CONF_DROPDOWN,
            "translation_key": "weekday",
        }
    }),
    vol.Required(CONF_REPEAT_WEEKS_INTERVAL, default=1): int,
    **_REPEAT_EVERY_TAIL_OPTIONS,
})

_STEP_OPTIONS_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA = vol.Schema({
    **_REPEAT_EVERY_HEAD_OPTIONS,
    vol.Required(CONF_REPEAT_MONTH_DAY, default=1): int,
    **_REPEAT_EVERY_TAIL_OPTIONS,
})

_STEP_OPTIONS_REPEAT_EVERY_WEEKDAY_OF_MONTH_SCHEMA = vol.Schema({
    **_REPEAT_EVERY_HEAD_OPTIONS,
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
    **_REPEAT_EVERY_TAIL_OPTIONS,
})

_STEP_OPTIONS_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA = vol.Schema({
    **_REPEAT_EVERY_HEAD_OPTIONS,
    vol.Required(CONF_REPEAT_DAYS_BEFORE_END, default=0): int,
    **_REPEAT_EVERY_TAIL_OPTIONS,
})

_STEP_OPTIONS_REPEAT_EVERY_SPECIFIC_DATE_SCHEMA = vol.Schema({
    **_REPEAT_EVERY_HEAD_OPTIONS,
    vol.Required(CONF_REPEAT_MONTH, default=1): int,
    vol.Required(CONF_REPEAT_MONTH_DAY, default=1): int,
    **_REPEAT_EVERY_TAIL_OPTIONS,
})


def _validate_month_day(value: int | None) -> dict[str, str]:
    """Return an errors dict if *value* is not a valid day of month (1–31)."""
    if value is None or not 1 <= value <= 31:
        return {CONF_REPEAT_MONTH_DAY: "invalid_month_day"}
    return {}


def _validate_days_before_end(value: int | None) -> dict[str, str]:
    """Return an errors dict if *value* is not a valid days-before-end-of-month (0–30)."""
    if value is None or not 0 <= value <= 30:
        return {CONF_REPEAT_DAYS_BEFORE_END: "invalid_days_before_end"}
    return {}


def _validate_month(value: int | None) -> dict[str, str]:
    """Return an errors dict if *value* is not a valid month (1–12)."""
    if value is None or not 1 <= value <= 12:
        return {CONF_REPEAT_MONTH: "invalid_month"}
    return {}


class TaskTrackerOptionsFlow(OptionsFlowWithReload):
    """Handle options for an existing Task Tracker config entry."""

    def __init__(self) -> None:
        """Initialise; accumulate user input across steps."""
        super().__init__()
        self._accumulated_options: dict[str, Any] = {}

    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1 – options entry point; routes to the appropriate combined step.

        For all modes the init form is skipped entirely: the flow jumps directly
        to the mode-specific combined options step, which shows both the
        mode-specific fields and the common fields in one page.  The repeat mode
        (and, for ``repeat_every`` tasks, the sub-type) are preserved as-is.
        """
        # For repeat_every entries: skip the init form entirely and go straight
        # to the combined mode-specific step.
        if self.config_entry.options.get(CONF_REPEAT_MODE) == CONF_REPEAT_EVERY:
            # Pre-seed accumulated options with the immutable schedule identity.
            self._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_EVERY
            repeat_every_type = self.config_entry.options.get(CONF_REPEAT_EVERY_TYPE)
            self._accumulated_options[CONF_REPEAT_EVERY_TYPE] = repeat_every_type
            if repeat_every_type == CONF_REPEAT_EVERY_DAY_OF_MONTH:
                return await self.async_step_options_repeat_every_day_of_month()
            if repeat_every_type == CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH:
                return await self.async_step_options_repeat_every_weekday_of_month()
            if repeat_every_type == CONF_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH:
                return await self.async_step_options_repeat_every_days_before_end_of_month()
            if repeat_every_type == CONF_REPEAT_EVERY_SPECIFIC_DATE:
                return await self.async_step_options_repeat_every_specific_date()
            return await self.async_step_options_repeat_every_weekday()

        # repeat_after: skip the init form, go straight to the combined step.
        self._accumulated_options[CONF_REPEAT_MODE] = CONF_REPEAT_AFTER
        return await self.async_step_options_repeat_after()

    async def async_step_options_repeat_after(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Combined options step for repeat_after mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="options_repeat_after",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_AFTER_SCHEMA, self.config_entry.options
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
        if etype == CONF_REPEAT_EVERY_SPECIFIC_DATE:
            return await self.async_step_repeat_every_specific_date()
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

        errors = _validate_month_day(user_input.get(CONF_REPEAT_MONTH_DAY))
        if errors:
            return self.async_show_form(
                step_id="repeat_every_day_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA, user_input
                ),
                errors=errors,
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

        errors = _validate_days_before_end(user_input.get(CONF_REPEAT_DAYS_BEFORE_END))
        if errors:
            return self.async_show_form(
                step_id="repeat_every_days_before_end_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA, user_input
                ),
                errors=errors,
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    # ------------------------------------------------------------------
    # Combined options steps for repeat_every entries.
    # Each shows both the mode-specific fields and the common task settings
    # (active, icon, tags, …) in a single form.  The repeat mode and the
    # repeat_every sub-type are NOT shown – they are preserved as-is from
    # the stored config entry options.
    # ------------------------------------------------------------------

    async def async_step_options_repeat_every_weekday(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Combined options step for repeat_every_weekday mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="options_repeat_every_weekday",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_WEEKDAY_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_options_repeat_every_day_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Combined options step for repeat_every_day_of_month mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="options_repeat_every_day_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA, self.config_entry.options
                ),
            )

        errors = _validate_month_day(user_input.get(CONF_REPEAT_MONTH_DAY))
        if errors:
            return self.async_show_form(
                step_id="options_repeat_every_day_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_DAY_OF_MONTH_SCHEMA, user_input
                ),
                errors=errors,
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_options_repeat_every_weekday_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Combined options step for repeat_every_weekday_of_month mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="options_repeat_every_weekday_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_WEEKDAY_OF_MONTH_SCHEMA, self.config_entry.options
                ),
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_options_repeat_every_days_before_end_of_month(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Combined options step for repeat_every_days_before_end_of_month mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="options_repeat_every_days_before_end_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA, self.config_entry.options
                ),
            )

        errors = _validate_days_before_end(user_input.get(CONF_REPEAT_DAYS_BEFORE_END))
        if errors:
            return self.async_show_form(
                step_id="options_repeat_every_days_before_end_of_month",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_DAYS_BEFORE_END_OF_MONTH_SCHEMA, user_input
                ),
                errors=errors,
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_repeat_every_specific_date(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b-5 – specific month and day every year."""
        if user_input is None:
            return self.async_show_form(
                step_id="repeat_every_specific_date",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_SPECIFIC_DATE_SCHEMA, self.config_entry.options
                ),
            )

        errors = _validate_month(user_input.get(CONF_REPEAT_MONTH))
        errors.update(_validate_month_day(user_input.get(CONF_REPEAT_MONTH_DAY)))
        if errors:
            return self.async_show_form(
                step_id="repeat_every_specific_date",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_REPEAT_EVERY_SPECIFIC_DATE_SCHEMA, user_input
                ),
                errors=errors,
            )

        self._accumulated_options.update(user_input)
        options = await validate_options(self._accumulated_options)
        return self.async_create_entry(data=options)

    async def async_step_options_repeat_every_specific_date(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Combined options step for repeat_every_specific_date mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="options_repeat_every_specific_date",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_SPECIFIC_DATE_SCHEMA, self.config_entry.options
                ),
            )

        errors = _validate_month(user_input.get(CONF_REPEAT_MONTH))
        errors.update(_validate_month_day(user_input.get(CONF_REPEAT_MONTH_DAY)))
        if errors:
            return self.async_show_form(
                step_id="options_repeat_every_specific_date",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_OPTIONS_REPEAT_EVERY_SPECIFIC_DATE_SCHEMA, user_input
                ),
                errors=errors,
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
            CONF_REPEAT_MONTH: None,
        })
    else:  # repeat_every
        weeks_interval = user_input.get(CONF_REPEAT_WEEKS_INTERVAL, 1)
        if weeks_interval is None or weeks_interval < 1:
            weeks_interval = 1
        month_day = user_input.get(CONF_REPEAT_MONTH_DAY, 1)
        if month_day is None:
            month_day = 1
        if not 1 <= month_day <= 31:
            raise vol.Invalid(
                f"Day of month must be between 1 and 31, got {month_day}",
                path=[CONF_REPEAT_MONTH_DAY],
            )
        nth_occurrence = user_input.get(CONF_REPEAT_NTH_OCCURRENCE, "1")
        if nth_occurrence not in _NTH_OCCURRENCES:
            nth_occurrence = "1"
        days_before_end = user_input.get(CONF_REPEAT_DAYS_BEFORE_END, 0)
        if days_before_end is None:
            days_before_end = 0
        if not 0 <= days_before_end <= 30:
            raise vol.Invalid(
                f"Days before month end must be between 0 and 30, got {days_before_end}",
                path=[CONF_REPEAT_DAYS_BEFORE_END],
            )
        month = user_input.get(CONF_REPEAT_MONTH, 1)
        if month is None:
            month = 1
        if not 1 <= month <= 12:
            raise vol.Invalid(
                f"Month must be between 1 and 12, got {month}",
                path=[CONF_REPEAT_MONTH],
            )
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
            CONF_REPEAT_MONTH: month,
        })

    return result
