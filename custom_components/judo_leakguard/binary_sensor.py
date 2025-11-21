"""Binary Sensor platform for Judo Leakguard."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up the binary_sensor platform."""
    coordinator: JudoLeakguardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JudoLeakguardLearnActiveBinarySensor(coordinator)])


class JudoLeakguardLearnActiveBinarySensor(JudoLeakguardEntity, BinarySensorEntity):
    """Binary sensor to show if learn mode is active."""

    _attr_translation_key = "learn_active"
    _attr_unique_id = "learn_active"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.learn_status.active
