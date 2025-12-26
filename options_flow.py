from typing import Any

from homeassistant.config_entries import OptionsFlowWithReload, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_ICON
from .const import STEP_INIT_SCHEMA, CONF_TASK_FREQUENCY_VALUE, CONF_NOTIFICATION_FREQUENCY, CONF_TAGS, CONF_ACTIVE, \
    CONF_TASK_FREQUENCY_TYPE


class TaskTrackerOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_INIT_SCHEMA, self.config_entry.options
                ),
            )

        options = await validate_options(user_input)

        return self.async_create_entry(data=options)


async def validate_options(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if user_input.get(CONF_TASK_FREQUENCY_VALUE, 0) < 1:
        user_input[CONF_TASK_FREQUENCY_VALUE] = 1

    if user_input.get(CONF_NOTIFICATION_FREQUENCY, 0) < 1:
        user_input[CONF_NOTIFICATION_FREQUENCY] = 1

    if not user_input.get(CONF_TAGS):
        user_input[CONF_TAGS] = ""

    if not user_input.get(CONF_ICON):
        user_input[CONF_ICON] = "mdi:calendar-question"

    if not user_input[CONF_ICON].startswith("mdi:"):
        user_input[CONF_ICON] = f"mdi:{user_input[CONF_ICON]}"

    if user_input.get(CONF_ACTIVE) is None:
        user_input[CONF_ACTIVE] = True

    options = {
        CONF_TASK_FREQUENCY_VALUE: user_input[CONF_TASK_FREQUENCY_VALUE],
        CONF_TASK_FREQUENCY_TYPE: user_input[CONF_TASK_FREQUENCY_TYPE],
        CONF_NOTIFICATION_FREQUENCY: user_input[CONF_NOTIFICATION_FREQUENCY],
        CONF_TAGS: user_input[CONF_TAGS],
        CONF_ICON: user_input[CONF_ICON],
        CONF_ACTIVE: user_input[CONF_ACTIVE],
    }

    return options
