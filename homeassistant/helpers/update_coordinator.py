"""Subset of Home Assistant's DataUpdateCoordinator implementation."""

from __future__ import annotations

from typing import Any, Callable, Generic, Optional, Set, TypeVar

from .entity import Entity

T = TypeVar("T")


class UpdateFailed(Exception):
    """Raised when a data update fails."""


class DataUpdateCoordinator(Generic[T]):
    def __init__(self, hass, logger, *, name: str, update_interval) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: Optional[T] = None
        self.last_update_success = False
        self._listeners: Set[Callable[[], None]] = set()

    async def _async_update_data(self) -> T:  # pragma: no cover - to be implemented by subclasses
        raise NotImplementedError

    async def async_config_entry_first_refresh(self) -> None:
        await self._async_refresh()

    async def async_request_refresh(self) -> None:
        await self._async_refresh()

    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(update_callback)

        def _remove() -> None:
            self._listeners.discard(update_callback)

        return _remove

    async def _async_refresh(self) -> None:
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except Exception as err:  # pragma: no cover - logged for visibility
            self.last_update_success = False
            if self.logger:
                self.logger.debug("Coordinator %s update failed: %s", self.name, err)
            raise
        finally:
            for listener in list(self._listeners):
                listener()


class CoordinatorEntity(Entity):
    """Entity that is backed by a :class:`DataUpdateCoordinator`."""

    def __init__(self, coordinator: DataUpdateCoordinator[Any]) -> None:
        super().__init__()
        self.coordinator = coordinator
        self._remove_listener: Optional[Callable[[], None]] = None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self.coordinator.async_add_listener(self._handle_coordinator_update)
        if self.coordinator.data is not None:
            self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:  # pragma: no cover - not triggered in tests
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None


__all__ = ["CoordinatorEntity", "DataUpdateCoordinator", "UpdateFailed"]
