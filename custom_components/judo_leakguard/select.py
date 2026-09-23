"""Select-Plattform für JUDO ZEWA i-SAFE (Urlaubstyp & Mikroleck-Modus)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JudoApiClient
from .const import (
    DOMAIN,
    MICROLEAK_MODES,
    MICROLEAK_MODES_REVERSE,
    VACATION_TYPES,
    VACATION_TYPES_REVERSE,
)
from .coordinator import JudoData, JudoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class JudoSelectEntityDescription(SelectEntityDescription):
    options_list: list[str] = None  # type: ignore[assignment]
    current_option_fn: Callable[[JudoData], str | None] = lambda _: None
    select_fn: Callable[[JudoApiClient, str], Awaitable[None]] | None = None
    # Kein Lesebefehl am Gerät: zuletzt gesendeten Wert merken
    optimistic: bool = False


SELECT_DESCRIPTIONS: tuple[JudoSelectEntityDescription, ...] = (
    JudoSelectEntityDescription(
        key="vacation_type",
        name="Urlaubstyp",
        icon="mdi:beach",
        options_list=list(VACATION_TYPES.values()),
        optimistic=True,  # das Gerät kennt keinen Lesebefehl für den Urlaubstyp
        select_fn=lambda c, v: c.set_vacation_type(VACATION_TYPES_REVERSE[v]),
    ),
    JudoSelectEntityDescription(
        key="microleak_mode",
        name="Mikroleck-Modus",
        icon="mdi:water-check",
        options_list=list(MICROLEAK_MODES.values()),
        current_option_fn=lambda d: MICROLEAK_MODES.get(d.status.microleak_mode),
        select_fn=lambda c, v: c.set_microleak_mode(MICROLEAK_MODES_REVERSE[v]),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: JudoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JudoSelect(coordinator, description, entry)
        for description in SELECT_DESCRIPTIONS
    )


class JudoSelect(CoordinatorEntity[JudoDataUpdateCoordinator], RestoreEntity, SelectEntity):
    """Repräsentiert eine Auswahlentität der JUDO ZEWA i-SAFE Integration."""

    entity_description: JudoSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JudoDataUpdateCoordinator,
        description: JudoSelectEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_options = description.options_list
        self._last_option: str | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JUDO ZEWA i-SAFE",
            manufacturer="JUDO Wasseraufbereitung GmbH",
            model="ZEWA i-SAFE",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if not self.entity_description.optimistic:
            return
        self._attr_assumed_state = True
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self.options:
            self._last_option = last_state.state

    @property
    def current_option(self) -> str | None:
        if self.entity_description.optimistic:
            return self._last_option
        if self.coordinator.data is None:
            return None
        return self.entity_description.current_option_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        try:
            await self.entity_description.select_fn(self.coordinator.client, option)
            if self.entity_description.optimistic:
                self._last_option = option
                self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        except Exception as exc:
            raise HomeAssistantError(
                f"Auswahl '{self.entity_description.key}' fehlgeschlagen: {exc}"
            ) from exc
