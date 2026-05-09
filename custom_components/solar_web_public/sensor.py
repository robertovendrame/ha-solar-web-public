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
class SolarWebSensorEntityDescription(SensorEntityDescription):
    """Solar Web sensor entity description."""

    data_key: str | None = None


SENSOR_DESCRIPTIONS: tuple[SolarWebSensorEntityDescription, ...] = (
    SolarWebSensorEntityDescription(
        key="plant",
        translation_key="plant",
        icon="mdi:solar-power-variant",
        data_key=None,
    ),
    SolarWebSensorEntityDescription(
        key="current_power",
        translation_key="current_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="current_power_w",
    ),
    SolarWebSensorEntityDescription(
        key="today_energy",
        translation_key="today_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="today_energy_kwh",
    ),
    SolarWebSensorEntityDescription(
        key="total_energy",
        translation_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="total_energy_kwh",
    ),
    SolarWebSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="battery_soc",
    ),
    SolarWebSensorEntityDescription(
        key="grid_power",
        translation_key="grid_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="grid_power_w",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solar Web Public sensors."""

    coordinator: SolarWebPublicCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        SolarWebPublicSensor(
            coordinator=coordinator,
            entry=entry,
            description=description,
        )
        for description in SENSOR_DESCRIPTIONS
    )


class SolarWebPublicSensor(
    CoordinatorEntity[SolarWebPublicCoordinator],
    SensorEntity,
):
    """Solar Web Public sensor."""

    entity_description: SolarWebSensorEntityDescription

    def __init__(
        self,
        coordinator: SolarWebPublicCoordinator,
        entry: ConfigEntry,
        description: SolarWebSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)

        self.entity_description = description
        self._entry = entry
        self._plant_name = entry.data[CONF_NAME]

        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": self._plant_name,
            "manufacturer": "Fronius",
            "model": "Solar.web shared plant",
        }

    @property
    def native_value(self) -> Any:
        """Return native value."""

        data = self.coordinator.data or {}

        if self.entity_description.key == "plant":
            return data.get("status", "unknown")

        if self.entity_description.data_key is None:
            return None

        return data.get(self.entity_description.data_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""

        if self.entity_description.key != "plant":
            return None

        data = self.coordinator.data or {}

        return {
            "name": self._plant_name,
            "plant_name": data.get("plant_name"),
            "location": data.get("location"),
            "current_power_w": data.get("current_power_w"),
            "today_energy_kwh": data.get("today_energy_kwh"),
            "total_energy_kwh": data.get("total_energy_kwh"),
            "battery_soc": data.get("battery_soc"),
            "grid_power_w": data.get("grid_power_w"),
            "last_update": data.get("last_update"),
            "content_type": data.get("content_type"),
            "payload_length": data.get("payload_length"),
            "token": data.get("token"),
        }