"""Simple in-memory device registry for tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional


@dataclass
class DeviceEntry:
    id: str
    identifiers: set[tuple[str, str]] = field(default_factory=set)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    sw_version: Optional[str] = None


class DeviceRegistry:
    def __init__(self) -> None:
        self._devices: Dict[str, DeviceEntry] = {}
        self._identifiers: Dict[tuple[str, str], str] = {}
        self._counter = 0

    def async_get_or_create(
        self,
        *,
        config_entry_id: str,
        identifiers: Iterable[tuple[str, str]],
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        name: Optional[str] = None,
        sw_version: Optional[str] = None,
    ) -> DeviceEntry:
        identifier_set = {tuple(identifier) for identifier in identifiers}
        for identifier in identifier_set:
            if identifier in self._identifiers:
                existing = self._identifiers[identifier]
                entry = self._devices[existing]
                if manufacturer is not None:
                    entry.manufacturer = manufacturer
                if model is not None:
                    entry.model = model
                if name is not None:
                    entry.name = name
                if sw_version is not None:
                    entry.sw_version = sw_version
                entry.identifiers.update(identifier_set)
                return entry

        self._counter += 1
        device_id = f"device-{self._counter}"
        entry = DeviceEntry(
            id=device_id,
            identifiers=identifier_set,
            manufacturer=manufacturer,
            model=model,
            name=name,
            sw_version=sw_version,
        )
        self._devices[device_id] = entry
        for identifier in identifier_set:
            self._identifiers[identifier] = device_id
        return entry

    def async_get(self, device_id: str) -> Optional[DeviceEntry]:
        return self._devices.get(device_id)

    @property
    def devices(self) -> Dict[str, DeviceEntry]:
        return self._devices


def async_get(hass) -> DeviceRegistry:
    registry = hass.data.get("_device_registry")
    if registry is None:
        registry = DeviceRegistry()
        hass.data["_device_registry"] = registry
    return registry


__all__ = ["DeviceEntry", "DeviceRegistry", "async_get"]
