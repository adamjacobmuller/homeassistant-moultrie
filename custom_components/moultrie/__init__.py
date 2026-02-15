"""The Moultrie Mobile integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import MoultrieApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MoultrieCoordinator

_LOGGER = logging.getLogger(__name__)

type MoultrieConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: MoultrieConfigEntry) -> bool:
    """Set up Moultrie Mobile from a config entry."""
    client = MoultrieApiClient(
        access_token=entry.data[CONF_ACCESS_TOKEN],
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
    )

    coordinator = MoultrieCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Store a listener to update tokens when they refresh
    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: _update_tokens_if_changed(hass, entry, client)
        )
    )

    return True


def _update_tokens_if_changed(
    hass: HomeAssistant, entry: ConfigEntry, client: MoultrieApiClient
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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
