"""Switch platform for Moultrie Mobile."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MoultrieCoordinator
from .entity import MoultrieEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MoultrieCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device_data in coordinator.data.get("devices", {}).items():
        settings = device_data.get("settings", {})
        # On Demand toggle (ODE)
        if "ODE" in settings:
            entities.append(
                MoultrieSettingSwitch(
                    coordinator, device_id, "on_demand", "ODE", "On demand"
                )
            )
        # Motion Freeze toggle (CFF)
        if "CFF" in settings:
            entities.append(
                MoultrieSettingSwitch(
                    coordinator, device_id, "motion_freeze", "CFF", "Motion freeze"
                )
            )
    async_add_entities(entities)


class MoultrieSettingSwitch(MoultrieEntity, SwitchEntity):
    """Switch for a Moultrie camera toggle setting."""

    _attr_icon = "mdi:toggle-switch"

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        key: str,
        setting_short: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, device_id, key)
        self._setting_short = setting_short
        self._attr_translation_key = key

    @property
    def is_on(self) -> bool | None:
        data = self.device_data
        if data is None:
            return None
        setting = data.get("settings", {}).get(self._setting_short)
        if setting is None:
            return None
        return setting.get("Value") == "T"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_value("T")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_value("F")

    async def _set_value(self, value: str) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.save_device_settings,
            self._device_id,
            [{"SettingShortText": self._setting_short, "Value": value}],
        )
        await self.coordinator.async_request_refresh()
