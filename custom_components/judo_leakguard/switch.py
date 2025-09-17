from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]
    device_type = hass.data[DOMAIN][entry.entry_id]["device_type"]

    async_add_entities([JudoValveSwitch(coordinator, client, device_type)])

class JudoValveSwitch(SwitchEntity):
    _attr_name = "Leakguard Valve"
    _attr_unique_id = None

    def __init__(self, coordinator, client, device_type: int):
        self.coordinator = coordinator
        self.client = client
        self.device_type = device_type
        self._is_on = True  # assume open

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_type)},
            manufacturer="JUDO",
            model=f"Type 0x{self.device_type:02X}",
            name="Judo Leakguard",
        )

    async def async_turn_on(self, **kwargs):
        await self.client.valve_open(self.device_type)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.client.valve_close(self.device_type)
        self._is_on = False
        self.async_write_ha_state()

    async def async_update(self):
        await self.coordinator.async_request_refresh()