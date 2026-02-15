"""Tests for the Moultrie Mobile sensor platform value functions."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

import pytest

from custom_components.moultrie.sensor import (
    _battery_value,
    _images_used,
    _latest_activity,
    _signal_value,
    _storage_free_gb,
    _storage_total_gb,
    _sw_version,
    _temperature,
)

from .conftest import MOCK_COORDINATOR_DATA, MOCK_DEVICE_INFO, MOCK_LATEST_IMAGE

DEVICE_ID = 12345


def _device_data() -> dict[str, Any]:
    """Return a deep copy of the mock device data for device 12345."""
    return copy.deepcopy(MOCK_COORDINATOR_DATA["devices"][DEVICE_ID])


def test_battery_sensor() -> None:
    """Test battery value is extracted correctly."""
    data = _device_data()
    result = _battery_value(data)
    assert result == 85


def test_signal_strength_sensor() -> None:
    """Test signal strength value is extracted correctly."""
    data = _device_data()
    result = _signal_value(data)
    assert result == 70


def test_storage_free_sensor() -> None:
    """Test free storage bytes are converted to GB correctly."""
    data = _device_data()
    result = _storage_free_gb(data)
    # 5368709120 / 1024^3 = 5.0
    assert result == 5.0


def test_storage_total_sensor() -> None:
    """Test total storage bytes are converted to GB correctly."""
    data = _device_data()
    result = _storage_total_gb(data)
    # 16106127360 / 1024^3 = 15.0
    assert result == 15.0


def test_images_used_sensor() -> None:
    """Test images used is extracted from Subscription."""
    data = _device_data()
    result = _images_used(data)
    assert result == 1500


def test_firmware_sensor() -> None:
    """Test firmware/software version is extracted correctly."""
    data = _device_data()
    result = _sw_version(data)
    assert result == "4.20"


def test_last_activity_sensor() -> None:
    """Test last activity is parsed as a UTC datetime."""
    data = _device_data()
    result = _latest_activity(data)
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result.tzinfo == timezone.utc
    assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def test_temperature_sensor() -> None:
    """Test temperature is extracted from latest_image and cast to float."""
    data = _device_data()
    result = _temperature(data)
    assert result == 45.0
    assert isinstance(result, float)


def test_sensor_unavailable() -> None:
    """Test all value_fn functions return None when device_data is None-like.

    When device_data is None the MoultrieSensor.native_value property
    short-circuits and returns None before calling value_fn. Here we verify
    that each value_fn also handles a data dict with missing keys gracefully.
    """
    empty_data: dict[str, Any] = {"info": {}}

    assert _battery_value(empty_data) is None
    assert _signal_value(empty_data) is None
    assert _storage_free_gb(empty_data) is None
    assert _storage_total_gb(empty_data) is None
    assert _images_used(empty_data) is None
    assert _sw_version(empty_data) is None
    assert _latest_activity(empty_data) is None
    assert _temperature(empty_data) is None


def test_sensor_with_missing_values() -> None:
    """Test value_fn functions return None when specific fields are absent."""
    data = _device_data()

    # Remove individual fields and verify each returns None
    del data["info"]["DeviceBatteryLevel"]
    assert _battery_value(data) is None

    del data["info"]["SignalStrength"]
    assert _signal_value(data) is None

    del data["info"]["FreeStorageBytes"]
    assert _storage_free_gb(data) is None

    del data["info"]["TotalStorageBytes"]
    assert _storage_total_gb(data) is None

    del data["info"]["Subscription"]
    assert _images_used(data) is None

    del data["info"]["SoftwareVersion"]
    assert _sw_version(data) is None

    del data["info"]["LatestActivity"]
    assert _latest_activity(data) is None

    del data["latest_image"]
    assert _temperature(data) is None


def test_temperature_sensor_non_numeric() -> None:
    """Test temperature returns None when the value cannot be cast to float."""
    data = _device_data()
    data["latest_image"]["temperature"] = "not_a_number"
    assert _temperature(data) is None


def test_latest_activity_invalid_format() -> None:
    """Test last activity returns None for unparseable date strings."""
    data = _device_data()
    data["info"]["LatestActivity"] = "not-a-date"
    assert _latest_activity(data) is None


def test_latest_activity_naive_datetime() -> None:
    """Test last activity adds UTC when the parsed datetime is naive."""
    data = _device_data()
    data["info"]["LatestActivity"] = "2024-06-01T12:00:00"
    result = _latest_activity(data)
    assert result is not None
    assert result.tzinfo == timezone.utc
    assert result == datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_firmware_sensor_empty_string() -> None:
    """Test firmware returns None for an empty string value."""
    data = _device_data()
    data["info"]["SoftwareVersion"] = ""
    assert _sw_version(data) is None


def test_temperature_sensor_empty_string() -> None:
    """Test temperature returns None when temperature is an empty string."""
    data = _device_data()
    data["latest_image"]["temperature"] = ""
    assert _temperature(data) is None
