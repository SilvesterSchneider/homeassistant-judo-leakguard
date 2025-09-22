from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from .const import DOMAIN

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    add_entities([
        TotalWater(coord, entry),
        Firmware(coord, entry),
        DeviceTime(coord, entry),
        SleepDuration(coord, entry),
        LearnRemaining(coord, entry),
        MicroLeakMode(coord, entry),
        FlowLimit(coord, entry),
        VolumeLimit(coord, entry),
        DurationLimit(coord, entry),
    ])

class _Base(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
    @property
    def available(self):
        return self.coordinator.last_update_success
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.unique_id)},
            "manufacturer": "JUDO",
            "model": "ZEWA i-SAFE",
        }
    async def async_update(self):
        await self.coordinator.async_request_refresh()

class TotalWater(_Base):
    _attr_name = "Total water"
    _attr_native_unit_of_measurement = "L"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    def native_value(self):
        return self.coordinator.data.get("total_l")

class Firmware(_Base):
    _attr_name = "Firmware"
    def native_value(self):
        return self.coordinator.data.get("fw")

class DeviceTime(_Base):
    _attr_name = "Device time"
    def native_value(self):
        return self.coordinator.data.get("datetime")

class SleepDuration(_Base):
    _attr_name = "Sleep duration"
    _attr_native_unit_of_measurement = "h"
    def native_value(self):
        return self.coordinator.data.get("sleep_h")

class LearnRemaining(_Base):
    _attr_name = "Learning remaining"
    _attr_native_unit_of_measurement = "L"
    def native_value(self):
        return self.coordinator.data.get("learn_remaining")

class MicroLeakMode(_Base):
    _attr_name = "Micro-leak mode"
    def native_value(self):
        m = self.coordinator.data.get("micro")
        return {0: "off", 1: "notify", 2: "notify_close"}.get(m, m)

class FlowLimit(_Base):
    _attr_name = "Absence flow limit"
    _attr_native_unit_of_measurement = "L/h"
    def native_value(self):
        limits = self.coordinator.data.get("limits")
        return limits[0] if limits else None

class VolumeLimit(_Base):
    _attr_name = "Absence volume limit"
    _attr_native_unit_of_measurement = "L"
    def native_value(self):
        limits = self.coordinator.data.get("limits")
        return limits[1] if limits else None

class DurationLimit(_Base):
    _attr_name = "Absence duration limit"
    _attr_native_unit_of_measurement = "min"
    def native_value(self):
        limits = self.coordinator.data.get("limits")
        return limits[2] if limits else None
