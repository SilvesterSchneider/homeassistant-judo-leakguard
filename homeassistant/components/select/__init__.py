"""Minimal select entity."""

from __future__ import annotations

from typing import List, Optional

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.entity import Entity


class SelectEntity(Entity):
    _attr_options: List[str] = []
    _attr_current_option: Optional[str] = None

    @property
    def options(self) -> List[str]:
        return list(getattr(self, "_attr_options", []))

    @property
    def current_option(self) -> Optional[str]:
        return getattr(self, "_attr_current_option", None)

    async def async_select_option(self, option: str) -> None:  # pragma: no cover
        raise NotImplementedError

    @property
    def state(self) -> str:
        return self.current_option or STATE_UNKNOWN

    def async_write_ha_state(self) -> None:
        if self.hass is None or self.entity_id is None:
            return
        attrs = dict(self.extra_state_attributes or {})
        attrs["options"] = self.options
        self.hass.states.async_set(self.entity_id, self.state, attrs)


__all__ = ["SelectEntity"]
