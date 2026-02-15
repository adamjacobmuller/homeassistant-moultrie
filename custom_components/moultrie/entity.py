"""Base entity for Moultrie Mobile."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MoultrieCoordinator


class MoultrieEntity(CoordinatorEntity[MoultrieCoordinator]):
    """Base class for Moultrie entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"

    @property
    def device_data(self) -> dict[str, Any] | None:
        """Return data for this device."""
        return self.coordinator.get_device_data(self._device_id)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for this entity."""
        data = self.device_data
        if data is None:
            return None
        info: dict[str, Any] = data["info"]
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=info.get("DeviceName", f"Moultrie {self._device_id}"),
            manufacturer="Moultrie",
            model=info.get("DisplayName") or info.get("Model", "Unknown"),
            sw_version=info.get("SoftwareVersion"),
            serial_number=info.get("SerialNumber"),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.device_data is not None and super().available
