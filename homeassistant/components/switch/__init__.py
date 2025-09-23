"""Minimal switch entity implementation."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity


class SwitchEntity(Entity):
    @property
    def is_on(self) -> bool:
        return getattr(self, "_attr_is_on", False)

    async def async_turn_on(self, **kwargs):  # pragma: no cover - overridden by entities
        raise NotImplementedError

    async def async_turn_off(self, **kwargs):  # pragma: no cover - overridden by entities
        raise NotImplementedError

    @property
    def state(self) -> str:
        return "on" if self.is_on else "off"

    def async_write_ha_state(self) -> None:
        if self.hass is None or self.entity_id is None:
            return
        attrs = dict(self.extra_state_attributes or {})
        self.hass.states.async_set(self.entity_id, self.state, attrs)


__all__ = ["SwitchEntity"]
