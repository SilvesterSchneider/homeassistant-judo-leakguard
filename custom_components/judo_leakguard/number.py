from __future__ import annotations
from homeassistant.components.number import NumberEntity
from .const import DOMAIN
from .api import JudoClient

async def async_setup_entry(hass, entry, add_entities):
    client: JudoClient = hass.data[DOMAIN][entry.entry_id]
    add_entities([
        SleepHoursNumber(client, entry),
        FlowLimitNumber(client, entry),
        VolumeLimitNumber(client, entry),
        DurationLimitNumber(client, entry),
    ])

class _BaseNumber(NumberEntity):
    _attr_has_entity_name = True
    def __init__(self, client: JudoClient, entry):
        self._client = client
        self._entry = entry
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._entry.unique_id)}, "manufacturer": "JUDO", "model": "ZEWA i‑SAFE"}

class SleepHoursNumber(_BaseNumber):
    _attr_name = "Sleep hours"
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1
    async def async_set_native_value(self, value: float) -> None:
        await self._client.write_sleep_duration(int(value))

class FlowLimitNumber(_BaseNumber):
    _attr_name = "Flow limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 10
    async def async_set_native_value(self, value: float) -> None:
        flow, vol, dur = await self._client.read_absence_limits()
        await self._client.write_leak_settings(0, int(value), vol, dur)

class VolumeLimitNumber(_BaseNumber):
    _attr_name = "Volume limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    async def async_set_native_value(self, value: float) -> None:
        flow, vol, dur = await self._client.read_absence_limits()
        await self._client.write_leak_settings(0, flow, int(value), dur)

class DurationLimitNumber(_BaseNumber):
    _attr_name = "Duration limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    async def async_set_native_value(self, value: float) -> None:
        flow, vol, dur = await self._client.read_absence_limits()
        await self._client.write_leak_settings(0, flow, vol, int(value))