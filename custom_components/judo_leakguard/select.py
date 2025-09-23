from __future__ import annotations
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JudoClient
from .const import DOMAIN
from .helpers import build_device_info, build_unique_id

VAC_OPTIONS = ["off", "u1", "u2", "u3"]
MICROLEAK_OPTIONS = ["off", "notify", "notify_close"]

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client: JudoClient = data["client"]
    coordinator = data["coordinator"]
    add_entities([VacationType(coordinator, client, entry), MicroLeakMode(coordinator, client, entry)])

class _Base(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
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
        try:
            idx = int(value)
        except (TypeError, ValueError):
            return None
        if 0 <= idx < len(self.options):
            return self.options[idx]
        return None

    async def async_select_option(self, option: str) -> None:
        option_key = option.lower()
        if option_key not in VAC_OPTIONS:
            raise ValueError(f"Unsupported vacation option: {option}")
        await self._client.write_vacation_type(VAC_OPTIONS.index(option_key))
        await self.coordinator.async_request_refresh()

class MicroLeakMode(_Base):
    _attr_translation_key = "microleak_mode_set"
    _attr_options = MICROLEAK_OPTIONS
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "microleak_mode")
    @property
    def current_option(self):
        value = (self.coordinator.data or {}).get("microleak_mode")
        try:
            idx = int(value)
        except (TypeError, ValueError):
            return None
        if 0 <= idx < len(self.options):
            return self.options[idx]
        return None

    async def async_select_option(self, option: str) -> None:
        option_key = option.lower()
        if option_key not in MICROLEAK_OPTIONS:
            raise ValueError(f"Unsupported microleak option: {option}")
        await self._client.write_microleak_mode(MICROLEAK_OPTIONS.index(option_key))
        await self.coordinator.async_request_refresh()
