from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JudoClient
from .const import DOMAIN
from .helpers import build_device_info, build_unique_id

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client: JudoClient = data["client"]
    coordinator = data["coordinator"]
    add_entities(
        [
            ValveSwitch(coordinator, client, entry),
            SleepSwitch(coordinator, client, entry),
            VacationSwitch(coordinator, client, entry),
        ]
    )

class _BaseSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, client: JudoClient, entry, key: str, state_key: str | None = None):
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        self._state_key = state_key
        device_data = self.coordinator.data or {}
        self._attr_device_info = build_device_info(device_data)
        self._attr_unique_id = build_unique_id(device_data, key)
        if state_key:
            self._state = bool((device_data or {}).get(state_key, False))
        else:
            self._state = False

    @property
    def is_on(self):
        if self._state_key:
            value = (self.coordinator.data or {}).get(self._state_key)
            if value is not None:
                return bool(value)
        return self._state

class ValveSwitch(_BaseSwitch):
    _attr_name = "Valve open"
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "valve")
    async def async_turn_on(self, **kwargs):
        await self._client.action_no_payload("5200")
        self._state = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
    async def async_turn_off(self, **kwargs):
        await self._client.action_no_payload("5100")
        self._state = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

class SleepSwitch(_BaseSwitch):
    _attr_name = "Sleep mode"
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "sleep_mode", state_key="sleep_active")
    async def async_turn_on(self, **kwargs):
        await self._client.action_no_payload("5400")
        self._state = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
    async def async_turn_off(self, **kwargs):
        await self._client.action_no_payload("5500")
        self._state = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

class VacationSwitch(_BaseSwitch):
    _attr_name = "Vacation mode"
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "vacation_mode", state_key="vacation_active")
    async def async_turn_on(self, **kwargs):
        await self._client.action_no_payload("5700")
        self._state = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
    async def async_turn_off(self, **kwargs):
        await self._client.action_no_payload("5800")
        self._state = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
