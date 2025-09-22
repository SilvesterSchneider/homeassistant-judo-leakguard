from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    add_entities([LearnActive(coord, entry)])

class _Base(BinarySensorEntity):
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

class LearnActive(_Base):
    _attr_name = "Learning active"
    @property
    def is_on(self):
        return self.coordinator.data.get("learn_active")
