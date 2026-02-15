"""Tests for the Moultrie Mobile select platform."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.moultrie.select import MoultrieSelect, MoultrieSelectDescription

from .conftest import MOCK_COORDINATOR_DATA


def _make_description(
    key: str = "capture_mode",
    setting_short: str = "CTD",
) -> MoultrieSelectDescription:
    """Create a MoultrieSelectDescription."""
    return MoultrieSelectDescription(
        key=key,
        translation_key=key,
        setting_short=setting_short,
    )


def _make_select(
    coordinator: MagicMock,
    setting_short: str = "CTD",
    key: str = "capture_mode",
    device_id: int = 12345,
) -> MoultrieSelect:
    """Create a MoultrieSelect with a mock coordinator."""
    desc = _make_description(key=key, setting_short=setting_short)
    select = MoultrieSelect.__new__(MoultrieSelect)
    select.coordinator = coordinator
    select._device_id = device_id
    select._setting_short = setting_short
    select._attr_unique_id = f"{device_id}_{key}"
    select.entity_description = desc
    return select


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


def test_select_options_list() -> None:
    """Test that options returns the list of Text values from setting Options."""
    coordinator = _mock_coordinator()
    select = _make_select(coordinator, setting_short="CTD")

    assert select.options == ["Time Lapse", "Motion Detect", "Both"]


def test_select_options_list_empty() -> None:
    """Test that options returns empty list when setting has no Options."""
    coordinator = _mock_coordinator()
    # CFF has an empty Options list
    select = _make_select(coordinator, setting_short="CFF", key="motion_freeze")

    assert select.options == []


def test_select_options_missing_device() -> None:
    """Test that options returns empty list when device data is missing."""
    coordinator = _mock_coordinator()
    select = _make_select(coordinator, device_id=99999)

    assert select.options == []


def test_select_current_option() -> None:
    """Test that current_option returns the Text matching the current Value."""
    coordinator = _mock_coordinator()
    # CTD has Value="T", which maps to "Time Lapse"
    select = _make_select(coordinator, setting_short="CTD")

    assert select.current_option == "Time Lapse"


def test_select_current_option_different_value() -> None:
    """Test current_option with a different current value."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    data["devices"][12345]["settings"]["CTD"]["Value"] = "M"
    coordinator = _mock_coordinator(data)
    select = _make_select(coordinator, setting_short="CTD")

    assert select.current_option == "Motion Detect"


def test_select_current_option_missing_device() -> None:
    """Test that current_option returns None when device data is missing."""
    coordinator = _mock_coordinator()
    select = _make_select(coordinator, device_id=99999)

    assert select.current_option is None


def test_select_current_option_unknown_value() -> None:
    """Test current_option falls back to raw value when no Option matches."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    data["devices"][12345]["settings"]["CTD"]["Value"] = "X"
    coordinator = _mock_coordinator(data)
    select = _make_select(coordinator, setting_short="CTD")

    # Falls back to the raw Value string when no Option matches
    assert select.current_option == "X"


@pytest.mark.asyncio
async def test_select_change_option() -> None:
    """Test selecting an option maps Text back to Value and saves via API."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator = _mock_coordinator(data)
    select = _make_select(coordinator, setting_short="CTD")
    select.async_write_ha_state = MagicMock()

    await select.async_select_option("Motion Detect")

    # The value in settings_groups should now be "M"
    for group in data["devices"][12345]["settings_groups"]:
        for s in group.get("Settings", []):
            if s["SettingShortText"] == "CTD":
                assert s["Value"] == "M"

    coordinator.client.save_device_settings.assert_awaited_once_with(
        12345,
        67890,
        data["devices"][12345]["settings_groups"],
    )
    select.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_select_change_option_upload_frequency() -> None:
    """Test selecting an option for upload frequency setting."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator = _mock_coordinator(data)
    select = _make_select(
        coordinator, setting_short="MTI", key="upload_frequency"
    )
    select.async_write_ha_state = MagicMock()

    await select.async_select_option("Hourly")

    for group in data["devices"][12345]["settings_groups"]:
        for s in group.get("Settings", []):
            if s["SettingShortText"] == "MTI":
                assert s["Value"] == "1"

    coordinator.client.save_device_settings.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_api_error_raises_ha_error() -> None:
    """Test that an API error during save raises HomeAssistantError."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA)
    coordinator = _mock_coordinator(data)
    coordinator.client.save_device_settings = AsyncMock(
        side_effect=Exception("API failure")
    )
    select = _make_select(coordinator, setting_short="CTD")
    select.async_write_ha_state = MagicMock()

    with pytest.raises(HomeAssistantError):
        await select.async_select_option("Both")


@pytest.mark.asyncio
async def test_select_no_device_data() -> None:
    """Test that async_select_option returns early when device data is None."""
    coordinator = _mock_coordinator()
    select = _make_select(coordinator, device_id=99999)
    select.async_write_ha_state = MagicMock()

    # Should not raise
    await select.async_select_option("Time Lapse")

    coordinator.client.save_device_settings.assert_not_awaited()
    select.async_write_ha_state.assert_not_called()
