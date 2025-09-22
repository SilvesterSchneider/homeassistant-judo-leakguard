from __future__ import annotations
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JudoClient
from .const import DOMAIN
from .helpers import build_device_info, build_unique_id

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client: JudoClient = data["client"]
    coordinator = data["coordinator"]
    add_entities(
        [
            SleepHours(coordinator, client, entry),
            FlowLimit(coordinator, client, entry),
            VolumeLimit(coordinator, client, entry),
            DurationLimit(coordinator, client, entry),
        ]
    )

class _Base(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, client: JudoClient, entry, key: str):
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        device_data = self.coordinator.data or {}
        self._attr_device_info = build_device_info(device_data)
        self._attr_unique_id = build_unique_id(device_data, key)

class SleepHours(_Base):
    _attr_translation_key = "sleep_hours"
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "sleep_hours")
    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("sleep_hours")
    async def async_set_native_value(self, value: float) -> None:
        await self._client.write_sleep_duration(int(value))
        await self.coordinator.async_request_refresh()

class FlowLimit(_Base):
    _attr_translation_key = "absence_flow_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 10
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "absence_flow")
    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("absence_flow_l_h")
    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data or {}
        volume = int(data.get("absence_volume_l", 0) or 0)
        duration = int(data.get("absence_duration_min", 0) or 0)
        await self._client.write_absence_limits(int(value), volume, duration)
        await self.coordinator.async_request_refresh()

class VolumeLimit(_Base):
    _attr_translation_key = "absence_volume_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "absence_volume")
    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("absence_volume_l")
    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data or {}
        flow = int(data.get("absence_flow_l_h", 0) or 0)
        duration = int(data.get("absence_duration_min", 0) or 0)
        await self._client.write_absence_limits(flow, int(value), duration)
        await self.coordinator.async_request_refresh()

class DurationLimit(_Base):
    _attr_translation_key = "absence_duration_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "absence_duration")
    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("absence_duration_min")
    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data or {}
        flow = int(data.get("absence_flow_l_h", 0) or 0)
        volume = int(data.get("absence_volume_l", 0) or 0)
        await self._client.write_absence_limits(flow, volume, int(value))
        await self.coordinator.async_request_refresh()
