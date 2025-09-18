from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from .api import JudoClient
from .const import DOMAIN

async def async_setup_entry(hass, entry, add_entities):
    client: JudoClient = hass.data[DOMAIN][entry.entry_id]
    add_entities([
        ValveSwitch(client, entry),
        SleepModeSwitch(client, entry),
        VacationSwitch(client, entry),
    ])

class _ActionSwitch(SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, client: JudoClient, entry):
        self._client = client
        self._entry = entry
        self._state = False

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._entry.unique_id)}, "manufacturer": "JUDO", "model": "ZEWA i‑SAFE"}

class ValveSwitch(_ActionSwitch):
    _attr_name = "Valve open"
    async def async_turn_on(self):
        await self._client.action_no_payload("5200")
        self._state = True
        self.async_write_ha_state()
    async def async_turn_off(self):
        await self._client.action_no_payload("5100")
        self._state = False
        self.async_write_ha_state()
    @property
    def is_on(self):
        return self._state

class SleepModeSwitch(_ActionSwitch):
    _attr_name = "Sleep mode"
    async def async_turn_on(self):
        await self._client.action_no_payload("5400")
        self._state = True
        self.async_write_ha_state()
    async def async_turn_off(self):
        await self._client.action_no_payload("5500")
        self._state = False
        self.async_write_ha_state()
    @property
    def is_on(self):
        return self._state

class VacationSwitch(_ActionSwitch):
    _attr_name = "Vacation mode"
    async def async_turn_on(self):
        await self._client.action_no_payload("5700")
        self._state = True
        self.async_write_ha_state()
    async def async_turn_off(self):
        await self._client.action_no_payload("5800")
        self._state = False
        self.async_write_ha_state()
    @property
    def is_on(self):
        return self._state