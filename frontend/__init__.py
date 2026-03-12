"""Task Tracker JavaScript module registration."""

import logging
import os
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import MODE_STORAGE, LovelaceData
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from ..const import URL_BASE, TASK_TRACKER_CARDS, TASK_TRACKER_PANEL  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class TaskTrackerCardRegistration:
    """Register Javascript modules."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        self.hass = hass
        self.lovelace: LovelaceData = self.hass.data.get("lovelace")
        if hasattr(self.lovelace, "resource_mode"):
            self.resource_mode = self.lovelace.resource_mode
        else:
            # Backwards compatibility before 2026.2
            self.resource_mode = self.lovelace.mode

    async def async_register(self):
        """Register view_assist path."""
        await self._async_register_path()
        if self.resource_mode == MODE_STORAGE:
            await self._async_register_modules()
        await self._async_register_panel()

    # install card resources
    async def _async_register_path(self):
        """Register resource path if not already registered."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(Path(__file__).parent), False)]
            )
            _LOGGER.debug("Registered resource path from %s", Path(__file__).parent)
        except RuntimeError:
            # Runtime error is likley this is already registered.
            _LOGGER.debug("Resource path already registered")

    async def _async_register_modules(self):
        """Register modules if not already registered."""
        _LOGGER.debug("Installing javascript modules")

        # Get resources already registered
        resources = [
            resource
            for resource in self.lovelace.resources.async_items()
            if resource["url"].startswith(URL_BASE)
        ]

        for module in TASK_TRACKER_CARDS:
            url = f"{URL_BASE}/{module.get('filename')}"

            card_registered = False

            for resource in resources:
                if self._get_resource_path(resource["url"]) == url:
                    card_registered = True
                    # check version
                    if self._get_resource_version(resource["url"]) != module.get(
                            "version"
                    ):
                        # Update card version
                        _LOGGER.debug(
                            "Updating %s to version %s",
                            module.get("name"),
                            module.get("version"),
                        )
                        await self.lovelace.resources.async_update_item(
                            resource.get("id"),
                            {
                                "res_type": "module",
                                "url": url + "?v=" + module.get("version"),
                            },
                        )
                        # Remove old gzipped files
                        await self.async_remove_gzip_files()
                    else:
                        _LOGGER.debug(
                            "%s already registered as version %s",
                            module.get("name"),
                            module.get("version"),
                        )

            if not card_registered:
                _LOGGER.debug(
                    "Registering %s as version %s",
                    module.get("name"),
                    module.get("version"),
                )
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": url + "?v=" + module.get("version")}
                )

    def _get_resource_path(self, url: str):
        return url.split("?")[0]

    def _get_resource_version(self, url: str):
        if version := url.split("?")[1].replace("v=", ""):
            return version
        return 0

    async def _async_register_panel(self):
        """Register the Task Tracker sidebar panel."""
        try:
            await async_register_panel(
                self.hass,
                webcomponent_name=TASK_TRACKER_PANEL["webcomponent_name"],
                frontend_url_path=TASK_TRACKER_PANEL["frontend_url_path"],
                module_url=f"{URL_BASE}/{TASK_TRACKER_PANEL['filename']}",
                sidebar_title=TASK_TRACKER_PANEL["sidebar_title"],
                sidebar_icon=TASK_TRACKER_PANEL["sidebar_icon"],
                require_admin=False,
            )
            _LOGGER.debug("Registered Task Tracker panel")
        except HomeAssistantError:
            _LOGGER.debug("Task Tracker panel already registered")

    async def async_unregister(self):
        """Unload lovelace module resource."""
        if self.resource_mode == MODE_STORAGE:
            for module in TASK_TRACKER_CARDS:
                url = f"{URL_BASE}/{module.get('filename')}"
                task_tracker_resources = [
                    resource
                    for resource in self.lovelace.resources.async_items()
                    if str(resource["url"]).startswith(url)
                ]
                for resource in task_tracker_resources:
                    await self.lovelace.resources.async_delete_item(resource.get("id"))

    async def async_remove_gzip_files(self):
        """Remove cached gzip files."""
        await self.hass.async_add_executor_job(self.remove_gzip_files)

    def remove_gzip_files(self):
        """Remove cached gzip files."""
        path = self.hass.config.path("custom_components/task_tracker/frontend")

        gzip_files = [
            filename for filename in os.listdir(path) if filename.endswith(".gz")
        ]

        for file in gzip_files:
            try:
                if (
                        Path.stat(Path(f"{path}/{file}")).st_mtime
                        < Path.stat(Path(f"{path}/{file.replace('.gz', '')}")).st_mtime
                ):
                    _LOGGER.debug("Removing older gzip file - %s", file)
                    Path.unlink(Path(f"{path}/{file}"))
            except OSError:
                pass
