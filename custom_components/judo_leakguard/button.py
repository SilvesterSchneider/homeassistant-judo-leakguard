from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from .const import DOMAIN
from .api import JudoClient

async def async_setup_entry(hass, entry, add_entities):
    client: JudoClient = hass.data[DOMAIN][entry.entry_id]
    add_entities([
        AlarmResetButton(client, entry),
        MicroLeakTestButton(client, entry),
        LearnStartButton(client, entry),
    ])

class _ActionButton(ButtonEntity):
    _attr_has_entity_name = True
    def __init__(self, client: JudoClient, entry):
        self._client = client
        self._entry = entry
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._entry.unique_id)}, "manufacturer": "JUDO", "model": "ZEWA i‑SAFE"}

class AlarmResetButton(_ActionButton):
    _attr_name = "Reset alarms"
    async def async_press(self):
        await self._client.action_no_payload("6300")

class MicroLeakTestButton(_ActionButton):
    _attr_name = "Start micro‑leak test"
    async def async_press(self):
        await self._client.action_no_payload("5C00")

class LearnStartButton(_ActionButton):
    _attr_name = "Start learning"
    async def async_press(self):
        await self._client.action_no_payload("5D00")
