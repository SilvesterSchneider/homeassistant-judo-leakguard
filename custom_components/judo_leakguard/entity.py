"""Base entity for Judo Leakguard."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JudoLeakguardCoordinator


class JudoLeakguardEntity(CoordinatorEntity[JudoLeakguardCoordinator]):
    """Base entity for Judo Leakguard."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JudoLeakguardCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data.serial_number)},
            name="Judo Leakguard",
            manufacturer="Judo",
            model="ZEWA i-SAFE",
            sw_version=coordinator.data.firmware_info.version,
            serial_number=coordinator.data.serial_number,
        )
