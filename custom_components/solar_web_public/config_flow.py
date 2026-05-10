"""Config flow for Solar Web Public."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarWebInvalidUrlError, SolarWebPublicApiError, SolarWebPublicClient
from .const import (
    ALL_SENSOR_KEYS,
    CONF_ENABLED_SENSOR_GROUPS,
    CONF_ENABLED_SENSORS,
    CONF_NAME,
    CONF_REFRESH_INTERVAL,
    CONF_SHARED_URL,
    DEFAULT_ENABLED_SENSOR_KEYS,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    SENSOR_GROUP_LABELS,
    SENSOR_GROUPS,
    SENSOR_LABELS,
)


def _sensor_options() -> list[dict[str, str]]:
    """Return selectable sensor options."""

    return [
        {
            "value": sensor_key,
            "label": SENSOR_LABELS[sensor_key],
        }
        for sensor_key in ALL_SENSOR_KEYS
    ]


def _sensor_group_options() -> list[dict[str, str]]:
    """Return selectable sensor group options."""

    return [
        {
            "value": group_key,
            "label": SENSOR_GROUP_LABELS[group_key],
        }
        for group_key in SENSOR_GROUPS
    ]


def _sensors_from_groups(group_keys: list[str]) -> list[str]:
    """Return sensor keys enabled by selected groups."""

    sensors: list[str] = []

    for group_key in group_keys:
        for sensor_key in SENSOR_GROUPS.get(group_key, []):
            if sensor_key not in sensors:
                sensors.append(sensor_key)

    if not sensors:
        sensors = DEFAULT_ENABLED_SENSOR_KEYS.copy()

    return sensors


class SolarWebPublicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Web Public."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""

        self._user_input: dict = {}

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SolarWebPublicOptionsFlow:
        """Create the options flow."""

        return SolarWebPublicOptionsFlow(config_entry)

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

                self._user_input = user_input
                return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_SHARED_URL): str,
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=DEFAULT_REFRESH_INTERVAL,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=3600,
                        step=30,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_ENABLED_SENSOR_GROUPS,
                    default=[],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_sensor_group_options(),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_sensors(self, user_input=None):
        """Handle individual sensor selection."""

        selected_groups = self._user_input.get(CONF_ENABLED_SENSOR_GROUPS, [])
        default_sensors = _sensors_from_groups(selected_groups)

        if user_input is not None:
            enabled_sensors = user_input.get(
                CONF_ENABLED_SENSORS,
                default_sensors,
            )

            if not enabled_sensors:
                enabled_sensors = [ALL_SENSOR_KEYS[0]]

            return self.async_create_entry(
                title=self._user_input[CONF_NAME],
                data={
                    CONF_NAME: self._user_input[CONF_NAME],
                    CONF_SHARED_URL: self._user_input[CONF_SHARED_URL],
                    CONF_REFRESH_INTERVAL: self._user_input.get(
                        CONF_REFRESH_INTERVAL,
                        DEFAULT_REFRESH_INTERVAL,
                    ),
                },
                options={
                    CONF_REFRESH_INTERVAL: self._user_input.get(
                        CONF_REFRESH_INTERVAL,
                        DEFAULT_REFRESH_INTERVAL,
                    ),
                    CONF_ENABLED_SENSOR_GROUPS: selected_groups,
                    CONF_ENABLED_SENSORS: enabled_sensors,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLED_SENSORS,
                    default=default_sensors,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_sensor_options(),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
        )
class SolarWebPublicOptionsFlow(config_entries.OptionsFlow):
    """Handle Solar Web Public options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

        self._config_entry = config_entry
        self._user_input: dict = {}

    async def async_step_init(self, user_input=None):
        """Manage integration options."""

        if user_input is not None:
            self._user_input = user_input
            return await self.async_step_sensors()

        current_refresh_interval = self._config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self._config_entry.data.get(
                CONF_REFRESH_INTERVAL,
                DEFAULT_REFRESH_INTERVAL,
            ),
        )

        current_groups = self._config_entry.options.get(CONF_ENABLED_SENSOR_GROUPS, [])

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=current_refresh_interval,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=3600,
                        step=30,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_ENABLED_SENSOR_GROUPS,
                    default=current_groups,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_sensor_group_options(),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    async def async_step_sensors(self, user_input=None):
        """Handle individual sensor selection."""

        current_enabled_sensors = self._config_entry.options.get(
            CONF_ENABLED_SENSORS,
            DEFAULT_ENABLED_SENSOR_KEYS,
        )
        current_groups = self._config_entry.options.get(CONF_ENABLED_SENSOR_GROUPS, [])

        selected_groups = self._user_input.get(
            CONF_ENABLED_SENSOR_GROUPS,
            current_groups,
        )

        if selected_groups:
            default_sensors = _sensors_from_groups(selected_groups)
        else:
            default_sensors = current_enabled_sensors

        if user_input is not None:
            enabled_sensors = user_input.get(
                CONF_ENABLED_SENSORS,
                default_sensors,
            )

            if not enabled_sensors:
                enabled_sensors = [ALL_SENSOR_KEYS[0]]

            return self.async_create_entry(
                title="",
                data={
                    CONF_REFRESH_INTERVAL: self._user_input.get(
                        CONF_REFRESH_INTERVAL,
                        DEFAULT_REFRESH_INTERVAL,
                    ),
                    CONF_ENABLED_SENSOR_GROUPS: selected_groups,
                    CONF_ENABLED_SENSORS: enabled_sensors,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLED_SENSORS,
                    default=default_sensors,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_sensor_options(),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
        )