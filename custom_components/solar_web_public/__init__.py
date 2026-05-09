"""Solar Web Public integration."""

from __future__ import annotations

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
    if registry is None:
        return

    token = client.token
    plant_key = client.plant_key

    # Log migration start
    hass.logger.info(
        "Solar Web Public: Starting entity registry migration for entry %s. "
        "Token: %s, Plant key: %s",
        entry.entry_id,
        token,
        plant_key,
    )

    sensor_keys = [
        "plant",
        "current_power",
        "production_power",
        "consumption_power",
        "grid_power",
        "feed_in_power",
        "grid_import_power",
        "battery_power",
        "battery_soc",
        "today_energy",
        "month_energy",
        "year_energy",
        "total_energy",
        "grid_export_energy_today",
        "grid_import_energy_today",
        "today_earning",
        "month_earning",
        "year_earning",
        "total_earning",
        "diagnostics",
    ]

    migrated_count = 0
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.domain != "sensor":
            continue

        hass.logger.debug(
            "Solar Web Public: Checking entity %s with unique_id %s",
            registry_entry.entity_id,
            registry_entry.unique_id,
        )

        # Check if unique_id uses old token-based format
        if registry_entry.unique_id.startswith(f"{DOMAIN}_{token}_"):
            # Extract suffix after token
            _, suffix = registry_entry.unique_id.split(f"{DOMAIN}_{token}_", 1)
            new_unique_id = f"{DOMAIN}_{plant_key}_{suffix}"

            hass.logger.info(
                "Solar Web Public: Migrating entity %s from %s to %s",
                registry_entry.entity_id,
                registry_entry.unique_id,
                new_unique_id,
            )

            try:
                registry.async_update_entity(
                    registry_entry.entity_id,
                    new_unique_id=new_unique_id,
                )
                migrated_count += 1
            except Exception as e:
                hass.logger.error(
                    "Solar Web Public: Failed to migrate entity %s: %s",
                    registry_entry.entity_id,
                    e,
                )
                continue

    hass.logger.info(
        "Solar Web Public: Migration completed. Migrated %d entities for entry %s",
        migrated_count,
        entry.entry_id,
    )