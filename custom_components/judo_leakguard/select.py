from __future__ import annotations
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JudoClient
from .const import DOMAIN
from .helpers import build_device_info, build_unique_id

VAC_OPTIONS = ["off","U1","U2","U3"]

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client: JudoClient = data["client"]
    coordinator = data["coordinator"]
    add_entities([VacationType(coordinator, client, entry), MicroLeakMode(coordinator, client, entry)])

class _Base(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, client: JudoClient, entry, key: str):
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        device_data = self.coordinator.data or {}
        self._attr_device_info = build_device_info(device_data)
        self._attr_unique_id = build_unique_id(device_data, key)

class VacationType(_Base):
    _attr_translation_key = "vacation_type"
    _attr_options = VAC_OPTIONS
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "vacation_type")
    @property
    def current_option(self):
        value = (self.coordinator.data or {}).get("vacation_type")
        if value is None or not (0 <= int(value) < len(self.options)):
            return None
        return self.options[int(value)]
    async def async_select_option(self, option: str) -> None:
        await self._client.write_vacation_type(VAC_OPTIONS.index(option))
        await self.coordinator.async_request_refresh()

class MicroLeakMode(_Base):
    _attr_translation_key = "microleak_mode_set"
    _attr_options = ["off","notify","notify_close"]
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "microleak_mode")
    @property
    def current_option(self):
        value = (self.coordinator.data or {}).get("microleak_mode")
        mapping = {0: "off", 1: "notify", 2: "notify_close"}
        return mapping.get(int(value)) if value is not None else None
    async def async_select_option(self, option: str) -> None:
        mapping = {"off":0, "notify":1, "notify_close":2}
        await self._client.write_microleak_mode(mapping[option])
        await self.coordinator.async_request_refresh()
