"""Config flow for the Task Tracker integration."""

from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from typing import Any

from .const import DOMAIN, STEP_USER_DATA_SCHEMA
from .options_flow import TaskTrackerOptionsFlow, validate_options

_LOGGER = logging.getLogger(__name__)


class TaskTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Task Tracker."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors={})

        data = {
            CONF_NAME: user_input[CONF_NAME],
        }

        options = await validate_options(user_input)

        return self.async_create_entry(title=user_input[CONF_NAME], data=data, options=options)

    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: ConfigEntry,
    ) -> TaskTrackerOptionsFlow:
        """Create the options flow."""
        return TaskTrackerOptionsFlow()
