"""Sensor-Plattform für JUDO ZEWA i-SAFE."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPE_NAMES, DOMAIN, MICROLEAK_MODES
from .coordinator import JudoData, JudoDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class JudoSensorEntityDescription(SensorEntityDescription):
    value_fn: Any = None  # callable(JudoData) → value


SENSOR_DESCRIPTIONS: tuple[JudoSensorEntityDescription, ...] = (
    # ── Geräteinfos ──────────────────────────────────────────────────────────
    JudoSensorEntityDescription(
        key="device_type",
        name="Gerätetyp",
        icon="mdi:chip",
        value_fn=lambda d: DEVICE_TYPE_NAMES.get(d.info.device_type, f"Unbekannt (0x{d.info.device_type:02X})"),
    ),
    JudoSensorEntityDescription(
        key="device_serial",
        name="Seriennummer",
        icon="mdi:barcode",
        value_fn=lambda d: str(d.info.serial_number),
    ),
    JudoSensorEntityDescription(
        key="device_firmware",
        name="Firmware-Version",
        icon="mdi:chip",
        value_fn=lambda d: d.info.fw_version,
    ),
    JudoSensorEntityDescription(
        key="installation_date",
        name="Inbetriebnahmedatum",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.info.commission_date,
    ),
    # ── Betriebsdaten ─────────────────────────────────────────────────────────
    JudoSensorEntityDescription(
        key="total_water_liters",
        name="Gesamtwasser",
        icon="mdi:water",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.status.total_water_liters,
    ),
    JudoSensorEntityDescription(
        key="total_water_m3",
        name="Gesamtwasser (m³)",
        icon="mdi:water",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value_fn=lambda d: round(d.status.total_water_liters / 1000, 3),
    ),
    JudoSensorEntityDescription(
        key="sleep_duration",
        name="Schlafdauer",
        icon="mdi:sleep",
        native_unit_of_measurement="h",
        value_fn=lambda d: d.status.sleep_hours,
    ),
    JudoSensorEntityDescription(
        key="learning_remaining_water",
        name="Lernmodus Restwasser",
        icon="mdi:water-sync",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        value_fn=lambda d: d.status.learning_remaining_water,
    ),
    # ── Abwesenheitslimits ────────────────────────────────────────────────────
    JudoSensorEntityDescription(
        key="absence_flow_limit",
        name="Abwesenheit – Durchfluss-Limit",
        icon="mdi:water-pump",
        native_unit_of_measurement="L/h",
        value_fn=lambda d: d.status.absence_flow_limit,
    ),
    JudoSensorEntityDescription(
        key="absence_volume_limit",
        name="Abwesenheit – Volumen-Limit",
        icon="mdi:water-boiler",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        value_fn=lambda d: d.status.absence_volume_limit,
    ),
    JudoSensorEntityDescription(
        key="absence_duration_limit",
        name="Abwesenheit – Dauer-Limit",
        icon="mdi:timer",
        native_unit_of_measurement="min",
        value_fn=lambda d: d.status.absence_duration_limit,
    ),
    # ── Datum/Zeit ────────────────────────────────────────────────────────────
    JudoSensorEntityDescription(
        key="device_datetime",
        name="Gerätedatum/-zeit",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.status.device_datetime,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: JudoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JudoSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class JudoSensor(CoordinatorEntity[JudoDataUpdateCoordinator], SensorEntity):
    """Repräsentiert einen Sensor der JUDO ZEWA i-SAFE Integration."""

    entity_description: JudoSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JudoDataUpdateCoordinator,
        description: JudoSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JUDO ZEWA i-SAFE",
            manufacturer="JUDO Wasseraufbereitung GmbH",
            model="ZEWA i-SAFE",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
