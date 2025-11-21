"""Number platform for Judo Leakguard."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up the number platform."""
    coordinator: JudoLeakguardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JudoLeakguardSleepHoursNumber(coordinator),
            JudoLeakguardAbsenceFlowLimitNumber(coordinator),
            JudoLeakguardAbsenceVolumeLimitNumber(coordinator),
            JudoLeakguardAbsenceDurationLimitNumber(coordinator),
        ]
    )


class JudoLeakguardSleepHoursNumber(JudoLeakguardEntity, NumberEntity):
    """Number to set sleep hours."""

    _attr_translation_key = "sleep_hours"
    _attr_unique_id = "sleep_hours"
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        """Return the value."""
        return float(self.coordinator.data.sleep_hours)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator.api.async_set_sleep_hours(self.coordinator.session, int(value))
        await self.coordinator.async_request_refresh()


class JudoLeakguardAbsenceFlowLimitNumber(JudoLeakguardEntity, NumberEntity):
    """Number to set absence flow limit."""

    _attr_translation_key = "absence_flow_limit"
    _attr_unique_id = "absence_flow_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535  # U16
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        """Return the value."""
        return float(self.coordinator.data.absence_limits.max_flow_lph)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        current = self.coordinator.data.absence_limits
        new_limits = type(current)(
            max_flow_lph=int(value),
            max_volume_l=current.max_volume_l,
            max_duration_min=current.max_duration_min,
        )
        await self.coordinator.api.async_write_absence_limits(self.coordinator.session, new_limits)
        await self.coordinator.async_request_refresh()


class JudoLeakguardAbsenceVolumeLimitNumber(JudoLeakguardEntity, NumberEntity):
    """Number to set absence volume limit."""

    _attr_translation_key = "absence_volume_limit"
    _attr_unique_id = "absence_volume_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        """Return the value."""
        return float(self.coordinator.data.absence_limits.max_volume_l)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        current = self.coordinator.data.absence_limits
        new_limits = type(current)(
            max_flow_lph=current.max_flow_lph,
            max_volume_l=int(value),
            max_duration_min=current.max_duration_min,
        )
        await self.coordinator.api.async_write_absence_limits(self.coordinator.session, new_limits)
        await self.coordinator.async_request_refresh()


class JudoLeakguardAbsenceDurationLimitNumber(JudoLeakguardEntity, NumberEntity):
    """Number to set absence duration limit."""

    _attr_translation_key = "absence_duration_limit"
    _attr_unique_id = "absence_duration_limit"
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        """Return the value."""
        return float(self.coordinator.data.absence_limits.max_duration_min)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        current = self.coordinator.data.absence_limits
        new_limits = type(current)(
            max_flow_lph=current.max_flow_lph,
            max_volume_l=current.max_volume_l,
            max_duration_min=int(value),
        )
        await self.coordinator.api.async_write_absence_limits(self.coordinator.session, new_limits)
        await self.coordinator.async_request_refresh()
