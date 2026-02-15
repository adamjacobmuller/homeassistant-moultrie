"""Tests for the Moultrie Mobile switch platform."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.moultrie.switch import MoultrieSettingSwitch

from .conftest import MOCK_COORDINATOR_DATA


def _make_switch(
    coordinator: MagicMock,
    setting_short: str = "ODE",
    key: str = "on_demand",
    device_id: int = 12345,
) -> MoultrieSettingSwitch:
    """Create a MoultrieSettingSwitch with a mock coordinator."""
    switch = MoultrieSettingSwitch.__new__(MoultrieSettingSwitch)
    switch.coordinator = coordinator
    switch._device_id = device_id
    switch._setting_short = setting_short
    switch._attr_unique_id = f"{device_id}_{key}"
    switch._attr_translation_key = key
    return switch


def _mock_coordinator(
    data: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock coordinator with device data."""
    coordinator = MagicMock()
    if data is None:
        data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator.data = data
    coordinator.get_device_data = MagicMock(
        side_effect=lambda did: data.get("devices", {}).get(did) if data else None
    )
    coordinator.client = MagicMock()
    coordinator.client.save_device_settings = AsyncMock(return_value=True)
    return coordinator


def test_switch_is_on_true() -> None:
    """Test switch returns True when setting Value is 'T'."""
    coordinator = _mock_coordinator()
    switch = _make_switch(coordinator, setting_short="ODE")

    assert switch.is_on is True


def test_switch_is_on_false() -> None:
    """Test switch returns False when setting Value is 'F'."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    data["devices"][12345]["settings"]["ODE"]["Value"] = "F"
    coordinator = _mock_coordinator(data)
    switch = _make_switch(coordinator, setting_short="ODE")

    assert switch.is_on is False


def test_switch_is_on_missing_device() -> None:
    """Test switch returns None when device data is missing."""
    coordinator = _mock_coordinator()
    switch = _make_switch(coordinator, device_id=99999)

    assert switch.is_on is None


def test_switch_is_on_missing_setting() -> None:
    """Test switch returns None when the setting key is absent."""
    coordinator = _mock_coordinator()
    switch = _make_switch(coordinator, setting_short="NONEXISTENT")

    assert switch.is_on is None


@pytest.mark.asyncio
async def test_switch_turn_on() -> None:
    """Test turning on the switch sets Value to 'T' and calls save."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    data["devices"][12345]["settings"]["ODE"]["Value"] = "F"
    coordinator = _mock_coordinator(data)
    switch = _make_switch(coordinator, setting_short="ODE")
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()

    # The value in settings_groups should now be "T"
    for group in data["devices"][12345]["settings_groups"]:
        for s in group.get("Settings", []):
            if s["SettingShortText"] == "ODE":
                assert s["Value"] == "T"

    coordinator.client.save_device_settings.assert_awaited_once_with(
        12345,
        67890,
        data["devices"][12345]["settings_groups"],
    )
    switch.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_switch_turn_off() -> None:
    """Test turning off the switch sets Value to 'F' and calls save."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator = _mock_coordinator(data)
    switch = _make_switch(coordinator, setting_short="ODE")
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_off()

    for group in data["devices"][12345]["settings_groups"]:
        for s in group.get("Settings", []):
            if s["SettingShortText"] == "ODE":
                assert s["Value"] == "F"

    coordinator.client.save_device_settings.assert_awaited_once_with(
        12345,
        67890,
        data["devices"][12345]["settings_groups"],
    )
    switch.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_switch_api_error_raises_ha_error() -> None:
    """Test that an API error during save raises HomeAssistantError."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator = _mock_coordinator(data)
    coordinator.client.save_device_settings = AsyncMock(
        side_effect=Exception("API failure")
    )
    switch = _make_switch(coordinator, setting_short="ODE")
    switch.async_write_ha_state = MagicMock()

    with pytest.raises(HomeAssistantError):
        await switch.async_turn_on()


@pytest.mark.asyncio
async def test_switch_set_value_no_device_data() -> None:
    """Test that _set_value returns early when device data is None."""
    coordinator = _mock_coordinator()
    switch = _make_switch(coordinator, device_id=99999)
    switch.async_write_ha_state = MagicMock()

    # Should not raise
    await switch.async_turn_on()

    coordinator.client.save_device_settings.assert_not_awaited()
    switch.async_write_ha_state.assert_not_called()
