"""Select platform for Moultrie Mobile."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MoultrieConfigEntry
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
    entry: MoultrieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moultrie select entities."""
    coordinator = entry.runtime_data
    entities: list[MoultrieSelect] = []
    for device_id, device_data in coordinator.data.get("devices", {}).items():
        settings = device_data.get("settings", {})
        for desc in SELECT_DESCRIPTIONS:
            if desc.setting_short in settings:
                entities.append(MoultrieSelect(coordinator, device_id, desc))
    async_add_entities(entities)


class MoultrieSelect(MoultrieEntity, SelectEntity):
    """Select entity for a Moultrie dropdown camera setting."""

    entity_description: MoultrieSelectDescription
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        description: MoultrieSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._setting_short = description.setting_short

    @property
    def _setting_data(self) -> dict[str, Any] | None:
        """Get the setting data for this entity."""
        data = self.device_data
        if data is None:
            return None
        return data.get("settings", {}).get(self._setting_short)

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        setting = self._setting_data
        if setting is None:
            return []
        opts = setting.get("Options", [])
        return [opt["Text"] for opt in opts if "Text" in opt]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        setting = self._setting_data
        if setting is None:
            return None
        current_val = setting.get("Value")
        for opt in setting.get("Options", []):
            if opt.get("Value") == current_val:
                return opt.get("Text")
        return current_val

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        data = self.device_data
        setting = self._setting_data
        if data is None or setting is None:
            return

        value = option
        for opt in setting.get("Options", []):
            if opt.get("Text") == option:
                value = opt["Value"]
                break

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
