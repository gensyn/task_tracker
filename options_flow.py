from homeassistant.components.local_todo.const import DOMAIN as LOCAL_TODO_DOMAIN
from homeassistant.config_entries import OptionsFlowWithReload, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_ICON, CONF_OPTIONS, CONF_MODE
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.selector import selector
from .const import CONF_TASK_INTERVAL_VALUE, CONF_NOTIFICATION_INTERVAL, CONF_TAGS, CONF_ACTIVE, \
    CONF_TASK_INTERVAL_TYPE, CONF_TODO_OFFSET_DAYS, CONF_SELECT, CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR, \
    CONF_DROPDOWN, CONF_VALUE, CONF_LABEL, CONF_TODO_LISTS


class TaskTrackerOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        todo_lists = await get_todo_lists(self.hass)

        STEP_INIT_SCHEMA = vol.Schema(
            {
                vol.Optional(CONF_ACTIVE): bool,
                vol.Required(CONF_TASK_INTERVAL_VALUE, default=7): int,
                vol.Required(CONF_TASK_INTERVAL_TYPE): selector({
                    CONF_SELECT: {
                        CONF_OPTIONS: [CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR],
                        CONF_MODE: CONF_DROPDOWN,
                        "translation_key": "task_interval",
                    }
                }),
                vol.Optional(CONF_ICON, default="mdi:calendar-question"): str,
                vol.Optional(CONF_TAGS): str,
                vol.Optional(CONF_TODO_LISTS): selector({
                    CONF_SELECT: {
                        CONF_OPTIONS: [{"value": todo[0], "label": todo[1]} for todo in todo_lists],
                        CONF_MODE: CONF_DROPDOWN,
                        "translation_key": "task_interval",
                        "multiple": True,
                    }
                }),
                vol.Optional(CONF_TODO_OFFSET_DAYS, default=0): int,
                vol.Optional(CONF_NOTIFICATION_INTERVAL, default=1): int,
            }
        )

        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_INIT_SCHEMA, self.config_entry.options
                ),
            )

        options = await validate_options(user_input)

        return self.async_create_entry(data=options)


async def get_todo_lists(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return entity_ids for all entities whose registry entry domain matches integration_domain."""
    registry = entity_registry.async_get(hass)
    return [(entry.entity_id, hass.states.get(entry.entity_id).attributes.get("friendly_name", entry.entity_id)) for entry in registry.entities.values() if entry.platform == LOCAL_TODO_DOMAIN and entry.entity_id.startswith("todo.")]


async def validate_options(user_input: dict[str, Any]) -> dict[str, Any]:
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

    options = {
        CONF_ACTIVE: user_input[CONF_ACTIVE],
        CONF_TASK_INTERVAL_VALUE: user_input[CONF_TASK_INTERVAL_VALUE],
        CONF_TASK_INTERVAL_TYPE: user_input[CONF_TASK_INTERVAL_TYPE],
        CONF_ICON: user_input[CONF_ICON],
        CONF_TAGS: user_input[CONF_TAGS],
        CONF_TODO_LISTS: user_input[CONF_TODO_LISTS],
        CONF_TODO_OFFSET_DAYS: user_input[CONF_TODO_OFFSET_DAYS],
        CONF_NOTIFICATION_INTERVAL: user_input[CONF_NOTIFICATION_INTERVAL],
    }

    return options
