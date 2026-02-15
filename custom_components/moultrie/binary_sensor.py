"""Binary sensor platform for Moultrie Mobile."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MoultrieCoordinator
from .entity import MoultrieEntity


@dataclass(frozen=True, kw_only=True)
class MoultrieBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Moultrie binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


def _subscription_active(data: dict[str, Any]) -> bool | None:
    sub = data["info"].get("Subscription", {})
    name = sub.get("PlanName")
    if name is None:
        return None
    return not sub.get("IsPendingCancellation", False)


def _device_active(data: dict[str, Any]) -> bool | None:
    return data["info"].get("IsActive")


def _on_demand_enabled(data: dict[str, Any]) -> bool | None:
    return data["info"].get("OnDemandSwitchSetting")


def _pending_settings(data: dict[str, Any]) -> bool | None:
    return data["info"].get("HasPendingSettingsUpdates")


BINARY_SENSOR_DESCRIPTIONS: list[MoultrieBinarySensorDescription] = [
    MoultrieBinarySensorDescription(
        key="subscription_active",
        translation_key="subscription_active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=_subscription_active,
    ),
    MoultrieBinarySensorDescription(
        key="device_active",
        translation_key="device_active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=_device_active,
    ),
    MoultrieBinarySensorDescription(
        key="on_demand_enabled",
        translation_key="on_demand_enabled",
        icon="mdi:camera-wireless",
        value_fn=_on_demand_enabled,
    ),
    MoultrieBinarySensorDescription(
        key="pending_settings",
        translation_key="pending_settings",
        icon="mdi:sync-alert",
        value_fn=_pending_settings,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MoultrieCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id in coordinator.data.get("devices", {}):
        for desc in BINARY_SENSOR_DESCRIPTIONS:
            entities.append(MoultrieBinarySensor(coordinator, device_id, desc))
    async_add_entities(entities)


class MoultrieBinarySensor(MoultrieEntity, BinarySensorEntity):
    """A Moultrie binary sensor."""

    entity_description: MoultrieBinarySensorDescription

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        description: MoultrieBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        data = self.device_data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
