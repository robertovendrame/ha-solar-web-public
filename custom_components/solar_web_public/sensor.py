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
    CURRENCY_EURO,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALL_SENSOR_KEYS,
    CONF_ENABLED_SENSORS,
    CONF_NAME,
    DEFAULT_ENABLED_SENSOR_KEYS,
    DOMAIN,
    SENSOR_BATTERY_POWER,
    SENSOR_BATTERY_SOC,
    SENSOR_CONSUMPTION_POWER,
    SENSOR_CURRENT_POWER,
    SENSOR_DIAGNOSTICS,
    SENSOR_FEED_IN_POWER,
    SENSOR_GRID_EXPORT_ENERGY_TODAY,
    SENSOR_GRID_IMPORT_ENERGY_TODAY,
    SENSOR_GRID_IMPORT_POWER,
    SENSOR_GRID_POWER,
    SENSOR_MONTH_EARNING,
    SENSOR_MONTH_ENERGY,
    SENSOR_PLANT,
    SENSOR_PRODUCTION_POWER,
    SENSOR_TODAY_EARNING,
    SENSOR_TODAY_ENERGY,
    SENSOR_TOTAL_EARNING,
    SENSOR_TOTAL_ENERGY,
    SENSOR_YEAR_EARNING,
    SENSOR_YEAR_ENERGY,
)
from .coordinator import SolarWebPublicCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarWebSensorDescription(SensorEntityDescription):
    """Solar Web sensor description."""

    data_key: str | None = None


SENSOR_DESCRIPTIONS: dict[str, SolarWebSensorDescription] = {
    SENSOR_PLANT: SolarWebSensorDescription(
        key=SENSOR_PLANT,
        name=None,
        data_key=None,
    ),
    SENSOR_CURRENT_POWER: SolarWebSensorDescription(
        key=SENSOR_CURRENT_POWER,
        name="Potenza attuale",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="current_power_w",
    ),
    SENSOR_PRODUCTION_POWER: SolarWebSensorDescription(
        key=SENSOR_PRODUCTION_POWER,
        name="Potenza produzione",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="production_w",
    ),
    SENSOR_CONSUMPTION_POWER: SolarWebSensorDescription(
        key=SENSOR_CONSUMPTION_POWER,
        name="Potenza consumo",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="consumption_w",
    ),
    SENSOR_GRID_POWER: SolarWebSensorDescription(
        key=SENSOR_GRID_POWER,
        name="Potenza rete",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="grid_power_w",
    ),
    SENSOR_FEED_IN_POWER: SolarWebSensorDescription(
        key=SENSOR_FEED_IN_POWER,
        name="Potenza immessa in rete",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="feed_in_w",
    ),
    SENSOR_GRID_IMPORT_POWER: SolarWebSensorDescription(
        key=SENSOR_GRID_IMPORT_POWER,
        name="Potenza prelevata dalla rete",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="energy_from_grid_w",
    ),
    SENSOR_BATTERY_POWER: SolarWebSensorDescription(
        key=SENSOR_BATTERY_POWER,
        name="Potenza batteria",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="battery_power_w",
    ),
    SENSOR_BATTERY_SOC: SolarWebSensorDescription(
        key=SENSOR_BATTERY_SOC,
        name="Batteria",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="battery_soc",
    ),
    SENSOR_TODAY_ENERGY: SolarWebSensorDescription(
        key=SENSOR_TODAY_ENERGY,
        name="Energia oggi",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="today_energy_kwh",
    ),
    SENSOR_MONTH_ENERGY: SolarWebSensorDescription(
        key=SENSOR_MONTH_ENERGY,
        name="Energia mese",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="month_energy_kwh",
    ),
    SENSOR_YEAR_ENERGY: SolarWebSensorDescription(
        key=SENSOR_YEAR_ENERGY,
        name="Energia anno",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="year_energy_kwh",
    ),
    SENSOR_TOTAL_ENERGY: SolarWebSensorDescription(
        key=SENSOR_TOTAL_ENERGY,
        name="Energia totale",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="total_energy_kwh",
    ),
    SENSOR_GRID_EXPORT_ENERGY_TODAY: SolarWebSensorDescription(
        key=SENSOR_GRID_EXPORT_ENERGY_TODAY,
        name="Energia immessa oggi",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="chart_to_grid_kwh",
    ),
    SENSOR_GRID_IMPORT_ENERGY_TODAY: SolarWebSensorDescription(
        key=SENSOR_GRID_IMPORT_ENERGY_TODAY,
        name="Energia prelevata oggi",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_key="chart_from_grid_kwh",
    ),
    SENSOR_TODAY_EARNING: SolarWebSensorDescription(
        key=SENSOR_TODAY_EARNING,
        name="Guadagno oggi",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        data_key="today_earning",
    ),
    SENSOR_MONTH_EARNING: SolarWebSensorDescription(
        key=SENSOR_MONTH_EARNING,
        name="Guadagno mese",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        data_key="month_earning",
    ),
    SENSOR_YEAR_EARNING: SolarWebSensorDescription(
        key=SENSOR_YEAR_EARNING,
        name="Guadagno anno",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        data_key="year_earning",
    ),
    SENSOR_TOTAL_EARNING: SolarWebSensorDescription(
        key=SENSOR_TOTAL_EARNING,
        name="Guadagno totale",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        data_key="total_earning",
    ),
    SENSOR_DIAGNOSTICS: SolarWebSensorDescription(
        key=SENSOR_DIAGNOSTICS,
        name="Diagnostica",
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key=None,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solar Web Public sensors."""

    coordinator: SolarWebPublicCoordinator = hass.data[DOMAIN][entry.entry_id]

    enabled_sensor_keys = entry.options.get(
        CONF_ENABLED_SENSORS,
        DEFAULT_ENABLED_SENSOR_KEYS,
    )

    enabled_sensor_keys = [
        sensor_key
        for sensor_key in enabled_sensor_keys
        if sensor_key in ALL_SENSOR_KEYS
    ]

    if SENSOR_PLANT not in enabled_sensor_keys:
        enabled_sensor_keys.insert(0, SENSOR_PLANT)

    entities = [
        SolarWebPublicSensor(
            coordinator=coordinator,
            entry=entry,
            description=SENSOR_DESCRIPTIONS[sensor_key],
        )
        for sensor_key in enabled_sensor_keys
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

        plant_key = coordinator.client.plant_key

        self._attr_has_entity_name = True
        self._attr_translation_key = description.key
        self._attr_name = None

        if description.key == SENSOR_PLANT:
            self._attr_unique_id = f"{DOMAIN}_{plant_key}_plant"
        else:
            self._attr_unique_id = f"{DOMAIN}_{plant_key}_{description.key}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, plant_key)},
            "name": self._plant_name,
            "manufacturer": "Solar.web",
            "model": "Solar.web shared plant",
        }

    @property
    def native_value(self) -> Any:
        """Return the native value."""

        data = self.coordinator.data or {}

        if self.entity_description.key == SENSOR_PLANT:
            return data.get("status", "unknown")

        if self.entity_description.key == SENSOR_DIAGNOSTICS:
            if data.get("actual_data_available") and data.get("productions_available"):
                return "ok"
            if data.get("payload_length", 0) > 0:
                return "partial"
            return "unknown"

        if self.entity_description.data_key is None:
            return None

        return data.get(self.entity_description.data_key)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement for monetary sensors."""

        if self.entity_description.device_class == SensorDeviceClass.MONETARY:
            return (self.coordinator.data or {}).get("earning_currency") or CURRENCY_EURO

        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return sensor attributes."""

        data = self.coordinator.data or {}

        if self.entity_description.key == SENSOR_DIAGNOSTICS:
            return self._diagnostic_attributes(data)

        if self.entity_description.key == SENSOR_PLANT:
            return self._plant_attributes(data)

        return self._minimal_attributes(data)

    def _minimal_attributes(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return minimal attributes for numeric sensors."""

        return {
            "plant_name": data.get("plant_name"),
            "location": data.get("location"),
            "status": data.get("status"),
            "is_online": data.get("is_online"),
            "pv_system_id": data.get("pv_system_id"),
        }

    def _plant_attributes(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return rich plant attributes."""

        return {
            "configured_name": self._plant_name,
            "plant_name": data.get("plant_name"),
            "location": data.get("location"),
            "page_title": data.get("page_title"),
            "status": data.get("status"),
            "is_online": data.get("is_online"),
            "all_online": data.get("all_online"),
            "pv_system_id": data.get("pv_system_id"),
            "peak_power_wp": data.get("peak_power_wp"),
            "current_power_w": data.get("current_power_w"),
            "production_w": data.get("production_w"),
            "consumption_w": data.get("consumption_w"),
            "grid_power_w": data.get("grid_power_w"),
            "feed_in_w": data.get("feed_in_w"),
            "energy_from_grid_w": data.get("energy_from_grid_w"),
            "battery_power_w": data.get("battery_power_w"),
            "battery_soc": data.get("battery_soc"),
            "battery_mode": data.get("battery_mode"),
            "today_energy_kwh": data.get("today_energy_kwh"),
            "month_energy_kwh": data.get("month_energy_kwh"),
            "year_energy_kwh": data.get("year_energy_kwh"),
            "total_energy_kwh": data.get("total_energy_kwh"),
            "today_energy_label": data.get("today_energy_label"),
            "month_energy_label": data.get("month_energy_label"),
            "year_energy_label": data.get("year_energy_label"),
            "total_energy_label": data.get("total_energy_label"),
            "today_earning": data.get("today_earning"),
            "month_earning": data.get("month_earning"),
            "year_earning": data.get("year_earning"),
            "total_earning": data.get("total_earning"),
            "earning_currency": data.get("earning_currency"),
            "grid_export_energy_today_kwh": data.get("chart_to_grid_kwh"),
            "grid_import_energy_today_kwh": data.get("chart_from_grid_kwh"),
        }

    def _diagnostic_attributes(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return diagnostic attributes."""

        return {
            **self._plant_attributes(data),
            "content_type": data.get("content_type"),
            "payload_length": data.get("payload_length"),
            "has_public_display": data.get("has_public_display"),
            "has_current_power": data.get("has_current_power"),
            "has_pv_system": data.get("has_pv_system"),
            "script_count": data.get("script_count"),
            "api_candidates": data.get("api_candidates"),
            "actual_data_url": data.get("actual_data_url"),
            "actual_data_available": data.get("actual_data_available"),
            "actual_data_error": data.get("actual_data_error"),
            "actual_data_debug_keys": data.get("actual_data_debug_keys"),
            "productions_url": data.get("productions_url"),
            "productions_available": data.get("productions_available"),
            "productions_error": data.get("productions_error"),
            "productions_debug_keys": data.get("productions_debug_keys"),
            "chart_url": data.get("chart_url"),
            "chart_available": data.get("chart_available"),
            "chart_error": data.get("chart_error"),
            "chart_debug_keys": data.get("chart_debug_keys"),
            "chart_has_meter": data.get("chart_has_meter"),
            "chart_to_grid_kwh": data.get("chart_to_grid_kwh"),
            "chart_from_grid_kwh": data.get("chart_from_grid_kwh"),
        }