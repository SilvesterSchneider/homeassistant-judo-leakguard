"""Binary sensor platform for learning state."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import JudoBaseEntity

DESCRIPTION = BinarySensorEntityDescription(
    key="learn_active",
    translation_key="learn_active",
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([JudoLearnBinarySensor(coordinator)])


class JudoLearnBinarySensor(JudoBaseEntity, BinarySensorEntity):
    """Indicate whether learning mode is active."""

    _attr_entity_description = DESCRIPTION

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_learn_active"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.learn_active
