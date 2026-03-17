"""Options flow for the Task Tracker integration."""
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import OptionsFlow, ConfigFlowResult
from homeassistant.const import CONF_ICON, CONF_MODE
from homeassistant.helpers.selector import selector
from .const import CONF_TASK_INTERVAL_VALUE, CONF_NOTIFICATION_INTERVAL, CONF_TAGS, CONF_ACTIVE, \
    CONF_TASK_INTERVAL_TYPE, CONF_TODO_OFFSET_DAYS, CONF_SELECT, CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR, \
    CONF_DROPDOWN, CONF_TODO_LISTS, CONF_ACTIVE_OVERRIDE, CONF_TASK_INTERVAL_OVERRIDE, CONF_TODO_OFFSET_OVERRIDE, \
    CONF_OPTIONS

_STEP_INIT_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ACTIVE): bool,
        vol.Optional(CONF_ACTIVE_OVERRIDE): selector({
            "entity": {
                "domain": "input_boolean",
            }
        }),
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
        vol.Optional(CONF_ICON, default="mdi:calendar-question"): str,
        vol.Optional(CONF_TAGS): str,
        vol.Optional(CONF_TODO_LISTS): selector({
            "entity": {
                "domain": "todo",
                "multiple": True,
            }
        }),
        vol.Optional(CONF_TODO_OFFSET_DAYS, default=0): int,
        vol.Optional(CONF_TODO_OFFSET_OVERRIDE): selector({
            "entity": {
                "domain": "input_number",
            }
        }),
        vol.Optional(CONF_NOTIFICATION_INTERVAL, default=1): int,
    }
)


<<<<<<< copilot/add-regression-integration-tests
class TaskTrackerOptionsFlow(OptionsFlow):
=======
class TaskTrackerOptionsFlow(OptionsFlowWithReload):
    """Handle options for an existing Task Tracker config entry."""

>>>>>>> main
    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    _STEP_INIT_SCHEMA, self.config_entry.options
                ),
            )

        options = await validate_options(user_input)

        return self.async_create_entry(data=options)


async def validate_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalise and validate raw user input from the options form."""
    if user_input.get(CONF_ACTIVE) is None:
        user_input[CONF_ACTIVE] = True

    if user_input.get(CONF_TASK_INTERVAL_VALUE, 0) < 1:
        user_input[CONF_TASK_INTERVAL_VALUE] = 1

    if not user_input.get(CONF_TASK_INTERVAL_TYPE):
        user_input[CONF_TASK_INTERVAL_TYPE] = CONF_DAY

    if not user_input.get(CONF_ICON):
        user_input[CONF_ICON] = "mdi:calendar-question"

    if not user_input[CONF_ICON].startswith("mdi:"):
        user_input[CONF_ICON] = f"mdi:{user_input[CONF_ICON]}"

    if not user_input.get(CONF_TAGS):
        user_input[CONF_TAGS] = ""

    if user_input.get(CONF_TODO_LISTS) is None:
        user_input[CONF_TODO_LISTS] = []

    if user_input.get(CONF_TODO_OFFSET_DAYS) is None:
        user_input[CONF_TODO_OFFSET_DAYS] = 0

    if user_input.get(CONF_NOTIFICATION_INTERVAL, 0) < 1:
        user_input[CONF_NOTIFICATION_INTERVAL] = 1

    return {
        CONF_ACTIVE: user_input[CONF_ACTIVE],
        CONF_ACTIVE_OVERRIDE: user_input.get(CONF_ACTIVE_OVERRIDE) or None,
        CONF_TASK_INTERVAL_VALUE: user_input[CONF_TASK_INTERVAL_VALUE],
        CONF_TASK_INTERVAL_TYPE: user_input[CONF_TASK_INTERVAL_TYPE],
        CONF_TASK_INTERVAL_OVERRIDE: user_input.get(CONF_TASK_INTERVAL_OVERRIDE) or None,
        CONF_ICON: user_input[CONF_ICON],
        CONF_TAGS: user_input[CONF_TAGS],
        CONF_TODO_LISTS: user_input[CONF_TODO_LISTS],
        CONF_TODO_OFFSET_DAYS: user_input[CONF_TODO_OFFSET_DAYS],
        CONF_TODO_OFFSET_OVERRIDE: user_input.get(CONF_TODO_OFFSET_OVERRIDE) or None,
        CONF_NOTIFICATION_INTERVAL: user_input[CONF_NOTIFICATION_INTERVAL],
    }
