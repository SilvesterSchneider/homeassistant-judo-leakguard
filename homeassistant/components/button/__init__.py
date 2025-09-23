"""Minimal button entity."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity


class ButtonEntity(Entity):
    async def async_press(self) -> None:  # pragma: no cover - overridden by entities
        raise NotImplementedError

    @property
    def state(self) -> str:
        return "unknown"


__all__ = ["ButtonEntity"]
