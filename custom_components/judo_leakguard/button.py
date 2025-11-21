"""Button platform for Judo Leakguard."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoLeakguardCoordinator
from .entity import JudoLeakguardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: JudoLeakguardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JudoLeakguardMicroLeakTestButton(coordinator),
            JudoLeakguardLearnModeButton(coordinator),
            JudoLeakguardResetAlarmsButton(coordinator),
        ]
    )


class JudoLeakguardMicroLeakTestButton(JudoLeakguardEntity, ButtonEntity):
    """Button to start micro leak test."""

    _attr_translation_key = "start_microleak_test"
    _attr_unique_id = "start_microleak_test"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_trigger_micro_leak_test(self.coordinator.session)


class JudoLeakguardLearnModeButton(JudoLeakguardEntity, ButtonEntity):
    """Button to start learn mode."""

    _attr_translation_key = "start_learning"
    _attr_unique_id = "start_learning"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_start_learn_mode(self.coordinator.session)


class JudoLeakguardResetAlarmsButton(JudoLeakguardEntity, ButtonEntity):
    """Button to reset alarms."""

    _attr_translation_key = "reset_alarms"
    _attr_unique_id = "reset_alarms"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_acknowledge_alarm(self.coordinator.session)
