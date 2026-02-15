"""Camera platform for Moultrie Mobile."""

from __future__ import annotations

import logging
from typing import Any

import requests

from homeassistant.components.camera import Camera
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
    for device_id in coordinator.data.get("devices", {}):
        entities.append(MoultrieCamera(coordinator, device_id))
    async_add_entities(entities)


class MoultrieCamera(MoultrieEntity, Camera):
    """Moultrie trail camera showing latest image."""

    _attr_translation_key = "trail_camera"

    def __init__(self, coordinator: MoultrieCoordinator, device_id: int) -> None:
        MoultrieEntity.__init__(self, coordinator, device_id, "camera")
        Camera.__init__(self)
        self._current_url: str | None = None
        self._cached_image: bytes | None = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.device_data
        if not data or not data.get("latest_image"):
            return {}
        img = data["latest_image"]
        attrs: dict[str, Any] = {}
        if img.get("takenOn"):
            attrs["taken_on"] = img["takenOn"]
        if img.get("temperature"):
            attrs["temperature"] = img["temperature"]
        if img.get("IsOnDemand"):
            attrs["on_demand"] = True
        if img.get("flash"):
            attrs["flash"] = True
        if img.get("imageUrl"):
            attrs["image_url"] = img["imageUrl"]
        if img.get("enhancedImageUrl"):
            attrs["enhanced_image_url"] = img["enhancedImageUrl"]
        return attrs

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        data = self.device_data
        if not data or not data.get("latest_image"):
            return None

        image_url = data["latest_image"].get("imageUrl")
        if not image_url:
            return None

        # Cache the image if URL hasn't changed
        if image_url == self._current_url and self._cached_image:
            return self._cached_image

        try:
            resp = await self.hass.async_add_executor_job(
                lambda: requests.get(image_url, timeout=30)
            )
            resp.raise_for_status()
            self._current_url = image_url
            self._cached_image = resp.content
            return self._cached_image
        except Exception:
            _LOGGER.exception("Failed to fetch camera image from %s", image_url)
            return self._cached_image
