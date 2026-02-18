"""Data update coordinator for Moultrie Mobile."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MoultrieApiClient, MoultrieApiError, MoultrieAuthError
from .const import CONF_ACCESS_TOKEN, CONF_EMAIL, CONF_PASSWORD, CONF_REFRESH_TOKEN, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

SIGNAL_NEW_DEVICE = f"{DOMAIN}_new_device"


class MoultrieCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Moultrie device data."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, client: MoultrieApiClient, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL),
        )
        self.client = client
        self._entry = entry
        self._known_device_ids: set[int] = set()

    async def _async_relogin(self) -> None:
        """Re-login using stored credentials when refresh token expires."""
        email = self._entry.data.get(CONF_EMAIL)
        password = self._entry.data.get(CONF_PASSWORD)
        if not email or not password:
            raise ConfigEntryAuthFailed("No stored credentials for re-login")

        _LOGGER.info("Refresh token expired, re-logging in with stored credentials")
        try:
            tokens = await MoultrieApiClient.login(email, password, self.client._session)
        except MoultrieAuthError as err:
            raise ConfigEntryAuthFailed(
                "Stored credentials are no longer valid"
            ) from err

        self.client._access_token = tokens["access_token"]
        self.client._refresh_token = tokens["refresh_token"]

        # Persist the new tokens
        self.hass.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                CONF_ACCESS_TOKEN: tokens["access_token"],
                CONF_REFRESH_TOKEN: tokens["refresh_token"],
            },
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Moultrie API."""
        try:
            try:
                devices = await self.client.get_devices()
            except MoultrieAuthError:
                await self._async_relogin()
                devices = await self.client.get_devices()

            data: dict[str, Any] = {"devices": {}}
            current_device_ids: set[int] = set()

            for device in devices:
                device_id = device["DeviceId"]
                current_device_ids.add(device_id)

                latest_image = await self.client.get_latest_image(device_id)

                settings = await self.client.get_device_settings(device_id)

                # Build a flat settings lookup by short code
                settings_map: dict[str, dict[str, Any]] = {}
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

            # Detect new devices
            new_devices = current_device_ids - self._known_device_ids
            if self._known_device_ids and new_devices:
                _LOGGER.info("New Moultrie devices detected: %s", new_devices)
                async_dispatcher_send(self.hass, SIGNAL_NEW_DEVICE)

            # Remove stale devices
            removed_devices = self._known_device_ids - current_device_ids
            if removed_devices:
                _LOGGER.info("Moultrie devices removed: %s", removed_devices)
                dev_reg = dr.async_get(self.hass)
                for device_id in removed_devices:
                    device_entry = dev_reg.async_get_device(
                        identifiers={(DOMAIN, str(device_id))}
                    )
                    if device_entry:
                        dev_reg.async_remove_device(device_entry.id)

            self._known_device_ids = current_device_ids
            return data

        except ConfigEntryAuthFailed:
            raise
        except MoultrieApiError as err:
            raise UpdateFailed(f"Error fetching Moultrie data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching Moultrie data: {err}") from err

    def get_device_data(self, device_id: int) -> dict[str, Any] | None:
        """Get data for a specific device."""
        if self.data is None:
            return None
        return self.data.get("devices", {}).get(device_id)
