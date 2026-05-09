"""Sensors for Solar Web Public."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import SolarWebPublicCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarWebSensorDescription(SensorEntityDescription):
    """Solar Web sensor description."""

    data_key: str | None = None


SENSOR_DESCRIPTIONS: tuple[SolarWebSensorDescription, ...] = (
    SolarWebSensorDescription(
        key="plant",
        name=None,
        icon="mdi:solar-power-variant",
        data_key=None,
    ),
    SolarWebSensorDescription(
        key="current_power",
        name="Potenza attuale",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="current_power_w",
    ),
    SolarWebSensorDescription(
        key="today_energy",
        name="Energia oggi",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="today_energy_kwh",
    ),
    SolarWebSensorDescription(
        key="total_energy",
        name="Energia totale",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="total_energy_kwh",
    ),
    SolarWebSensorDescription(
        key="battery_soc",
        name="Batteria",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="battery_soc",
    ),
    SolarWebSensorDescription(
        key="grid_power",
        name="Potenza rete",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="grid_power_w",
    ),
    SolarWebSensorDescription(
        key="diagnostics",
        name="Diagnostica",
        icon="mdi:bug-outline",
        data_key=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solar Web Public sensors."""

    coordinator: SolarWebPublicCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SolarWebPublicSensor(
            coordinator=coordinator,
            entry=entry,
            description=description,
        )
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class SolarWebPublicSensor(
    CoordinatorEntity[SolarWebPublicCoordinator],
    SensorEntity,
):
    """Solar Web Public sensor."""

    entity_description: SolarWebSensorDescription

    def __init__(
        self,
        coordinator: SolarWebPublicCoordinator,
        entry: ConfigEntry,
        description: SolarWebSensorDescription,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)

        self.entity_description = description
        self._entry = entry
        self._plant_name = entry.data[CONF_NAME]

        token = coordinator.client.token

        if description.key == "plant":
            self._attr_name = self._plant_name
            self._attr_unique_id = f"{DOMAIN}_{token}_plant"
        else:
            self._attr_name = f"{self._plant_name} {description.name}"
            self._attr_unique_id = f"{DOMAIN}_{token}_{description.key}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, token)},
            "name": self._plant_name,
            "manufacturer": "Fronius",
            "model": "Solar.web shared plant",
        }

    @property
    def native_value(self) -> Any:
        """Return the native value."""

        data = self.coordinator.data or {}

        if self.entity_description.key == "plant":
            return data.get("status", "unknown")

        if self.entity_description.key == "diagnostics":
            payload_length = data.get("payload_length")
            if payload_length is None:
                return "unknown"
            if int(payload_length) > 0:
                return "ok"
            return "empty"

        if self.entity_description.data_key is None:
            return None

        return data.get(self.entity_description.data_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        Important:
        keep attributes also on diagnostics and main plant sensor,
        like the original YAML/template test file.
        """

        data = self.coordinator.data or {}

        base_attributes: dict[str, Any] = {
            "configured_name": self._plant_name,
            "plant_name": data.get("plant_name"),
            "location": data.get("location"),
            "page_title": data.get("page_title"),
            "status": data.get("status"),
            "token": data.get("token"),
            "input_url": data.get("input_url"),
            "final_url": data.get("final_url"),
            "last_update": data.get("last_update"),
            "current_power_w": data.get("current_power_w"),
            "today_energy_kwh": data.get("today_energy_kwh"),
            "total_energy_kwh": data.get("total_energy_kwh"),
            "battery_soc": data.get("battery_soc"),
            "grid_power_w": data.get("grid_power_w"),
        }

        if self.entity_description.key == "plant":
            return base_attributes

        if self.entity_description.key == "diagnostics":
            return {
                **base_attributes,
                "content_type": data.get("content_type"),
                "payload_length": data.get("payload_length"),
                "has_api": data.get("has_api"),
                "has_public_display": data.get("has_public_display"),
                "has_current_power": data.get("has_current_power"),
                "has_pv_system": data.get("has_pv_system"),
                "script_count": data.get("script_count"),
                "script_sources": data.get("script_sources"),
                "api_candidates": data.get("api_candidates"),
                "debug_preview": data.get("debug_preview"),
            }

        return base_attributes