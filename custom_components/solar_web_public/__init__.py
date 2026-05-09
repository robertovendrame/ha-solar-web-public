"""Solar Web Public integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarWebPublicClient
from .const import (
    CONF_REFRESH_INTERVAL,
    CONF_SHARED_URL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SolarWebPublicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solar Web Public from a config entry."""

    session = async_get_clientsession(hass)

    client = SolarWebPublicClient(
        session=session,
        shared_url=entry.data[CONF_SHARED_URL],
    )

    coordinator = SolarWebPublicCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
        update_interval_seconds=entry.options.get(
            CONF_REFRESH_INTERVAL,
            entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    await _async_migrate_entity_registry(hass, entry, client)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Solar Web Public config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload integration when options are changed."""

    await hass.config_entries.async_reload(entry.entry_id)


async def _async_migrate_entity_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: SolarWebPublicClient,
) -> None:
    """Migrate old entity unique IDs from token-based IDs to hashed plant keys."""

    registry = er.async_get(hass)

    token = client.token
    plant_key = client.plant_key

    _LOGGER.info(
        "Solar Web Public: Starting entity registry migration for entry %s",
        entry.entry_id,
    )

    migrated_count = 0

    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.domain != "sensor":
            continue

        if not registry_entry.unique_id.startswith(f"{DOMAIN}_{token}_"):
            continue

        _, suffix = registry_entry.unique_id.split(f"{DOMAIN}_{token}_", 1)
        new_unique_id = f"{DOMAIN}_{plant_key}_{suffix}"

        _LOGGER.info(
            "Solar Web Public: Migrating entity %s to hashed unique ID",
            registry_entry.entity_id,
        )

        try:
            registry.async_update_entity(
                registry_entry.entity_id,
                new_unique_id=new_unique_id,
            )
            migrated_count += 1
        except ValueError as err:
            _LOGGER.warning(
                "Solar Web Public: Could not migrate entity %s: %s",
                registry_entry.entity_id,
                err,
            )

    _LOGGER.info(
        "Solar Web Public: Entity registry migration completed for entry %s. Migrated %d entities",
        entry.entry_id,
        migrated_count,
    )