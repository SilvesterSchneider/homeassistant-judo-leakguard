"""Binärsensor-Plattform für JUDO ZEWA i-SAFE."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JudoDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: JudoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JudoLearnActiveSensor(coordinator, entry)])


class JudoLearnActiveSensor(
    CoordinatorEntity[JudoDataUpdateCoordinator], BinarySensorEntity
):
    """Zeigt an, ob der Lernmodus aktiv ist."""

    _attr_has_entity_name = True
    _attr_name = "Lernmodus aktiv"
    _attr_icon = "mdi:school"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self, coordinator: JudoDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_learn_active"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JUDO ZEWA i-SAFE",
            manufacturer="JUDO Wasseraufbereitung GmbH",
            model="ZEWA i-SAFE",
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.status.learn_active
