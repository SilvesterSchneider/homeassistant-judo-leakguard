"""Simple entity registry used by the tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class EntityRegistryEntry:
    entity_id: str
    unique_id: Optional[str]
    platform: str
    domain: str
    device_id: Optional[str] = None
    config_entry_id: Optional[str] = None


class EntityRegistry:
    def __init__(self) -> None:
        self._entities: Dict[str, EntityRegistryEntry] = {}
        self._by_unique: Dict[Tuple[str, str, str], str] = {}

    def async_get(self, entity_id: str) -> Optional[EntityRegistryEntry]:
        return self._entities.get(entity_id)

    def async_get_entity_id(self, domain: str, platform: str, unique_id: str) -> Optional[str]:
        return self._by_unique.get((domain, platform, unique_id))

    def _register(
        self,
        domain: str,
        platform: str,
        unique_id: Optional[str],
        entity_id: str,
        *,
        device_id: Optional[str] = None,
        config_entry_id: Optional[str] = None,
    ) -> EntityRegistryEntry:
        entry = EntityRegistryEntry(
            entity_id=entity_id,
            unique_id=unique_id,
            platform=platform,
            domain=domain,
            device_id=device_id,
            config_entry_id=config_entry_id,
        )
        self._entities[entity_id] = entry
        if unique_id is not None:
            self._by_unique[(domain, platform, unique_id)] = entity_id
        return entry

    def async_remove(self, entity_id: str) -> None:
        entry = self._entities.pop(entity_id, None)
        if entry and entry.unique_id is not None:
            self._by_unique.pop((entry.domain, entry.platform, entry.unique_id), None)


def async_get(hass) -> EntityRegistry:
    registry = hass.data.get("_entity_registry")
    if registry is None:
        registry = EntityRegistry()
        hass.data["_entity_registry"] = registry
    return registry


__all__ = ["EntityRegistry", "EntityRegistryEntry", "async_get"]
