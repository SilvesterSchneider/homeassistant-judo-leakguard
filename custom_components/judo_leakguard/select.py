from __future__ import annotations
from homeassistant.components.select import SelectEntity
from .api import JudoClient
from .const import DOMAIN

VAC_OPTIONS = ["off","U1","U2","U3"]

async def async_setup_entry(hass, entry, add_entities):
    client: JudoClient = hass.data[DOMAIN][entry.entry_id]["client"]
    add_entities([VacationType(client, entry), MicroLeakMode(client, entry)])

class _Base(SelectEntity):
    _attr_has_entity_name = True
    def __init__(self, client: JudoClient, entry):
        self._client = client
        self._entry = entry
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.unique_id)},
            "manufacturer": "JUDO",
            "model": "ZEWA i-SAFE",
        }

class VacationType(_Base):
    _attr_name = "Vacation type"
    _attr_options = VAC_OPTIONS
    async def async_select_option(self, option: str) -> None:
        await self._client.write_vacation_type(VAC_OPTIONS.index(option))

class MicroLeakMode(_Base):
    _attr_name = "Micro-leak mode (set)"
    _attr_options = ["off","notify","notify_close"]
    async def async_select_option(self, option: str) -> None:
        mapping = {"off":0, "notify":1, "notify_close":2}
        await self._client.write_microleak_mode(mapping[option])
