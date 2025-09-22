from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .helpers import build_device_info, build_unique_id
from .api import JudoClient

async def async_setup_entry(hass, entry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client: JudoClient = data["client"]
    coordinator = data["coordinator"]
    add_entities(
        [
            AlarmReset(coordinator, client, entry),
            MicroLeakTest(coordinator, client, entry),
            LearnStart(coordinator, client, entry),
        ]
    )

class _Base(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, client: JudoClient, entry, key: str):
        super().__init__(coordinator)
        self._client = client
        self._entry = entry
        device_data = self.coordinator.data or {}
        self._attr_device_info = build_device_info(device_data)
        self._attr_unique_id = build_unique_id(device_data, key)

class AlarmReset(_Base):
    _attr_name = "Reset alarms"
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "alarm_reset")
    async def async_press(self):
        await self._client.action_no_payload("6300")

class MicroLeakTest(_Base):
    _attr_name = "Start micro-leak test"
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "microleak_test")
    async def async_press(self):
        await self._client.action_no_payload("5C00")

class LearnStart(_Base):
    _attr_name = "Start learning"
    def __init__(self, coordinator, client: JudoClient, entry):
        super().__init__(coordinator, client, entry, "learn_start")
    async def async_press(self):
        await self._client.action_no_payload("5D00")
