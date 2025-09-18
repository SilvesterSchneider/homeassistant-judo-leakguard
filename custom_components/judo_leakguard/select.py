from __future__ import annotations
from homeassistant.components.select import SelectEntity
from .api import JudoClient
from .const import DOMAIN

VAC_OPTIONS = ["off", "U1", "U2", "U3"]

async def async_setup_entry(hass, entry, add_entities):
    client: JudoClient = hass.data[DOMAIN][entry.entry_id]
    add_entities([VacationSelect(client, entry)])

class VacationSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Vacation type"
    _attr_options = VAC_OPTIONS
    def __init__(self, client: JudoClient, entry):
        self._client = client
        self._entry = entry
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._entry.unique_id)}, "manufacturer": "JUDO", "model": "ZEWA i‑SAFE"}
    async def async_select_option(self, option: str) -> None:
        idx = VAC_OPTIONS.index(option)
        await self._client.write_vacation_type(idx)