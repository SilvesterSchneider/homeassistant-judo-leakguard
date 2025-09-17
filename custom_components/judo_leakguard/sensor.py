from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    dt = hass.data[DOMAIN][entry.entry_id]["device_type"]

    async_add_entities([
        TotalWaterSensor(c, dt),
        SoftWaterSensor(c, dt),
        ServicePhoneSensor(c, dt),
    ])

class _Base(JudoBase := SensorEntity):
    def __init__(self, coordinator, device_type):
        self.coordinator = coordinator
        self.device_type = device_type

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_type)},
            manufacturer="JUDO",
            model=f"Type 0x{self.device_type:02X}",
            name="Judo Leakguard",
        )

class TotalWaterSensor(_Base):
    _attr_name = "Total water"
    _attr_native_unit_of_measurement = "L"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:water"
    _attr_unique_id = "judo_total_water"

    @property
    def native_value(self):
        return self.coordinator.data.get("total_liters")

class SoftWaterSensor(_Base):
    _attr_name = "Soft water"
    _attr_native_unit_of_measurement = "L"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:water-check"
    _attr_unique_id = "judo_soft_water"

    @property
    def native_value(self):
        return self.coordinator.data.get("soft_liters")

class ServicePhoneSensor(_Base):
    _attr_name = "Service phone"
    _attr_icon = "mdi:phone"
    _attr_unique_id = "judo_service_phone"

    @property
    def native_value(self):
        return self.coordinator.data.get("service_phone")