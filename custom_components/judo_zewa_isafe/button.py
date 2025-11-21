"""Button entities for momentary commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import JudoBaseEntity


@dataclass
class JudoButtonDescription(ButtonEntityDescription):
    action: Callable[[object], Awaitable[None]]


BUTTONS: tuple[JudoButtonDescription, ...] = (
    JudoButtonDescription(key="ack_alarm", translation_key="reset_alarms", action=lambda client: client.ack_alarm()),
    JudoButtonDescription(
        key="start_microleak_test",
        translation_key="start_microleak_test",
        action=lambda client: client.micro_leak_test(),
    ),
    JudoButtonDescription(
        key="start_learning",
        translation_key="start_learning",
        action=lambda client: client.learn_mode_start(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client = data["client"]
    async_add_entities([JudoButtonEntity(coordinator, client, description) for description in BUTTONS])


class JudoButtonEntity(JudoBaseEntity, ButtonEntity):
    """Representation of a command button."""

    entity_description: JudoButtonDescription

    def __init__(self, coordinator, client, description: JudoButtonDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._client = client
        self._attr_unique_id = f"{coordinator.data.serial}_{description.key}"

    async def async_press(self) -> None:
        await self.entity_description.action(self._client)
