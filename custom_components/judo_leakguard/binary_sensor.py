from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from .sensor import _Base

async def async_setup_entry(hass, entry, add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id + "_sensor_coordinator"] if False else None  # placeholder if reusing sensors' coordinator

    # For simplicity, we reuse data fetched in sensors via device class mixers; or create minimal on‑demand reads
    client = hass.data[DOMAIN][entry.entry_id]

    add_entities([
        LearnActiveBinary(client, entry),
    ])

class LearnActiveBinary(_Base, BinarySensorEntity):
    _attr_name = "Learning active"
    @property
    def is_on(self):
        # lightweight direct poll; ensure we don't spam -> could be optimized by sharing coordinator
        return self.coordinator.data.get("learn")[0] if self.coordinator and self.coordinator.data else None
