"""Minimal configuration entry framework for tests."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from .core import HomeAssistant


HANDLERS: Dict[str, type["ConfigFlow"]] = {}

SOURCE_USER = "user"


class ConfigEntryState:
    LOADED = "loaded"
    NOT_LOADED = "not_loaded"


class ConfigFlow:
    """Base class for configuration flows."""

    VERSION = 1

    def __init_subclass__(cls, *, domain: Optional[str] = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if domain is not None:
            cls.domain = domain
            HANDLERS[domain] = cls

    def __init__(self) -> None:
        self.hass = None
        self.context: Dict[str, Any] = {}
        self._unique_id: Optional[str] = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):  # pragma: no cover - overridden in tests
        raise NotImplementedError

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):  # pragma: no cover
        raise NotImplementedError

    async def async_set_unique_id(self, unique_id: str) -> None:
        self._unique_id = unique_id

    def _async_current_entries(self) -> List["ConfigEntry"]:
        if self.hass is None or self.hass.config_entries is None:
            return []
        return list(self.hass.config_entries._entries.values())

    def _abort_if_unique_id_configured(self) -> None:
        if self._unique_id is None:
            return
        for entry in self._async_current_entries():
            if entry.unique_id == self._unique_id:
                raise AbortFlow("already_configured")

    def async_show_form(self, *, step_id: str, data_schema: Any, errors: Optional[Dict[str, str]] = None):
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
        }

    def async_create_entry(self, *, title: str, data: Dict[str, Any]):
        return {
            "type": "create_entry",
            "title": title,
            "data": data,
        }

    def async_abort(self, *, reason: str):
        return {
            "type": "abort",
            "reason": reason,
        }


class AbortFlow(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class OptionsFlow:
    def async_show_form(self, *, step_id: str, data_schema: Any, errors: Optional[Dict[str, str]] = None):
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
        }

    def async_create_entry(self, *, title: str, data: Dict[str, Any]):
        return {
            "type": "create_entry",
            "title": title,
            "data": data,
        }


@dataclass
class ConfigEntry:
    domain: str
    title: str
    data: Dict[str, Any]
    options: Dict[str, Any]
    entry_id: str
    unique_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.hass = None
        self.state = ConfigEntryState.NOT_LOADED
        self._on_unload: List[Callable[[], Any]] = []
        self._update_listeners: List[Callable[[HomeAssistant, ConfigEntry], Any]] = []

    def add_to_hass(self, hass: HomeAssistant) -> None:
        self.hass = hass
        hass.config_entries._add(self)

    def add_update_listener(self, listener: Callable[[HomeAssistant, ConfigEntry], Any]) -> Callable[[], None]:
        self._update_listeners.append(listener)

        def _remove() -> None:
            self._update_listeners.remove(listener)

        return _remove

    def async_on_unload(self, callback: Callable[[], Any]) -> None:
        self._on_unload.append(callback)

    async def async_unload(self) -> None:
        for callback in list(self._on_unload):
            result = callback()
            if inspect.isawaitable(result):
                await result
        self._on_unload.clear()


class ConfigEntriesFlowManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._flows: Dict[str, Dict[str, Any]] = {}

    async def async_init(self, domain: str, *, context: Optional[Dict[str, Any]] = None):
        handler = HANDLERS.get(domain)
        if handler is None:
            raise ValueError(f"No config flow handler for domain {domain}")
        flow = handler()
        flow.hass = self.hass
        flow.context = context or {}
        flow_id = uuid4().hex
        try:
            result = await flow.async_step_user()
        except AbortFlow as exc:
            return {"type": "abort", "reason": exc.reason, "flow_id": flow_id}
        if result["type"] == "form":
            result["flow_id"] = flow_id
            self._flows[flow_id] = {"flow": flow, "step_id": result["step_id"]}
        else:
            result["flow_id"] = flow_id
        return result

    async def async_configure(self, flow_id: str, user_input: Optional[Dict[str, Any]] = None):
        if flow_id not in self._flows:
            raise ValueError(f"Unknown flow_id: {flow_id}")
        entry = self._flows[flow_id]
        flow: ConfigFlow = entry["flow"]
        step_id: str = entry["step_id"]
        step_method = getattr(flow, f"async_step_{step_id}")
        try:
            result = await step_method(user_input)
        except AbortFlow as exc:
            self._flows.pop(flow_id, None)
            return {"type": "abort", "reason": exc.reason, "flow_id": flow_id}
        result["flow_id"] = flow_id
        if result["type"] == "form":
            entry["step_id"] = result["step_id"]
        else:
            self._flows.pop(flow_id, None)
        return result


class ConfigEntries:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._entries: Dict[str, ConfigEntry] = {}
        self.flow = ConfigEntriesFlowManager(hass)
        hass.attach_config_entries(self)

    def _add(self, entry: ConfigEntry) -> None:
        self._entries[entry.entry_id] = entry

    def async_entries(self) -> List[ConfigEntry]:
        return list(self._entries.values())

    async def async_setup(self, entry_id: str) -> bool:
        entry = self._entries[entry_id]
        module = import_module(f"custom_components.{entry.domain}")
        setup = getattr(module, "async_setup_entry")
        success = await setup(self.hass, entry)
        if success:
            entry.state = ConfigEntryState.LOADED
        return success

    async def async_forward_entry_setups(self, entry: ConfigEntry, platforms: Iterable[Any]) -> None:
        tasks: List[asyncio.Task[Any]] = []
        for platform in platforms:
            platform_name = getattr(platform, "value", str(platform))
            module = import_module(f"custom_components.{entry.domain}.{platform_name}")

            def _add_entities(entities: Iterable[Any], update_before_add: bool = False, *, _platform=platform_name) -> None:
                task = self.hass.async_create_task(
                    self.hass._async_add_entities(entry, _platform, entry.domain, list(entities), update_before_add)
                )
                tasks.append(task)

            setup = getattr(module, "async_setup_entry")
            await setup(self.hass, entry, _add_entities)
        if tasks:
            await asyncio.gather(*tasks)

    async def async_unload_platforms(self, entry: ConfigEntry, platforms: Iterable[Any]) -> bool:
        unload_ok = True
        for platform in platforms:
            platform_name = getattr(platform, "value", str(platform))
            module = import_module(f"custom_components.{entry.domain}.{platform_name}")
            unload = getattr(module, "async_unload_entry", None)
            if unload is not None:
                result = await unload(self.hass, entry)
                unload_ok = unload_ok and bool(result)
        self.hass._remove_entities_for_entry(entry.entry_id)
        return unload_ok

    async def async_unload(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry is None:
            return False
        module = import_module(f"custom_components.{entry.domain}")
        unload = getattr(module, "async_unload_entry", None)
        if unload is None:
            return False
        success = await unload(self.hass, entry)
        if success:
            await entry.async_unload()
            entry.state = ConfigEntryState.NOT_LOADED
        return success

    async def async_reload(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            return False
        success = await self.async_unload(entry_id)
        if not success:
            return False
        return await self.async_setup(entry_id)


__all__ = [
    "ConfigEntries",
    "ConfigEntriesFlowManager",
    "ConfigEntry",
    "ConfigEntryState",
    "ConfigFlow",
    "OptionsFlow",
    "SOURCE_USER",
]
