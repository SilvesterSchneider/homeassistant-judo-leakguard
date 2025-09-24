"""aiohttp test utilities stub for offline environments.

This module provides minimal stand-ins that satisfy ``pytest-aiohttp``'s
imports without requiring the real :mod:`aiohttp` test helpers.  The
implementations only record arguments and create simple placeholders so
that the rest of the test-suite can run when the actual dependency is not
available.  None of the helpers talk to the network; instead they raise a
``RuntimeError`` if advanced functionality is requested.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Any, Iterator

__all__ = [
    "BaseTestServer",
    "RawTestServer",
    "TestClient",
    "TestServer",
    "loop_context",
    "unused_port",
]


class _UnsupportedOperation(RuntimeError):
    """Raised when the stub cannot emulate the requested behaviour."""


class BaseTestServer:
    """Very small placeholder emulating :class:`aiohttp.test_utils.BaseTestServer`."""

    def __init__(self, app: Any = None, *, loop: asyncio.AbstractEventLoop | None = None, **kwargs: Any) -> None:
        self.app = app
        self.loop = loop or asyncio.get_event_loop()
        self.kwargs = kwargs
        self.started = False

    async def start_server(self, *args: Any, **kwargs: Any) -> "BaseTestServer":
        """Pretend to start the server without binding to a socket."""

        self.started = True
        return self

    async def close(self) -> None:
        """Mark the server as stopped."""

        self.started = False

    async def __aenter__(self) -> "BaseTestServer":
        await self.start_server()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def make_url(self, path: str) -> str:
        """Return the path unchanged.

        The real helper produces a full URL based on the listening socket.
        For our tests the exact value is irrelevant, so echo the path.
        """

        return path


class RawTestServer(BaseTestServer):
    """Alias used by :mod:`pytest-aiohttp` for raw TCP servers."""


class TestServer(BaseTestServer):
    """HTTP server wrapper used by :mod:`pytest-aiohttp`."""


class TestClient:
    """Lightweight replacement for :class:`aiohttp.test_utils.TestClient`."""

    def __init__(self, server: Any, *, loop: asyncio.AbstractEventLoop | None = None, **kwargs: Any) -> None:
        self.server = server
        self.loop = loop or asyncio.get_event_loop()
        self.kwargs = kwargs
        self.closed = False

    async def start_server(self) -> "TestClient":
        """Pretend to start the underlying server."""

        return self

    async def close(self) -> None:
        self.closed = True

    async def __aenter__(self) -> "TestClient":
        return await self.start_server()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def __getattr__(self, name: str) -> Any:
        raise _UnsupportedOperation(
            f"aiohttp.test_utils.TestClient stub does not implement attribute {name!r}."
        )


@contextlib.contextmanager
def loop_context(loop: asyncio.AbstractEventLoop | None = None) -> Iterator[asyncio.AbstractEventLoop]:
    """Provide a very small stand-in for :func:`aiohttp.test_utils.loop_context`."""

    created = loop is None
    if created:
        loop = asyncio.new_event_loop()
    try:
        assert loop is not None
        yield loop
    finally:
        if created:
            loop.close()


def unused_port() -> int:
    """Return an available TCP port number."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _unsupported_async(*args: Any, **kwargs: Any) -> None:
    raise _UnsupportedOperation("aiohttp.test_utils stub cannot perform network operations.")


# expose placeholders for attributes that :mod:`pytest-aiohttp` may import
TestServer.start = _unsupported_async  # type: ignore[assignment]
RawTestServer.start = _unsupported_async  # type: ignore[assignment]
