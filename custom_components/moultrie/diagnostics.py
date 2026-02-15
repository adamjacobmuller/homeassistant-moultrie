"""Diagnostics support for Moultrie Mobile."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MoultrieConfigEntry

REDACT_CONFIG = {
    "email",
    "password",
    "access_token",
    "refresh_token",
}

REDACT_DATA = {
    "AccountId",
    "SerialNumber",
    "MEID",
    "MacAddress",
    "IMEI",
    "ICCID",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: MoultrieConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "config_entry": async_redact_data(dict(entry.data), REDACT_CONFIG),
        "coordinator_data": async_redact_data(
            coordinator.data or {}, REDACT_DATA
        ),
    }
