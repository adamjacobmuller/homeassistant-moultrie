"""Tests for the Moultrie Mobile button platform."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.moultrie.button import MoultrieOnDemandButton

from .conftest import MOCK_COORDINATOR_DATA


def _make_button(
    coordinator: MagicMock,
    meid: str = "MEID12345",
    key: str = "request_photo",
    event_type: str = "image",
    device_id: int = 12345,
) -> MoultrieOnDemandButton:
    """Create a MoultrieOnDemandButton with a mock coordinator."""
    button = MoultrieOnDemandButton.__new__(MoultrieOnDemandButton)
    button.coordinator = coordinator
    button._device_id = device_id
    button._meid = meid
    button._event_type = event_type
    button._attr_unique_id = f"{device_id}_{key}"
    button._attr_translation_key = key
    button._attr_icon = "mdi:camera" if event_type == "image" else "mdi:video"
    return button


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
    coordinator.client.request_on_demand = AsyncMock(return_value={})
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_button_press_photo() -> None:
    """Test pressing the photo button calls request_on_demand with 'image'."""
    coordinator = _mock_coordinator()
    button = _make_button(coordinator, event_type="image", key="request_photo")

    await button.async_press()

    coordinator.client.request_on_demand.assert_awaited_once_with(
        "MEID12345",
        "image",
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_button_press_video() -> None:
    """Test pressing the video button calls request_on_demand with 'video'."""
    coordinator = _mock_coordinator()
    button = _make_button(
        coordinator, event_type="video", key="request_video"
    )

    await button.async_press()

    coordinator.client.request_on_demand.assert_awaited_once_with(
        "MEID12345",
        "video",
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_button_api_error_raises_ha_error() -> None:
    """Test that an API error during on-demand request raises HomeAssistantError."""
    coordinator = _mock_coordinator()
    coordinator.client.request_on_demand = AsyncMock(
        side_effect=Exception("API failure")
    )
    button = _make_button(coordinator, event_type="image", key="request_photo")

    with pytest.raises(HomeAssistantError):
        await button.async_press()

    # refresh should NOT have been called since the request failed
    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_button_press_with_different_meid() -> None:
    """Test pressing a button with a different MEID passes the correct value."""
    coordinator = _mock_coordinator()
    button = _make_button(
        coordinator, meid="MEID99999", event_type="image", key="request_photo"
    )

    await button.async_press()

    coordinator.client.request_on_demand.assert_awaited_once_with(
        "MEID99999",
        "image",
    )
