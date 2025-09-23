"""Minimal number entity."""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.entity import Entity


class NumberEntity(Entity):
    _attr_native_value: Optional[float] = None
    _attr_native_min_value: Optional[float] = None
    _attr_native_max_value: Optional[float] = None
    _attr_native_step: Optional[float] = None
    _attr_native_unit_of_measurement: Optional[str] = None

    @property
    def native_value(self) -> Optional[float]:
        return getattr(self, "_attr_native_value", None)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return getattr(self, "_attr_native_unit_of_measurement", None)

    async def async_set_native_value(self, value: float) -> None:  # pragma: no cover
        raise NotImplementedError

    @property
    def state(self) -> Any:
        value = self.native_value
        if value is None:
            return STATE_UNKNOWN
        if int(value) == value:
            return str(int(value))
        return str(value)

    def async_write_ha_state(self) -> None:
        if self.hass is None or self.entity_id is None:
            return
        attrs = dict(self.extra_state_attributes or {})
        unit = self.native_unit_of_measurement
        if unit is not None:
            attrs["unit_of_measurement"] = unit
        if self._attr_native_min_value is not None:
            attrs["native_min_value"] = self._attr_native_min_value
        if self._attr_native_max_value is not None:
            attrs["native_max_value"] = self._attr_native_max_value
        if self._attr_native_step is not None:
            attrs["native_step"] = self._attr_native_step
        self.hass.states.async_set(self.entity_id, self.state, attrs)


__all__ = ["NumberEntity"]
