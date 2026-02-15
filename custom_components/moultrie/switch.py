"""Switch platform for Moultrie Mobile."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MoultrieConfigEntry
from .coordinator import MoultrieCoordinator
from .entity import MoultrieEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MoultrieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moultrie switch entities."""
    coordinator = entry.runtime_data
    entities: list[MoultrieSettingSwitch] = []
    for device_id, device_data in coordinator.data.get("devices", {}).items():
        settings = device_data.get("settings", {})
        if "ODE" in settings:
            entities.append(
                MoultrieSettingSwitch(coordinator, device_id, "on_demand", "ODE")
            )
        if "CFF" in settings:
            entities.append(
                MoultrieSettingSwitch(coordinator, device_id, "motion_freeze", "CFF")
            )
    async_add_entities(entities)


class MoultrieSettingSwitch(MoultrieEntity, SwitchEntity):
    """Switch for a Moultrie camera toggle setting."""

    _attr_icon = "mdi:toggle-switch"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        key: str,
        setting_short: str,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, device_id, key)
        self._setting_short = setting_short
        self._attr_translation_key = key

    @property
    def is_on(self) -> bool | None:
        """Return the current state."""
        data = self.device_data
        if data is None:
            return None
        setting = data.get("settings", {}).get(self._setting_short)
        if setting is None:
            return None
        return setting.get("Value") == "T"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self._set_value("T")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self._set_value("F")

    async def _set_value(self, value: str) -> None:
        """Set the setting value via the API."""
        data = self.device_data
        if data is None:
            return

        for group in data["settings_groups"]:
            for s in group.get("Settings", []):
                if s.get("SettingShortText") == self._setting_short:
                    s["Value"] = value

        modem_id = data["info"].get("ModemId", 0)
        try:
            await self.coordinator.client.save_device_settings(
                self._device_id,
                modem_id,
                data["settings_groups"],
            )
        except Exception as err:
            raise HomeAssistantError(
                translation_domain="moultrie",
                translation_key="settings_save_failed",
            ) from err
        self.async_write_ha_state()
