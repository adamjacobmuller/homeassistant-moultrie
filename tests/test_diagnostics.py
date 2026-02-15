"""Tests for the Moultrie Mobile diagnostics."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.moultrie.diagnostics import (
    REDACT_CONFIG,
    REDACT_DATA,
    async_get_config_entry_diagnostics,
)

from .conftest import (
    MOCK_ACCESS_TOKEN,
    MOCK_COORDINATOR_DATA,
    MOCK_EMAIL,
    MOCK_PASSWORD,
    MOCK_REFRESH_TOKEN,
)

REDACTED = "**REDACTED**"


def _mock_entry(
    data: dict[str, Any] | None = None,
    coordinator_data: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock config entry with runtime_data pointing to a mock coordinator."""
    if data is None:
        data = {
            "email": MOCK_EMAIL,
            "password": MOCK_PASSWORD,
            "access_token": MOCK_ACCESS_TOKEN,
            "refresh_token": MOCK_REFRESH_TOKEN,
        }

    entry = MagicMock()
    entry.data = data

    coordinator = MagicMock()
    if coordinator_data is None:
        coordinator_data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator.data = coordinator_data
    entry.runtime_data = coordinator

    return entry


@pytest.mark.asyncio
async def test_diagnostics_redacts_config(hass: HomeAssistant) -> None:
    """Test that email, password, access_token, and refresh_token are redacted."""
    entry = _mock_entry()
    result = await async_get_config_entry_diagnostics(hass, entry)

    config = result["config_entry"]
    assert config["email"] == REDACTED
    assert config["password"] == REDACTED
    assert config["access_token"] == REDACTED
    assert config["refresh_token"] == REDACTED


@pytest.mark.asyncio
async def test_diagnostics_redacts_device_data(hass: HomeAssistant) -> None:
    """Test that sensitive device fields like SerialNumber and MEID are redacted."""
    entry = _mock_entry()
    result = await async_get_config_entry_diagnostics(hass, entry)

    coord_data = result["coordinator_data"]
    device = coord_data["devices"][12345]
    info = device["info"]

    assert info["SerialNumber"] == REDACTED
    assert info["MEID"] == REDACTED


@pytest.mark.asyncio
async def test_diagnostics_includes_coordinator_data(hass: HomeAssistant) -> None:
    """Test that non-sensitive coordinator data is present and unredacted."""
    entry = _mock_entry()
    result = await async_get_config_entry_diagnostics(hass, entry)

    coord_data = result["coordinator_data"]
    assert "devices" in coord_data
    assert 12345 in coord_data["devices"]

    device = coord_data["devices"][12345]
    info = device["info"]

    # Non-sensitive fields should be present and unredacted
    assert info["DeviceName"] == "Test Camera"
    assert info["Model"] == "MCG-14072"
    assert info["DeviceBatteryLevel"] == 85
    assert info["SignalStrength"] == 70
    assert info["IsActive"] is True

    # Settings should be present
    assert "settings_groups" in device
    assert "settings" in device


@pytest.mark.asyncio
async def test_diagnostics_with_none_coordinator_data(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics when coordinator.data is None."""
    entry = _mock_entry(coordinator_data=None)
    # When coordinator.data is None, the fallback is {}
    entry.runtime_data.data = None

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["coordinator_data"] == {}


@pytest.mark.asyncio
async def test_diagnostics_redact_config_keys_match() -> None:
    """Test that the REDACT_CONFIG set contains the expected keys."""
    assert REDACT_CONFIG == {"email", "password", "access_token", "refresh_token"}


@pytest.mark.asyncio
async def test_diagnostics_redact_data_keys_match() -> None:
    """Test that the REDACT_DATA set contains the expected device-level keys."""
    assert REDACT_DATA == {
        "AccountId",
        "SerialNumber",
        "MEID",
        "MacAddress",
        "IMEI",
        "ICCID",
    }
