"""Core primitives for the lightweight Home Assistant test harness."""

from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional, Set

from .exceptions import HomeAssistantError
from .helpers import device_registry as dr, entity_registry as er


@dataclass
class ServiceCall:
    hass: "HomeAssistant"
    domain: str
    service: str
    data: Dict[str, Any]


@dataclass
class State:
    entity_id: str
    state: str
    attributes: Dict[str, Any]


class StateMachine:
    def __init__(self, hass: "HomeAssistant") -> None:
        self._states: Dict[str, State] = {}
        self.hass = hass

    def get(self, entity_id: str) -> Optional[State]:
        return self._states.get(entity_id)

    def async_set(self, entity_id: str, state: Any, attributes: Optional[Dict[str, Any]] = None) -> None:
        state_str = "unknown" if state is None else str(state)
        self._states[entity_id] = State(entity_id=entity_id, state=state_str, attributes=attributes or {})

    def async_remove(self, entity_id: str) -> None:
        self._states.pop(entity_id, None)


class ServiceRegistry:
    def __init__(self, hass: "HomeAssistant") -> None:
        self.hass = hass
        self._handlers: Dict[str, Dict[str, Callable[[ServiceCall], Any]]] = {}
        self._entity_handlers: Dict[str, Dict[str, str]] = {}

    def async_register(
        self,
        domain: str,
        service: str,
        handler: Callable[[ServiceCall], Any],
        *,
        schema: Any = None,
    ) -> None:
        self._handlers.setdefault(domain, {})[service] = handler

    def async_remove(self, domain: str, service: str) -> None:
        self._handlers.get(domain, {}).pop(service, None)

    def has_service(self, domain: str, service: str) -> bool:
        return service in self._handlers.get(domain, {}) or service in self._entity_handlers.get(domain, {})

    def register_entity_service(self, domain: str, service: str, method_name: str) -> None:
        self._entity_handlers.setdefault(domain, {})[service] = method_name

    async def async_call(
        self,
        domain: str,
        service: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        blocking: bool = False,
    ) -> None:
        data = dict(data or {})
        handler = self._handlers.get(domain, {}).get(service)
        if handler is not None:
            call = ServiceCall(self.hass, domain, service, data)
            result = handler(call)
            if inspect.isawaitable(result):
                if blocking:
                    await result
                else:
                    self.hass.async_create_task(result)
            elif blocking:
                await self.hass.async_block_till_done()
            return

        entity_services = self._entity_handlers.get(domain)
        if entity_services and service in entity_services:
            entity_id = data.get("entity_id")
            if not entity_id:
                raise HomeAssistantError("entity_id required for entity service call")
            entity = self.hass.get_entity(entity_id)
            if entity is None:
                raise HomeAssistantError(f"Entity {entity_id} not found")
            method_name = entity_services[service]
            if not hasattr(entity, method_name):
                raise HomeAssistantError(f"Entity {entity_id} does not implement {method_name}")
            method = getattr(entity, method_name)
            call_kwargs = dict(data)
            call_kwargs.pop("entity_id", None)
            result = method(**call_kwargs)
            if inspect.isawaitable(result):
                if blocking:
                    await result
                else:
                    self.hass.async_create_task(result)
            if blocking:
                await self.hass.async_block_till_done()
            return

        raise HomeAssistantError(f"Service {domain}.{service} not found")


_SLUGIFY_RE = re.compile(r"[^a-z0-9_]+")


def _slugify(value: str) -> str:
    value = value.strip().lower().replace(" ", "_")
    return _SLUGIFY_RE.sub("_", value)


class HomeAssistant:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.data: Dict[str, Any] = {}
        self.states = StateMachine(self)
        self.services = ServiceRegistry(self)
        self.config_entries = None  # delayed import to avoid cycle
        self._entities: Dict[str, Any] = {}
        self._entity_sources: Dict[str, Set[str]] = {}
        self._tasks: Set[asyncio.Task[Any]] = set()
        self._entity_counters: Dict[str, int] = {}

        # Entity services for the supported domains
        self.services.register_entity_service("button", "press", "async_press")
        self.services.register_entity_service("switch", "turn_on", "async_turn_on")
        self.services.register_entity_service("switch", "turn_off", "async_turn_off")
        self.services.register_entity_service("number", "set_value", "async_set_native_value")
        self.services.register_entity_service("select", "select_option", "async_select_option")

    def attach_config_entries(self, manager) -> None:
        self.config_entries = manager

    def async_create_task(self, coro: Awaitable[Any]) -> asyncio.Task[Any]:
        task = self.loop.create_task(coro)
        self._tasks.add(task)

        def _done(_):
            self._tasks.discard(task)

        task.add_done_callback(_done)
        return task

    async def async_block_till_done(self) -> None:
        await asyncio.sleep(0)
        pending = [task for task in self._tasks if not task.done()]
        for task in pending:
            await asyncio.sleep(0)

    async def async_stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.sleep(0)

    def get_entity(self, entity_id: str):
        return self._entities.get(entity_id)

    def _next_entity_id(self, domain: str) -> str:
        self._entity_counters.setdefault(domain, 0)
        self._entity_counters[domain] += 1
        return f"{domain}.{domain}_{self._entity_counters[domain]}"

    async def _async_add_entities(
        self,
        entry,
        domain: str,
        platform: str,
        entities: Iterable[Any],
        update_before_add: bool,
    ) -> None:
        entity_registry = er.async_get(self)
        device_registry = dr.async_get(self)
        for entity in entities:
            entity.hass = self
            if update_before_add:
                await entity.async_update()
            unique_id = getattr(entity, "unique_id", None)
            if unique_id:
                object_id = _slugify(str(unique_id))
                entity_id = f"{domain}.{object_id}"
            else:
                entity_id = self._next_entity_id(domain)
            entity.entity_id = entity_id

            device_id = None
            device_info = getattr(entity, "device_info", None)
            if device_info is not None:
                identifiers = set(tuple(pair) for pair in device_info.identifiers)
                entry_info = device_registry.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    identifiers=identifiers,
                    manufacturer=device_info.manufacturer,
                    model=device_info.model,
                    name=device_info.name,
                    sw_version=device_info.sw_version,
                )
                device_id = entry_info.id

            entity_registry._register(
                domain,
                platform,
                unique_id,
                entity_id,
                device_id=device_id,
                config_entry_id=entry.entry_id,
            )
            self._entities[entity_id] = entity
            self._entity_sources.setdefault(entry.entry_id, set()).add(entity_id)
            await entity.async_added_to_hass()
            entity.async_write_ha_state()

    def _remove_entities_for_entry(self, entry_id: str) -> None:
        entity_ids = self._entity_sources.pop(entry_id, set())
        entity_registry = er.async_get(self)
        for entity_id in entity_ids:
            self.states.async_remove(entity_id)
            self._entities.pop(entity_id, None)
            entity_registry.async_remove(entity_id)


__all__ = ["HomeAssistant", "ServiceCall", "State", "StateMachine"]
