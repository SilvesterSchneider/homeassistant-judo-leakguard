"""Select entities for ZEWA modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import JudoBaseEntity


@dataclass
class JudoSelectDescription(SelectEntityDescription):
    set_option_fn: Callable[[object, str, "JudoSelectEntity"], Awaitable[None]]
    options: list[str]


async def _set_vacation(client, option: str, entity: "JudoSelectEntity") -> None:
    mapping = {"off": 0, "u1": 1, "u2": 2, "u3": 3}
    await client.set_vacation_type(mapping[option])
    await entity.coordinator.async_request_refresh()


async def _set_micro_mode(client, option: str, entity: "JudoSelectEntity") -> None:
    mapping = {"off": 0, "notify": 1, "notify_close": 2}
    await client.set_micro_leak_mode(mapping[option])
    await entity.coordinator.async_request_refresh()


SELECTS: tuple[JudoSelectDescription, ...] = (
    JudoSelectDescription(
        key="vacation_type",
        translation_key="vacation_type",
        options=["off", "u1", "u2", "u3"],
        set_option_fn=_set_vacation,
    ),
    JudoSelectDescription(
        key="micro_leak_mode",
        translation_key="micro_leak_mode",
        options=["off", "notify", "notify_close"],
        set_option_fn=_set_micro_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client = data["client"]
    async_add_entities([JudoSelectEntity(coordinator, client, description) for description in SELECTS])


class JudoSelectEntity(JudoBaseEntity, SelectEntity):
    """Representation of a select entity."""

    entity_description: JudoSelectDescription

    def __init__(self, coordinator, client, description: JudoSelectDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._client = client
        self._attr_unique_id = f"{coordinator.data.serial}_{description.key}"
        self._attr_options = description.options

    @property
    def current_option(self) -> str | None:
        if self.entity_description.key == "vacation_type":
            mapping = {0: "off", 1: "u1", 2: "u2", 3: "u3"}
            return mapping.get(self.coordinator.data.vacation_type)
        mapping = {0: "off", 1: "notify", 2: "notify_close"}
        return mapping.get(self.coordinator.data.micro_leak_mode)

    async def async_select_option(self, option: str) -> None:
        await self.entity_description.set_option_fn(self._client, option, self)
