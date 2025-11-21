"""Sensor platform for Judo ZEWA i-SAFE."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoCoordinatorData
from .entity import JudoBaseEntity


@dataclass
class JudoSensorEntityDescription(SensorEntityDescription):
    """Describes a ZEWA sensor entity."""

    value_fn: Callable[[JudoCoordinatorData], object]


SENSORS: tuple[JudoSensorEntityDescription, ...] = (
    JudoSensorEntityDescription(
        key="total_water_l",
        translation_key="total_water_liters",
        native_unit_of_measurement="L",
        value_fn=lambda data: data.total_water_l,
    ),
    JudoSensorEntityDescription(
        key="total_water_m3",
        translation_key="total_water_cubic_m",
        native_unit_of_measurement="m³",
        value_fn=lambda data: round(data.total_water_l / 1000, 3),
    ),
    JudoSensorEntityDescription(
        key="sleep_duration",
        translation_key="sleep_duration",
        native_unit_of_measurement="h",
        value_fn=lambda data: data.sleep_hours,
    ),
    JudoSensorEntityDescription(
        key="absence_flow_limit",
        translation_key="absence_flow_limit",
        native_unit_of_measurement="L/h",
        value_fn=lambda data: data.absence_limits.max_flow_l_h,
    ),
    JudoSensorEntityDescription(
        key="absence_volume_limit",
        translation_key="absence_volume_limit",
        native_unit_of_measurement="L",
        value_fn=lambda data: data.absence_limits.max_volume_l,
    ),
    JudoSensorEntityDescription(
        key="absence_duration_limit",
        translation_key="absence_duration_limit",
        native_unit_of_measurement="min",
        value_fn=lambda data: data.absence_limits.max_duration_min,
    ),
    JudoSensorEntityDescription(
        key="learning_remaining_water",
        translation_key="learning_remaining_water",
        native_unit_of_measurement="L",
        value_fn=lambda data: data.learning_remaining_l,
    ),
    JudoSensorEntityDescription(
        key="device_clock",
        translation_key="device_clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.clock.as_datetime(),
    ),
    JudoSensorEntityDescription(
        key="installation_date",
        translation_key="installation_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.commission_date,
    ),
    JudoSensorEntityDescription(
        key="device_serial",
        translation_key="device_serial",
        value_fn=lambda data: data.serial,
    ),
    JudoSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        value_fn=lambda data: data.firmware,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors based on a config entry."""

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [JudoSensorEntity(coordinator, description) for description in SENSORS]
    async_add_entities(entities)


class JudoSensorEntity(JudoBaseEntity, SensorEntity):
    """Representation of a ZEWA sensor."""

    entity_description: JudoSensorEntityDescription

    def __init__(self, coordinator, description: JudoSensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
