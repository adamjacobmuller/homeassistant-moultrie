"""Tests for the Moultrie Mobile data update coordinator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.moultrie.api import MoultrieApiError
from custom_components.moultrie.const import DOMAIN
from custom_components.moultrie.coordinator import (
    SIGNAL_NEW_DEVICE,
    MoultrieCoordinator,
)

from .conftest import (
    MOCK_COORDINATOR_DATA,
    MOCK_DEVICE_INFO,
    MOCK_LATEST_IMAGE,
    MOCK_SETTINGS_GROUPS,
    _build_settings_map,
)


async def test_successful_data_fetch(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that a successful update returns the expected data structure."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)

    data = await coordinator._async_update_data()

    assert "devices" in data
    assert 12345 in data["devices"]

    device_data = data["devices"][12345]
    assert device_data["info"] == MOCK_DEVICE_INFO
    assert device_data["latest_image"] == MOCK_LATEST_IMAGE
    assert device_data["settings_groups"] == MOCK_SETTINGS_GROUPS
    assert device_data["settings"] == _build_settings_map(MOCK_SETTINGS_GROUPS)

    # Verify all expected setting short codes are present
    assert "CTD" in device_data["settings"]
    assert "CCM" in device_data["settings"]
    assert "MTI" in device_data["settings"]

    mock_api_client.get_devices.assert_awaited_once()
    mock_api_client.get_latest_image.assert_awaited_once_with(12345)
    mock_api_client.get_device_settings.assert_awaited_once_with(12345)


async def test_update_failed_on_api_error(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that a MoultrieApiError raises UpdateFailed."""
    mock_api_client.get_devices = AsyncMock(
        side_effect=MoultrieApiError("API is down")
    )
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)

    with pytest.raises(UpdateFailed, match="Error fetching Moultrie data"):
        await coordinator._async_update_data()


async def test_update_failed_on_generic_exception(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that a generic exception also raises UpdateFailed."""
    mock_api_client.get_devices = AsyncMock(
        side_effect=RuntimeError("unexpected failure")
    )
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)

    with pytest.raises(UpdateFailed, match="Error fetching Moultrie data"):
        await coordinator._async_update_data()


async def test_get_device_data(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test get_device_data returns the correct device entry."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)
    coordinator.data = MOCK_COORDINATOR_DATA

    result = coordinator.get_device_data(12345)

    assert result is not None
    assert result["info"] == MOCK_DEVICE_INFO
    assert result["latest_image"] == MOCK_LATEST_IMAGE
    assert result["settings_groups"] == MOCK_SETTINGS_GROUPS


async def test_get_device_data_no_data(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test get_device_data returns None when coordinator has no data."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)
    coordinator.data = None

    assert coordinator.get_device_data(12345) is None


async def test_get_device_data_unknown_device(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test get_device_data returns None for a device ID not in data."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)
    coordinator.data = MOCK_COORDINATOR_DATA

    assert coordinator.get_device_data(99999) is None


async def test_new_device_detection(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that SIGNAL_NEW_DEVICE fires when a new device appears."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)

    # First update: populates _known_device_ids, no signal expected
    await coordinator._async_update_data()

    # Second update: introduce a new device
    new_device: dict[str, Any] = {
        **MOCK_DEVICE_INFO,
        "DeviceId": 67890,
        "DeviceName": "New Camera",
    }
    mock_api_client.get_devices = AsyncMock(
        return_value=[MOCK_DEVICE_INFO, new_device]
    )

    with patch(
        "custom_components.moultrie.coordinator.async_dispatcher_send"
    ) as mock_dispatch:
        data = await coordinator._async_update_data()

        mock_dispatch.assert_called_once_with(hass, SIGNAL_NEW_DEVICE)

    # Both devices should be present in the returned data
    assert 12345 in data["devices"]
    assert 67890 in data["devices"]


async def test_no_signal_on_first_update(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that SIGNAL_NEW_DEVICE does NOT fire on the very first update."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)

    with patch(
        "custom_components.moultrie.coordinator.async_dispatcher_send"
    ) as mock_dispatch:
        await coordinator._async_update_data()

        mock_dispatch.assert_not_called()


async def test_stale_device_removal(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that a device is removed from the registry when it disappears."""
    mock_config_entry.add_to_hass(hass)
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)
    coordinator.config_entry = mock_config_entry

    # First update: device 12345 is present
    await coordinator._async_update_data()

    # Register the device in the device registry so removal can find it
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "12345")},
        name="Test Camera",
    )

    # Confirm device exists in registry
    device_entry = dev_reg.async_get_device(identifiers={(DOMAIN, "12345")})
    assert device_entry is not None

    # Second update: device 12345 disappears
    mock_api_client.get_devices = AsyncMock(return_value=[])

    await coordinator._async_update_data()

    # Device should have been removed from the registry
    device_entry = dev_reg.async_get_device(identifiers={(DOMAIN, "12345")})
    assert device_entry is None


async def test_stale_device_removal_device_not_in_registry(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test stale device removal does not error when device is not in registry."""
    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)

    # First update: device 12345 is present
    await coordinator._async_update_data()

    # Second update: device 12345 disappears but was never in the device registry
    mock_api_client.get_devices = AsyncMock(return_value=[])

    # Should not raise
    data = await coordinator._async_update_data()
    assert data["devices"] == {}


async def test_multiple_devices(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test coordinator handles multiple devices."""
    second_device: dict[str, Any] = {
        **MOCK_DEVICE_INFO,
        "DeviceId": 99999,
        "DeviceName": "Second Camera",
    }
    mock_api_client.get_devices = AsyncMock(
        return_value=[MOCK_DEVICE_INFO, second_device]
    )

    coordinator = MoultrieCoordinator(hass, mock_api_client, mock_config_entry)
    data = await coordinator._async_update_data()

    assert 12345 in data["devices"]
    assert 99999 in data["devices"]

    # API should have been called for each device
    assert mock_api_client.get_latest_image.await_count == 2
    assert mock_api_client.get_device_settings.await_count == 2
