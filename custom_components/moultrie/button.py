"""Button platform for Moultrie Mobile."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
        info = device_data["info"]
        meid = info.get("MEID")
        if meid and info.get("OnDemandSwitchSetting"):
            entities.append(
                MoultrieOnDemandButton(
                    coordinator, device_id, meid, "request_photo", "image"
                )
            )
            if info.get("CanUploadVideo"):
                entities.append(
                    MoultrieOnDemandButton(
                        coordinator, device_id, meid, "request_video", "video"
                    )
                )
    async_add_entities(entities)


class MoultrieOnDemandButton(MoultrieEntity, ButtonEntity):
    """Button to request an on-demand photo or video."""

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        meid: str,
        key: str,
        event_type: str,
    ) -> None:
        super().__init__(coordinator, device_id, key)
        self._meid = meid
        self._event_type = event_type
        self._attr_translation_key = key
        self._attr_icon = (
            "mdi:camera" if event_type == "image" else "mdi:video"
        )

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.request_on_demand,
            self._meid,
            self._event_type,
        )
        _LOGGER.info(
            "Requested on-demand %s from %s", self._event_type, self._meid
        )
        # Refresh after a delay to pick up the new image
        await self.coordinator.async_request_refresh()
