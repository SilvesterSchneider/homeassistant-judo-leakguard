"""Number-Plattform für JUDO ZEWA i-SAFE (konfigurierbare Zahlenwerte)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Awaitable, Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JudoApiClient
from .const import DOMAIN
from .coordinator import JudoData, JudoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class JudoNumberEntityDescription(NumberEntityDescription):
    value_fn: Callable[[JudoData], float | int | None] = lambda _: None
    set_fn: Callable[[JudoApiClient, float], Awaitable[None]] | None = None


NUMBER_DESCRIPTIONS: tuple[JudoNumberEntityDescription, ...] = (
    # ── Schlafdauer ───────────────────────────────────────────────────────────
    JudoNumberEntityDescription(
        key="sleep_hours",
        name="Schlafdauer",
        icon="mdi:sleep",
        native_min_value=1,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement="h",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.status.sleep_hours,
        set_fn=lambda c, v: c.set_sleep_hours(int(v)),
    ),
    # ── Abwesenheit: Durchfluss-Limit ─────────────────────────────────────────
    JudoNumberEntityDescription(
        key="absence_flow_limit",
        name="Abwesenheit – Durchfluss-Limit",
        icon="mdi:water-pump",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        native_unit_of_measurement="L/h",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.status.absence_flow_limit,
        set_fn=lambda c, v: _set_absence_flow(c, int(v)),
    ),
    # ── Abwesenheit: Volumen-Limit ────────────────────────────────────────────
    JudoNumberEntityDescription(
        key="absence_volume_limit",
        name="Abwesenheit – Volumen-Limit",
        icon="mdi:water-boiler",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        native_unit_of_measurement="L",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.status.absence_volume_limit,
        set_fn=lambda c, v: _set_absence_volume(c, int(v)),
    ),
    # ── Abwesenheit: Dauer-Limit ──────────────────────────────────────────────
    JudoNumberEntityDescription(
        key="absence_duration_limit",
        name="Abwesenheit – Dauer-Limit",
        icon="mdi:timer",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.status.absence_duration_limit,
        set_fn=lambda c, v: _set_absence_duration(c, int(v)),
    ),
)


# Helfer: einzelne Absence-Werte setzen, andere aus Coordinator-Daten lesen
async def _set_absence_flow(client: JudoApiClient, value: int) -> None:
    # Wir rufen die aktuellen Limits ab und überschreiben nur den Flow-Wert
    flow, volume, duration = await client.get_absence_limits()
    await client.set_absence_limits(value, volume, duration)


async def _set_absence_volume(client: JudoApiClient, value: int) -> None:
    flow, volume, duration = await client.get_absence_limits()
    await client.set_absence_limits(flow, value, duration)


async def _set_absence_duration(client: JudoApiClient, value: int) -> None:
    flow, volume, duration = await client.get_absence_limits()
    await client.set_absence_limits(flow, volume, value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: JudoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JudoNumber(coordinator, description, entry)
        for description in NUMBER_DESCRIPTIONS
    )


class JudoNumber(CoordinatorEntity[JudoDataUpdateCoordinator], NumberEntity):
    """Konfigurationswert der JUDO ZEWA i-SAFE Integration."""

    entity_description: JudoNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JudoDataUpdateCoordinator,
        description: JudoNumberEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JUDO ZEWA i-SAFE",
            manufacturer="JUDO Wasseraufbereitung GmbH",
            model="ZEWA i-SAFE",
        )

    @property
    def native_value(self) -> float | int | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.entity_description.set_fn(self.coordinator.client, value)
            await self.coordinator.async_request_refresh()
        except Exception as exc:
            raise HomeAssistantError(
                f"Setzen von '{self.entity_description.key}' fehlgeschlagen: {exc}"
            ) from exc
