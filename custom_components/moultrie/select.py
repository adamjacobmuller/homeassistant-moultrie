"""Select platform for Moultrie Mobile."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MoultrieCoordinator
from .entity import MoultrieEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class MoultrieSelectDescription(SelectEntityDescription):
    """Describe a Moultrie select entity."""

    setting_short: str


SELECT_DESCRIPTIONS: list[MoultrieSelectDescription] = [
    MoultrieSelectDescription(
        key="capture_mode",
        translation_key="capture_mode",
        setting_short="CTD",
        icon="mdi:camera-burst",
    ),
    MoultrieSelectDescription(
        key="photo_video_mode",
        translation_key="photo_video_mode",
        setting_short="CCM",
        icon="mdi:camera-switch",
    ),
    MoultrieSelectDescription(
        key="upload_frequency",
        translation_key="upload_frequency",
        setting_short="MTI",
        icon="mdi:cloud-upload",
    ),
    MoultrieSelectDescription(
        key="photo_resolution",
        translation_key="photo_resolution",
        setting_short="CCR",
        icon="mdi:image-size-select-large",
    ),
    MoultrieSelectDescription(
        key="multi_shot",
        translation_key="multi_shot",
        setting_short="CMS",
        icon="mdi:image-multiple",
    ),
    MoultrieSelectDescription(
        key="video_resolution",
        translation_key="video_resolution",
        setting_short="CVR",
        icon="mdi:video-high-definition",
    ),
    MoultrieSelectDescription(
        key="pir_sensitivity",
        translation_key="pir_sensitivity",
        setting_short="CPR",
        icon="mdi:motion-sensor",
    ),
    MoultrieSelectDescription(
        key="power_source",
        translation_key="power_source",
        setting_short="BAT",
        icon="mdi:battery",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MoultrieCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device_data in coordinator.data.get("devices", {}).items():
        settings = device_data.get("settings", {})
        for desc in SELECT_DESCRIPTIONS:
            if desc.setting_short in settings:
                entities.append(
                    MoultrieSelect(coordinator, device_id, desc)
                )
    async_add_entities(entities)


class MoultrieSelect(MoultrieEntity, SelectEntity):
    """Select entity for a Moultrie dropdown camera setting."""

    entity_description: MoultrieSelectDescription

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        description: MoultrieSelectDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._setting_short = description.setting_short

    @property
    def _setting_data(self) -> dict | None:
        data = self.device_data
        if data is None:
            return None
        return data.get("settings", {}).get(self._setting_short)

    @property
    def options(self) -> list[str]:
        setting = self._setting_data
        if setting is None:
            return []
        opts = setting.get("Options", [])
        return [opt["Text"] for opt in opts if "Text" in opt]

    @property
    def current_option(self) -> str | None:
        setting = self._setting_data
        if setting is None:
            return None
        current_val = setting.get("Value")
        for opt in setting.get("Options", []):
            if opt.get("Value") == current_val:
                return opt.get("Text")
        return current_val

    async def async_select_option(self, option: str) -> None:
        setting = self._setting_data
        if setting is None:
            return
        # Find the value code for the selected text
        value = option
        for opt in setting.get("Options", []):
            if opt.get("Text") == option:
                value = opt["Value"]
                break

        await self.hass.async_add_executor_job(
            self.coordinator.client.save_device_settings,
            self._device_id,
            [{"SettingShortText": self._setting_short, "Value": value}],
        )
        await self.coordinator.async_request_refresh()
