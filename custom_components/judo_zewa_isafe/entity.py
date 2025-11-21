"""Base entity for the integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JudoDataUpdateCoordinator


class JudoBaseEntity(CoordinatorEntity[JudoDataUpdateCoordinator]):
    """Common entity behaviour for ZEWA devices."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JudoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        serial = coordinator.data.serial
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            manufacturer="Judo",
            model=coordinator.data.device_type,
            name="Judo ZEWA i-SAFE",
            sw_version=coordinator.data.firmware,
        )
