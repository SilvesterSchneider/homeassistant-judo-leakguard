"""Simplified aiohttp client helper."""

from __future__ import annotations

from typing import Optional

import aiohttp


def async_get_clientsession(hass) -> aiohttp.ClientSession:
    """Return the shared :class:`aiohttp.ClientSession` for the test harness."""

    session: Optional[aiohttp.ClientSession] = hass.data.get("_aiohttp_session")
    if session is None or getattr(session, "closed", False):
        session = aiohttp.ClientSession()
        hass.data["_aiohttp_session"] = session
    return session


__all__ = ["async_get_clientsession"]
