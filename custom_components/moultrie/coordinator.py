"""Data update coordinator for Moultrie Mobile."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MoultrieApiClient, MoultrieApiError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MoultrieCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Moultrie device data."""

    def __init__(self, hass: HomeAssistant, client: MoultrieApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Moultrie API."""
        try:
            devices = await self.hass.async_add_executor_job(self.client.get_devices)

            data: dict[str, Any] = {"devices": {}}

            for device in devices:
                device_id = device["DeviceId"]

                # Get latest image for this camera
                latest_image = await self.hass.async_add_executor_job(
                    self.client.get_latest_image, device_id
                )

                # Get device settings
                settings = await self.hass.async_add_executor_job(
                    self.client.get_device_settings, device_id
                )

                # Build a flat settings lookup by short code
                settings_map: dict[str, dict] = {}
                for group in settings:
                    for setting in group.get("Settings", []):
                        short = setting.get("SettingShortText")
                        if short:
                            settings_map[short] = setting

                data["devices"][device_id] = {
                    "info": device,
                    "latest_image": latest_image,
                    "settings_groups": settings,
                    "settings": settings_map,
                }

            return data

        except Exception as err:
            raise UpdateFailed(f"Error fetching Moultrie data: {err}") from err

    def get_device_data(self, device_id: int) -> dict[str, Any] | None:
        """Get data for a specific device."""
        if self.data is None:
            return None
        return self.data.get("devices", {}).get(device_id)
