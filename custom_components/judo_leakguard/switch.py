"""Switch-Plattform für JUDO ZEWA i-SAFE.

Hinweis: Das Gerät bietet keine Status-Rücklese-Kommandos für Ventil,
Sleep- und Urlaubsmodus. Die Switches arbeiten daher im „optimistic"-Modus –
der angezeigte Zustand entspricht dem zuletzt gesendeten Befehl.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .api import JudoApiClient
from .const import DOMAIN
from .coordinator import JudoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: JudoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    client = coordinator.client
    async_add_entities(
        [
            JudoValveSwitch(coordinator, client, entry),
            JudoSleepModeSwitch(coordinator, client, entry),
            JudoVacationModeSwitch(coordinator, client, entry),
        ]
    )


class JudoOptimisticSwitch(
    RestoreEntity, SwitchEntity
):
    """Basisklasse für optimistische Switches (kein Status-Readback)."""

    _attr_has_entity_name = True
    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: JudoDataUpdateCoordinator,
        client: JudoApiClient,
        entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._client = client
        self._is_on: bool = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JUDO ZEWA i-SAFE",
            manufacturer="JUDO Wasseraufbereitung GmbH",
            model="ZEWA i-SAFE",
        )

    async def async_added_to_hass(self) -> None:
        """Letzten Zustand aus dem HA-State-Store wiederherstellen."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        return self._is_on


# ── Ventil ────────────────────────────────────────────────────────────────────

class JudoValveSwitch(JudoOptimisticSwitch):
    """Steuert das Absperrventil (ON = offen, OFF = geschlossen)."""

    _attr_name = "Ventil"
    _attr_icon = "mdi:valve"

    def __init__(self, coordinator, client, entry):
        super().__init__(coordinator, client, entry)
        self._attr_unique_id = f"{entry.entry_id}_valve_open"
        # Standardzustand: offen
        self._is_on = True

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self._client.valve_open()
            self._is_on = True
            self.async_write_ha_state()
        except Exception as exc:
            raise HomeAssistantError(f"Ventil öffnen fehlgeschlagen: {exc}") from exc

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._client.valve_close()
            self._is_on = False
            self.async_write_ha_state()
        except Exception as exc:
            raise HomeAssistantError(f"Ventil schließen fehlgeschlagen: {exc}") from exc


# ── Sleep-Modus ───────────────────────────────────────────────────────────────

class JudoSleepModeSwitch(JudoOptimisticSwitch):
    """Steuert den Sleep-Modus."""

    _attr_name = "Sleep-Modus"
    _attr_icon = "mdi:sleep"

    def __init__(self, coordinator, client, entry):
        super().__init__(coordinator, client, entry)
        self._attr_unique_id = f"{entry.entry_id}_sleep_mode"

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self._client.sleep_start()
            self._is_on = True
            self.async_write_ha_state()
        except Exception as exc:
            raise HomeAssistantError(f"Sleep-Modus starten fehlgeschlagen: {exc}") from exc

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._client.sleep_stop()
            self._is_on = False
            self.async_write_ha_state()
        except Exception as exc:
            raise HomeAssistantError(f"Sleep-Modus beenden fehlgeschlagen: {exc}") from exc


# ── Urlaubsmodus ──────────────────────────────────────────────────────────────

class JudoVacationModeSwitch(JudoOptimisticSwitch):
    """Steuert den Urlaubsmodus."""

    _attr_name = "Urlaubsmodus"
    _attr_icon = "mdi:beach"

    def __init__(self, coordinator, client, entry):
        super().__init__(coordinator, client, entry)
        self._attr_unique_id = f"{entry.entry_id}_vacation_mode"

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self._client.vacation_start()
            self._is_on = True
            self.async_write_ha_state()
        except Exception as exc:
            raise HomeAssistantError(f"Urlaubsmodus starten fehlgeschlagen: {exc}") from exc

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._client.vacation_stop()
            self._is_on = False
            self.async_write_ha_state()
        except Exception as exc:
            raise HomeAssistantError(f"Urlaubsmodus beenden fehlgeschlagen: {exc}") from exc
