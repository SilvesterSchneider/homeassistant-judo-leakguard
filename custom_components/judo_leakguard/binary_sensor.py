from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .helpers import build_device_info, build_unique_id

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    add_entities([LearnActive(coord, entry)])

class _Base(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        device_data = self.coordinator.data or {}
        self._attr_device_info = build_device_info(device_data)

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_update(self):
        await self.coordinator.async_request_refresh()

class LearnActive(_Base):
    _attr_name = "Learning active"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = build_unique_id(self.coordinator.data, "learn_active")

    @property
    def is_on(self):
        return bool((self.coordinator.data or {}).get("learn_active"))
