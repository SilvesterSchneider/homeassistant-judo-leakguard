"""Button-Plattform für JUDO ZEWA i-SAFE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Awaitable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import JudoApiClient
from .const import DOMAIN
from .coordinator import JudoDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class JudoButtonEntityDescription(ButtonEntityDescription):
    press_fn: Callable[[JudoApiClient], Awaitable[None]] | None = None


BUTTON_DESCRIPTIONS: tuple[JudoButtonEntityDescription, ...] = (
    JudoButtonEntityDescription(
        key="reset_alarms",
        name="Meldungen zurücksetzen",
        icon="mdi:bell-off",
        press_fn=lambda c: c.ack_alarm(),
    ),
    JudoButtonEntityDescription(
        key="start_microleak_test",
        name="Mikroleck-Test starten",
        icon="mdi:water-check",
        press_fn=lambda c: c.start_microleak_test(),
    ),
    JudoButtonEntityDescription(
        key="start_learning",
        name="Lernmodus starten",
        icon="mdi:school",
        press_fn=lambda c: c.start_learning(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: JudoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    client = coordinator.client
    async_add_entities(
        JudoButton(description, client, entry) for description in BUTTON_DESCRIPTIONS
    )


class JudoButton(ButtonEntity):
    """Repräsentiert einen einmaligen Aktion-Button."""

    entity_description: JudoButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        description: JudoButtonEntityDescription,
        client: JudoApiClient,
        entry: ConfigEntry,
    ) -> None:
        self.entity_description = description
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JUDO ZEWA i-SAFE",
            manufacturer="JUDO Wasseraufbereitung GmbH",
            model="ZEWA i-SAFE",
        )

    async def async_press(self) -> None:
        try:
            await self.entity_description.press_fn(self._client)
        except Exception as exc:
            raise HomeAssistantError(
                f"Aktion '{self.entity_description.key}' fehlgeschlagen: {exc}"
            ) from exc
