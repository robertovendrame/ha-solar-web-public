"""Config flow for Solar Web Public."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarWebInvalidUrlError, SolarWebPublicApiError, SolarWebPublicClient
from .const import (
    CONF_NAME,
    CONF_REFRESH_INTERVAL,
    CONF_SHARED_URL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)


class SolarWebPublicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Web Public."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)

            try:
                client = SolarWebPublicClient(
                    session=session,
                    shared_url=user_input[CONF_SHARED_URL],
                )
                await client.async_get_data()

            except SolarWebInvalidUrlError:
                errors["base"] = "invalid_url"

            except SolarWebPublicApiError:
                errors["base"] = "cannot_connect"

            else:
                await self.async_set_unique_id(client.plant_key)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_SHARED_URL: user_input[CONF_SHARED_URL],
                        CONF_REFRESH_INTERVAL: user_input.get(
                            CONF_REFRESH_INTERVAL,
                            DEFAULT_REFRESH_INTERVAL,
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_SHARED_URL): str,
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=DEFAULT_REFRESH_INTERVAL,
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )