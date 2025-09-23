"""Minimal sensor entity implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.entity import Entity, EntityCategory


class SensorDeviceClass(str, Enum):
    WATER = "water"
    TIMESTAMP = "timestamp"


class SensorStateClass(str, Enum):
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"


@dataclass(frozen=True)
class SensorEntityDescription:
    key: str
    translation_key: Optional[str] = None
    native_unit_of_measurement: Optional[str] = None
    device_class: Optional[SensorDeviceClass] = None
    state_class: Optional[SensorStateClass] = None
    entity_category: Optional[EntityCategory] = None
    paths: tuple[str, ...] = ()


class SensorEntity(Entity):
    _attr_native_unit_of_measurement: Optional[str] = None
    _attr_device_class: Optional[SensorDeviceClass] = None
    _attr_state_class: Optional[SensorStateClass] = None

    @property
    def native_value(self) -> Any:
        return getattr(self, "_attr_native_value", None)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        if hasattr(self, "entity_description"):
            return getattr(self.entity_description, "native_unit_of_measurement", None)
        return getattr(self, "_attr_native_unit_of_measurement", None)

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        if hasattr(self, "entity_description"):
            return getattr(self.entity_description, "device_class", None)
        return getattr(self, "_attr_device_class", None)

    @property
    def state_class(self) -> Optional[SensorStateClass]:
        if hasattr(self, "entity_description"):
            return getattr(self.entity_description, "state_class", None)
        return getattr(self, "_attr_state_class", None)

    @property
    def state(self) -> Any:
        value = self.native_value
        if value is None:
            return STATE_UNKNOWN
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def async_write_ha_state(self) -> None:
        if self.hass is None or self.entity_id is None:
            return
        attrs = dict(self.extra_state_attributes or {})
        unit = self.native_unit_of_measurement
        if unit is not None:
            attrs["unit_of_measurement"] = unit
        device_class = self.device_class
        if device_class is not None:
            attrs["device_class"] = device_class
        state_class = self.state_class
        if state_class is not None:
            attrs["state_class"] = state_class
        self.hass.states.async_set(self.entity_id, self.state, attrs)


__all__ = [
    "SensorDeviceClass",
    "SensorEntity",
    "SensorEntityDescription",
    "SensorStateClass",
]
