"""Tests for the Moultrie Mobile integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.moultrie import (
    async_setup_entry,
    async_unload_entry,
    _update_tokens_if_changed,
)
from custom_components.moultrie.const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    PLATFORMS,
)

from .conftest import (
    MOCK_ACCESS_TOKEN,
    MOCK_COORDINATOR_DATA,
    MOCK_REFRESH_TOKEN,
)


@patch("custom_components.moultrie.MoultrieCoordinator")
@patch("custom_components.moultrie.MoultrieApiClient")
@patch("custom_components.moultrie.async_get_clientsession")
async def test_setup_entry(
    mock_get_session: MagicMock,
    mock_api_cls: MagicMock,
    mock_coord_cls: MagicMock,
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that async_setup_entry creates coordinator and stores it in runtime_data."""
    mock_config_entry.add_to_hass(hass)

    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    mock_client = MagicMock()
    mock_client.access_token = MOCK_ACCESS_TOKEN
    mock_client.refresh_token = MOCK_REFRESH_TOKEN
    mock_api_cls.return_value = mock_client

    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    mock_coord_cls.return_value = mock_coordinator

    with patch.object(
        hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
    ) as mock_forward:
        result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.runtime_data is mock_coordinator

    mock_api_cls.assert_called_once_with(
        access_token=MOCK_ACCESS_TOKEN,
        refresh_token=MOCK_REFRESH_TOKEN,
        session=mock_session,
    )
    mock_coord_cls.assert_called_once_with(hass, mock_client, mock_config_entry)
    mock_coordinator.async_config_entry_first_refresh.assert_awaited_once()
    mock_forward.assert_awaited_once_with(mock_config_entry, PLATFORMS)


@patch("custom_components.moultrie.MoultrieCoordinator")
@patch("custom_components.moultrie.MoultrieApiClient")
@patch("custom_components.moultrie.async_get_clientsession")
async def test_unload_entry(
    mock_get_session: MagicMock,
    mock_api_cls: MagicMock,
    mock_coord_cls: MagicMock,
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that async_unload_entry unloads all platforms."""
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    mock_unload.assert_awaited_once_with(mock_config_entry, PLATFORMS)


async def test_token_update_listener(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that _update_tokens_if_changed updates entry data when tokens differ."""
    mock_config_entry.add_to_hass(hass)

    mock_client = MagicMock()
    mock_client.access_token = "new_access_token"
    mock_client.refresh_token = "new_refresh_token"

    with patch.object(
        hass.config_entries, "async_update_entry"
    ) as mock_update:
        _update_tokens_if_changed(hass, mock_config_entry, mock_client)

    mock_update.assert_called_once()
    call_kwargs = mock_update.call_args
    updated_data = call_kwargs.kwargs["data"] if "data" in call_kwargs.kwargs else call_kwargs[1]["data"]
    assert updated_data[CONF_ACCESS_TOKEN] == "new_access_token"
    assert updated_data[CONF_REFRESH_TOKEN] == "new_refresh_token"


async def test_token_update_listener_no_change(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test that _update_tokens_if_changed does nothing when tokens are unchanged."""
    mock_config_entry.add_to_hass(hass)

    mock_client = MagicMock()
    mock_client.access_token = MOCK_ACCESS_TOKEN
    mock_client.refresh_token = MOCK_REFRESH_TOKEN

    with patch.object(
        hass.config_entries, "async_update_entry"
    ) as mock_update:
        _update_tokens_if_changed(hass, mock_config_entry, mock_client)

    mock_update.assert_not_called()
