"""Entity base classes used by the lightweight Home Assistant harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Optional

from homeassistant.const import STATE_UNKNOWN


class EntityCategory(str, Enum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


@dataclass
class DeviceInfo:
    identifiers: Iterable[tuple[str, str]]
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sw_version: Optional[str] = None
    name: Optional[str] = None


class Entity:
    """Small subset of the Home Assistant entity API."""

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_name: Optional[str] = None
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[DeviceInfo] = None
    _attr_extra_state_attributes: Optional[Dict[str, Any]] = None

    def __init__(self) -> None:
        self.hass = None
        self.entity_id: Optional[str] = None

    @property
    def should_poll(self) -> bool:
        return getattr(self, "_attr_should_poll", False)

    @property
    def name(self) -> Optional[str]:
        return getattr(self, "_attr_name", None)

    @property
    def unique_id(self) -> Optional[str]:
        return getattr(self, "_attr_unique_id", None)

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        return getattr(self, "_attr_device_info", None)

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        return getattr(self, "_attr_extra_state_attributes", None)

    @property
    def state(self) -> Any:
        return getattr(self, "_attr_state", STATE_UNKNOWN)

    async def async_added_to_hass(self) -> None:  # pragma: no cover - default implementation
        return None

    async def async_update(self) -> None:  # pragma: no cover - default implementation
        return None

    def async_write_ha_state(self) -> None:
        if self.hass is None or self.entity_id is None:
            return
        state = self.state
        attributes = dict(self.extra_state_attributes or {})
        self.hass.states.async_set(self.entity_id, state, attributes)


__all__ = ["DeviceInfo", "Entity", "EntityCategory"]
