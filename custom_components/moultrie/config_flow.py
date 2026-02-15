"""Config flow for Moultrie Mobile."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MoultrieApiClient, MoultrieAuthError
from .const import CONF_ACCESS_TOKEN, CONF_EMAIL, CONF_PASSWORD, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class MoultrieConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Moultrie Mobile."""

    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    async def _async_validate_credentials(
        self, email: str, password: str
    ) -> dict[str, str]:
        """Validate credentials and return tokens."""
        session = async_get_clientsession(self.hass)
        return await MoultrieApiClient.login(email, password, session)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                tokens = await self._async_validate_credentials(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
            except MoultrieAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Moultrie ({user_input[CONF_EMAIL]})",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCESS_TOKEN: tokens["access_token"],
                        CONF_REFRESH_TOKEN: tokens["refresh_token"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when token refresh fails."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._reauth_entry is not None
            try:
                tokens = await self._async_validate_credentials(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
            except MoultrieAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCESS_TOKEN: tokens["access_token"],
                        CONF_REFRESH_TOKEN: tokens["refresh_token"],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=self._reauth_entry.data.get(CONF_EMAIL) if self._reauth_entry else "",
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfigure step."""
        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfigure confirmation step."""
        errors: dict[str, str] = {}
        reconfigure_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        assert reconfigure_entry is not None

        if user_input is not None:
            try:
                tokens = await self._async_validate_credentials(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
            except MoultrieAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during reconfigure")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCESS_TOKEN: tokens["access_token"],
                        CONF_REFRESH_TOKEN: tokens["refresh_token"],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=reconfigure_entry.data.get(CONF_EMAIL, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
