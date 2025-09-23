"""Common testing helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry


class MockConfigEntry(ConfigEntry):
    """Drop-in replacement for the real helper used in Home Assistant tests."""

    def __init__(
        self,
        *,
        domain: str,
        data: Optional[Dict[str, Any]] = None,
        title: str = "Mock Entry",
        options: Optional[Dict[str, Any]] = None,
        unique_id: Optional[str] = None,
        entry_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            domain=domain,
            title=title,
            data=dict(data or {}),
            options=dict(options or {}),
            entry_id=entry_id or uuid4().hex,
            unique_id=unique_id,
        )


__all__ = ["MockConfigEntry"]
