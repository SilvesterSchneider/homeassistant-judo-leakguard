"""Switch platform for ZEWA commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import JudoBaseEntity


@dataclass
class JudoSwitchEntityDescription(SwitchEntityDescription):
    """Switch command description."""

    turn_on_fn: Callable[[object], Awaitable[None]]
    turn_off_fn: Callable[[object], Awaitable[None]]
    state_attr: str


SWITCHES: tuple[JudoSwitchEntityDescription, ...] = (
    JudoSwitchEntityDescription(
        key="valve_open",
        translation_key="valve_open",
        turn_on_fn=lambda client: client.open_valve(),
        turn_off_fn=lambda client: client.close_valve(),
        state_attr="valve_open",
    ),
    JudoSwitchEntityDescription(
        key="sleep_mode",
        translation_key="sleep_mode",
        turn_on_fn=lambda client: client.sleep_start(),
        turn_off_fn=lambda client: client.sleep_end(),
        state_attr="sleep_mode",
    ),
    JudoSwitchEntityDescription(
        key="vacation_mode",
        translation_key="vacation_mode",
        turn_on_fn=lambda client: client.vacation_start(),
        turn_off_fn=lambda client: client.vacation_end(),
        state_attr="vacation_mode",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client = data["client"]
    entities = [JudoSwitchEntity(coordinator, client, description) for description in SWITCHES]
    async_add_entities(entities)


class JudoSwitchEntity(JudoBaseEntity, SwitchEntity):
    """Representation of an optimistic switch."""

    _attr_assumed_state = True

    entity_description: JudoSwitchEntityDescription

    def __init__(self, coordinator, client, description: JudoSwitchEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._client = client
        self._attr_unique_id = f"{coordinator.data.serial}_{description.key}"

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.coordinator.runtime, self.entity_description.state_attr))

    async def async_turn_on(self, **kwargs):
        await self.entity_description.turn_on_fn(self._client)
        setattr(self.coordinator.runtime, self.entity_description.state_attr, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.entity_description.turn_off_fn(self._client)
        setattr(self.coordinator.runtime, self.entity_description.state_attr, False)
        self.async_write_ha_state()
