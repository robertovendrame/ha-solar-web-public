"""Coordinator for Solar Web Public."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarWebPublicApiError, SolarWebPublicClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolarWebPublicCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Solar Web Public data coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: SolarWebPublicClient,
        update_interval_seconds: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=update_interval_seconds),
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Solar.web."""
        try:
            return await self.client.async_get_data()
        except SolarWebPublicApiError as err:
            raise UpdateFailed(str(err)) from err