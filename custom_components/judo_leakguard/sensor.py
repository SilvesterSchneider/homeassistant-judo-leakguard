from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from datetime import timedelta
from .const import DOMAIN
from .api import JudoClient
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, add_entities):
    client: JudoClient = hass.data[DOMAIN][entry.entry_id]

    async def _async_update_data():
        return {
            "total_l": await client.get_total_liters(),
            "fw": await client.get_fw(),
            "datetime": await client.read_datetime(),
            "sleep_h": await client.read_sleep_duration(),
            "learn": await client.read_learn_status(),
            "micro": await client.read_microleak_mode(),
            "limits": await client.read_absence_limits(),
        }

    coordinator = DataUpdateCoordinator(hass, _LOGGER, name="judo_zewa_isafe", update_method=_async_update_data, update_interval=timedelta(seconds=60))
    await coordinator.async_config_entry_first_refresh()

    add_entities([
        TotalWaterSensor(coordinator),
        FirmwareSensor(coordinator),
        DateTimeSensor(coordinator),
        SleepDurationSensor(coordinator),
        LearnRemainingSensor(coordinator),
        MicroLeakModeSensor(coordinator),
        FlowLimitSensor(coordinator),
        VolumeLimitSensor(coordinator),
        DurationLimitSensor(coordinator),
    ])

class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.config_entry.unique_id)}, "manufacturer": "JUDO", "model": "ZEWA i‑SAFE"}

class TotalWaterSensor(_Base):
    _attr_name = "Total water"
    _attr_native_unit_of_measurement = "L"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    def native_value(self):
        return self.coordinator.data.get("total_l")

class FirmwareSensor(_Base):
    _attr_name = "Firmware"
    def native_value(self):
        return self.coordinator.data.get("fw")

class DateTimeSensor(_Base):
    _attr_name = "Device time"
    def native_value(self):
        return self.coordinator.data.get("datetime")

class SleepDurationSensor(_Base):
    _attr_name = "Sleep duration"
    _attr_native_unit_of_measurement = "h"
    def native_value(self):
        return self.coordinator.data.get("sleep_h")

class LearnRemainingSensor(_Base):
    _attr_name = "Learning remaining"
    _attr_native_unit_of_measurement = "L"
    def native_value(self):
        active, remaining = self.coordinator.data.get("learn") or (None, None)
        return remaining

class MicroLeakModeSensor(_Base):
    _attr_name = "Micro‑leak check mode"
    def native_value(self):
        m = self.coordinator.data.get("micro")
        return {0: "off", 1: "notify", 2: "notify_close"}.get(m, None)

class FlowLimitSensor(_Base):
    _attr_name = "Flow limit"
    _attr_native_unit_of_measurement = "L/h"
    def native_value(self):
        limits = self.coordinator.data.get("limits")
        return limits[0] if limits else None

class VolumeLimitSensor(_Base):
    _attr_name = "Volume limit"
    _attr_native_unit_of_measurement = "L"
    def native_value(self):
        limits = self.coordinator.data.get("limits")
        return limits[1] if limits else None

class DurationLimitSensor(_Base):
    _attr_name = "Duration limit"
    _attr_native_unit_of_measurement = "min"
    def native_value(self):
        limits = self.coordinator.data.get("limits")
        return limits[2] if limits else None
