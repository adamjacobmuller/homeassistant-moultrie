"""Sensor platform for Moultrie Mobile."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MoultrieCoordinator
from .entity import MoultrieEntity


@dataclass(frozen=True, kw_only=True)
class MoultrieSensorDescription(SensorEntityDescription):
    """Describe a Moultrie sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _battery_value(data: dict[str, Any]) -> int | None:
    return data["info"].get("DeviceBatteryLevel")


def _signal_value(data: dict[str, Any]) -> int | None:
    return data["info"].get("SignalStrength")


def _storage_free_gb(data: dict[str, Any]) -> float | None:
    free = data["info"].get("FreeStorageBytes")
    if free is None:
        return None
    return round(free / (1024**3), 2)


def _storage_total_gb(data: dict[str, Any]) -> float | None:
    total = data["info"].get("TotalStorageBytes")
    if total is None:
        return None
    return round(total / (1024**3), 2)


def _images_used(data: dict[str, Any]) -> int | None:
    sub = data["info"].get("Subscription", {})
    return sub.get("TotalImagesUsed")


def _sw_version(data: dict[str, Any]) -> str | None:
    return data["info"].get("SoftwareVersion") or None


def _latest_activity(data: dict[str, Any]) -> datetime | None:
    val = data["info"].get("LatestActivity")
    if val is None:
        return None
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _temperature(data: dict[str, Any]) -> float | None:
    img = data.get("latest_image")
    if img and img.get("temperature"):
        try:
            return float(img["temperature"])
        except (ValueError, TypeError):
            return None
    return None


SENSOR_DESCRIPTIONS: list[MoultrieSensorDescription] = [
    MoultrieSensorDescription(
        key="battery",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_battery_value,
    ),
    MoultrieSensorDescription(
        key="signal_strength",
        translation_key="signal_strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
        value_fn=_signal_value,
    ),
    MoultrieSensorDescription(
        key="storage_free",
        translation_key="storage_free",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_storage_free_gb,
    ),
    MoultrieSensorDescription(
        key="storage_total",
        translation_key="storage_total",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_storage_total_gb,
    ),
    MoultrieSensorDescription(
        key="images_used",
        translation_key="images_used",
        icon="mdi:image-multiple",
        state_class=SensorStateClass.TOTAL,
        value_fn=_images_used,
    ),
    MoultrieSensorDescription(
        key="firmware",
        translation_key="firmware",
        icon="mdi:cellphone-arrow-down",
        value_fn=_sw_version,
    ),
    MoultrieSensorDescription(
        key="last_activity",
        translation_key="last_activity",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_latest_activity,
    ),
    MoultrieSensorDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_temperature,
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
        for desc in SENSOR_DESCRIPTIONS:
            entities.append(MoultrieSensor(coordinator, device_id, desc))
    async_add_entities(entities)


class MoultrieSensor(MoultrieEntity, SensorEntity):
    """A Moultrie sensor."""

    entity_description: MoultrieSensorDescription

    def __init__(
        self,
        coordinator: MoultrieCoordinator,
        device_id: int,
        description: MoultrieSensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        data = self.device_data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
