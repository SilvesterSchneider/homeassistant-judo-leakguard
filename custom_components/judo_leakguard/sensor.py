from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfPressure,
    UnitOfVolume,
    UnitOfTemperature,
    UnitOfTime,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "judo_leakguard"


def _get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    try:
        cur: Any = data
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur
    except Exception:
        return default


def _first_present(data: dict[str, Any], candidates: Iterable[str]) -> Any:
    for path in candidates:
        val = _get_nested(data, path, default=None)
        if val is not None:
            return val
    return None


@dataclass(frozen=True)
class JudoSensorEntityDescription(SensorEntityDescription):
    paths: tuple[str, ...] = tuple()
    state_class: Optional[SensorStateClass] = None


SENSOR_DESCRIPTIONS: tuple[JudoSensorEntityDescription, ...] = (
    JudoSensorEntityDescription(
        key="pressure_bar",
        name="Pressure",
        paths=("pressure_bar", "pressure", "sensors.pressure_bar", "live.pressure_bar"),
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="water_flow_l_min",
        name="Water Flow",
        paths=("water_flow_l_min", "flow_l_min", "sensors.flow", "live.flow"),
        native_unit_of_measurement="L/min",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="total_water_m3",
        name="Total Water",
        paths=("total_water_m3", "total_m3", "counters.total_water_m3"),
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    JudoSensorEntityDescription(
        key="temperature_c",
        name="Device Temperature",
        paths=("temperature_c", "temp_c", "sensors.temperature_c"),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="battery_percent",
        name="Battery",
        paths=("battery_percent", "battery", "status.battery_percent"),
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JudoSensorEntityDescription(
        key="last_update_seconds",
        name="Last Update Age",
        paths=("last_update_seconds", "meta.age_seconds"),
        native_unit_of_measurement=UnitOfTime.SECONDS,
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

        serial = _first_present(self.coordinator.data or {}, ("serial", "device.serial", "meta.serial")) or "unknown"
        model = _first_present(self.coordinator.data or {}, ("model", "device.model", "meta.model")) or "ZEWA i-SAFE"
        swver = _first_present(self.coordinator.data or {}, ("firmware", "sw_version", "meta.firmware")) or None
        manufacturer = _first_present(self.coordinator.data or {}, ("manufacturer", "brand", "meta.manufacturer")) or "JUDO"

        self._attr_unique_id = f"{serial}_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=manufacturer,
            model=model,
            sw_version=str(swver) if swver is not None else None,
            name="Judo Leakguard",
            configuration_url=None,
        )

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        return True

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        value = _first_present(data, self.entity_description.paths or (self.entity_description.key,))
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
