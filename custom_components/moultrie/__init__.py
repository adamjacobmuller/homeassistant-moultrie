"""The Moultrie Mobile integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MoultrieApiClient, MoultrieAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    PLATFORMS,
)
from .coordinator import MoultrieCoordinator

_LOGGER = logging.getLogger(__name__)

type MoultrieConfigEntry = ConfigEntry[MoultrieCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MoultrieConfigEntry) -> bool:
    """Set up Moultrie Mobile from a config entry."""
    session = async_get_clientsession(hass)
    client = MoultrieApiClient(
        access_token=entry.data[CONF_ACCESS_TOKEN],
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        session=session,
    )

    coordinator = MoultrieCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: _update_tokens_if_changed(hass, entry, client)
        )
    )

    return True


def _update_tokens_if_changed(
    hass: HomeAssistant, entry: MoultrieConfigEntry, client: MoultrieApiClient
) -> None:
    """Update stored tokens if the client has refreshed them."""
    if (
        client.access_token != entry.data.get(CONF_ACCESS_TOKEN)
        or client.refresh_token != entry.data.get(CONF_REFRESH_TOKEN)
    ):
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: client.access_token,
                CONF_REFRESH_TOKEN: client.refresh_token,
            },
        )


async def async_unload_entry(hass: HomeAssistant, entry: MoultrieConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
