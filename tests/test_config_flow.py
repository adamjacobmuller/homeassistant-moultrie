"""Tests for the Moultrie Mobile config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_REAUTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.moultrie.api import MoultrieAuthError
from custom_components.moultrie.const import (
    CONF_ACCESS_TOKEN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

from .conftest import (
    MOCK_ACCESS_TOKEN,
    MOCK_EMAIL,
    MOCK_PASSWORD,
    MOCK_REFRESH_TOKEN,
)


async def test_user_step_success(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a successful user step creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Moultrie ({MOCK_EMAIL})"
    assert result["data"] == {
        CONF_EMAIL: MOCK_EMAIL,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
        CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
    }
    assert result["result"].unique_id == MOCK_EMAIL

    mock_login.assert_awaited_once_with(MOCK_EMAIL, MOCK_PASSWORD, mock_login.call_args[0][2])
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_step_invalid_auth(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that MoultrieAuthError returns an invalid_auth error."""
    mock_login.side_effect = MoultrieAuthError("Invalid credentials")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    assert len(mock_setup_entry.mock_calls) == 0


async def test_user_step_cannot_connect(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that a generic Exception returns a cannot_connect error."""
    mock_login.side_effect = Exception("Connection refused")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    assert len(mock_setup_entry.mock_calls) == 0


async def test_user_step_already_configured(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry,
) -> None:
    """Test that a duplicate unique_id aborts with already_configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_step_success(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry,
) -> None:
    """Test a successful reauth flow updates the entry."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    new_password = "new_password_456"
    new_access = "new_access_token"
    new_refresh = "new_refresh_token"
    mock_login.return_value = {
        "access_token": new_access,
        "refresh_token": new_refresh,
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: new_password},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert mock_config_entry.data[CONF_EMAIL] == MOCK_EMAIL
    assert mock_config_entry.data[CONF_PASSWORD] == new_password
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == new_access
    assert mock_config_entry.data[CONF_REFRESH_TOKEN] == new_refresh


async def test_reauth_step_invalid_auth(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry,
) -> None:
    """Test reauth with bad credentials shows invalid_auth error."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    mock_login.side_effect = MoultrieAuthError("Bad credentials")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: "wrong_password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_step_success(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry,
) -> None:
    """Test a successful reconfigure flow updates the entry."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"

    new_email = "newemail@example.com"
    new_password = "new_password_789"
    new_access = "reconfigured_access_token"
    new_refresh = "reconfigured_refresh_token"
    mock_login.return_value = {
        "access_token": new_access,
        "refresh_token": new_refresh,
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: new_email, CONF_PASSWORD: new_password},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert mock_config_entry.data[CONF_EMAIL] == new_email
    assert mock_config_entry.data[CONF_PASSWORD] == new_password
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == new_access
    assert mock_config_entry.data[CONF_REFRESH_TOKEN] == new_refresh


async def test_reconfigure_step_invalid_auth(
    hass: HomeAssistant,
    mock_login: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry,
) -> None:
    """Test reconfigure with bad credentials shows invalid_auth error."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"

    mock_login.side_effect = MoultrieAuthError("Bad credentials")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: "wrong_password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"
    assert result["errors"] == {"base": "invalid_auth"}
