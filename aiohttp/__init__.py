"""Lightweight aiohttp test stub used for offline unit tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .typedefs import LooseHeaders

__all__ = [
    "BasicAuth",
    "ClientError",
    "ClientConnectorError",
    "ClientResponseError",
    "ClientSession",
    "ClientTimeout",
    "register_mocker",
]


class ClientError(Exception):
    """Base error to mirror aiohttp.ClientError."""


class ClientConnectorError(ClientError):
    """Raised when a connection cannot be established."""


class ClientResponseError(ClientError):
    """Error raised for HTTP responses with error status codes."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(message or f"HTTP status {status}")
        self.status = status


@dataclass
class BasicAuth:
    """Minimal basic authentication container."""

    login: str
    password: str


@dataclass
class ClientTimeout:
    """Timeout placeholder used for compatibility."""

    total: Optional[float] = None


class _MockResponse:
    def __init__(self, status: int, body: str, headers: Optional[LooseHeaders] = None) -> None:
        self.status = status
        self._body = body
        self.headers = headers or {}

    async def text(self) -> str:
        await asyncio.sleep(0)
        return self._body

    async def __aenter__(self) -> "_MockResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@dataclass
class _MockSpec:
    status: int
    body: str
    headers: LooseHeaders


class _MockRegistry:
    def __init__(self) -> None:
        self._mocker: Optional["AioResponses"] = None

    def set(self, mocker: Optional["AioResponses"]) -> None:
        self._mocker = mocker

    def get(self) -> Optional["AioResponses"]:
        return self._mocker


_registry = _MockRegistry()


def register_mocker(mocker: Optional["AioResponses"]) -> None:
    """Register the active aioresponses mocker."""

    _registry.set(mocker)


class ClientSession:
    """Simplified in-memory HTTP client."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - compatibility
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def close(self) -> None:
        self._closed = True

    def get(self, url: str, **kwargs: Any) -> "_ResponseContext":
        mocker = _registry.get()
        if mocker is None:
            raise ClientConnectorError(f"No mock registered for GET {url}")
        spec = mocker._pop("GET", url)
        mocker._record("GET", url, kwargs)
        return _ResponseContext(spec)


class _ResponseContext:
    def __init__(self, spec: _MockSpec) -> None:
        self._spec = spec

    async def __aenter__(self) -> _MockResponse:
        return _MockResponse(self._spec.status, self._spec.body, self._spec.headers)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None
