from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers import build_device_info, build_unique_id, first_present

_LOGGER = logging.getLogger(__name__)

DOMAIN = "judo_leakguard"

UNIT_LITERS_PER_HOUR: str = cast(
    str, getattr(UnitOfVolumeFlowRate, "LITERS_PER_HOUR", "L/h")
)


@dataclass(frozen=True)
class JudoSensorEntityDescription(SensorEntityDescription):
    paths: tuple[str, ...] = tuple()


SENSOR_DESCRIPTIONS: tuple[JudoSensorEntityDescription, ...] = (
    JudoSensorEntityDescription(
        key="pressure_bar",
        translation_key="pressure",
        paths=("pressure_bar", "pressure", "sensors.pressure_bar", "live.pressure_bar"),
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="water_flow_l_min",
        translation_key="water_flow",
        paths=("water_flow_l_min", "flow_l_min", "sensors.flow", "live.flow"),
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="total_water_m3",
        translation_key="total_water",
        paths=("total_water_m3", "total_m3", "counters.total_water_m3"),
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    JudoSensorEntityDescription(
        key="total_water_l",
        translation_key="total_water_liters",
        paths=("total_water_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    JudoSensorEntityDescription(
        key="temperature_c",
        translation_key="device_temperature",
        paths=("temperature_c", "temp_c", "sensors.temperature_c"),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="battery_percent",
        translation_key="battery",
        paths=("battery_percent", "battery", "status.battery_percent"),
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="last_update_seconds",
        translation_key="last_update_age",
        paths=("last_update_seconds", "meta.age_seconds"),
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="sleep_hours",
        translation_key="sleep_duration",
        paths=("sleep_hours",),
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="absence_flow_l_h",
        translation_key="absence_flow_limit",
        paths=("absence_flow_l_h",),
        native_unit_of_measurement=UNIT_LITERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="absence_volume_l",
        translation_key="absence_volume_limit",
        paths=("absence_volume_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="absence_duration_min",
        translation_key="absence_duration_limit",
        paths=("absence_duration_min",),
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="learn_remaining_l",
        translation_key="learning_remaining_water",
        paths=("learn_remaining_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="installation_datetime",
        translation_key="installation_date",
        paths=("installation_datetime",),
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="device_time",
        translation_key="device_time",
        paths=("device_time_datetime",),
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="device_type",
        translation_key="device_type",
        paths=("device_type_label", "device_type_hex", "device_type_code"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="device_serial",
        translation_key="device_serial",
        paths=("serial", "device.serial", "meta.serial"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="device_firmware",
        translation_key="device_firmware",
        paths=("firmware", "sw_version", "meta.firmware"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JudoSensorEntityDescription(
        key="daily_usage_l",
        translation_key="daily_usage",
        paths=("daily_usage_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="weekly_usage_l",
        translation_key="weekly_usage",
        paths=("weekly_usage_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="monthly_usage_l",
        translation_key="monthly_usage",
        paths=("monthly_usage_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="yearly_usage_l",
        translation_key="yearly_usage",
        paths=("yearly_usage_l",),
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


class JudoSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        description: JudoSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry

        device_data = self.coordinator.data or {}

        self._attr_unique_id = build_unique_id(device_data, description.key)
        self._attr_device_info = build_device_info(device_data)

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        return True

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        value = first_present(data, self.entity_description.paths or (self.entity_description.key,))
        return value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_bucket = hass.data.get(DOMAIN, {})
    entry_bucket = domain_bucket.get(entry.entry_id, {})
    coordinator = entry_bucket.get("coordinator") or entry_bucket

    if not coordinator:
        _LOGGER.error(
            "Coordinator not found in hass.data[%s][%s]. "
            "Please ensure you store it as hass.data[DOMAIN][entry.entry_id]['coordinator'] during setup.",
            DOMAIN,
            entry.entry_id,
        )
        return

    entities: list[JudoSensor] = []
    for desc in SENSOR_DESCRIPTIONS:
        entities.append(JudoSensor(coordinator, entry, desc))

    async_add_entities(entities, update_before_add=True)

    _LOGGER.debug("Added %d Judo Leakguard sensors for entry %s", len(entities), entry.entry_id)
