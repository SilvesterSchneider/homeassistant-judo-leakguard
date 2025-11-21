"""Switch platform for Judo Leakguard."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
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
    """Set up the switch platform."""
    coordinator: JudoLeakguardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JudoLeakguardValveSwitch(coordinator),
            JudoLeakguardSleepSwitch(coordinator),
            JudoLeakguardVacationSwitch(coordinator),
        ]
    )


class JudoLeakguardValveSwitch(JudoLeakguardEntity, SwitchEntity):
    """Switch to control the valve."""

    _attr_translation_key = "valve_open"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_unique_id = "valve_open"

    def __init__(self, coordinator: JudoLeakguardCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        # Optimistic state
        self._is_on = True  # Default to open? Or unknown?

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Open the valve."""
        await self.coordinator.api.async_open_valve(self.coordinator.session)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close the valve."""
        await self.coordinator.api.async_close_valve(self.coordinator.session)
        self._is_on = False
        self.async_write_ha_state()


class JudoLeakguardSleepSwitch(JudoLeakguardEntity, SwitchEntity):
    """Switch to control sleep mode."""

    _attr_translation_key = "sleep_mode"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_unique_id = "sleep_mode"

    def __init__(self, coordinator: JudoLeakguardCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._is_on = False

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start sleep mode."""
        await self.coordinator.api.async_start_sleep_mode(self.coordinator.session)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """End sleep mode."""
        await self.coordinator.api.async_end_sleep_mode(self.coordinator.session)
        self._is_on = False
        self.async_write_ha_state()


class JudoLeakguardVacationSwitch(JudoLeakguardEntity, SwitchEntity):
    """Switch to control vacation mode."""

    _attr_translation_key = "vacation_mode"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_unique_id = "vacation_mode"

    def __init__(self, coordinator: JudoLeakguardCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._is_on = False

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start vacation mode."""
        await self.coordinator.api.async_start_vacation_mode(self.coordinator.session)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """End vacation mode."""
        await self.coordinator.api.async_end_vacation_mode(self.coordinator.session)
        self._is_on = False
        self.async_write_ha_state()
