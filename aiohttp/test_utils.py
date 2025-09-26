"""Lightweight aiohttp test utilities stub used during unit tests."""

from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Callable, Generator, Optional

__all__ = [
    "AioHTTPTestCase",
    "BaseTestServer",
    "RawTestServer",
    "TestClient",
    "TestServer",
    "loop_context",
    "setup_test_loop",
    "teardown_test_loop",
    "unused_port",
    "unused_tcp_port",
    "unused_tcp_port_factory",
    "unittest_run_loop",
]


def _get_loop(loop: Optional[asyncio.AbstractEventLoop]) -> asyncio.AbstractEventLoop:
    if loop is not None:
        return loop
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop_policy().get_event_loop()


class BaseTestServer:
    """Placeholder server implementation compatible with pytest-aiohttp."""

    def __init__(self, app: Optional[object] = None, *, loop: Optional[asyncio.AbstractEventLoop] = None, **kwargs: object) -> None:
        self.app = app
        self.loop = _get_loop(loop)

    async def start_server(self) -> "BaseTestServer":
        return self

    async def close(self) -> None:  # pragma: no cover - no-op cleanup
        return None


class TestServer(BaseTestServer):
    """Alias placeholder used by the plugin."""


class RawTestServer(BaseTestServer):
    """Alias placeholder used by the plugin."""


class TestClient:
    """Very small async context manager matching aiohttp.test_utils API."""

    def __init__(
        self,
        app: Optional[object] = None,
        *,
        server: Optional[TestServer] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs: object,
    ) -> None:
        self.app = app
        self.server = server or (TestServer(app, loop=loop, **kwargs) if app is not None else None)
        self.loop = _get_loop(loop)

    async def close(self) -> None:  # pragma: no cover - no-op cleanup
        return None

    async def __aenter__(self) -> "TestClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
        return None


def setup_test_loop(loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.AbstractEventLoop:
    loop = loop or asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def teardown_test_loop(loop: asyncio.AbstractEventLoop) -> None:
    if loop.is_closed():  # pragma: no cover - defensive guard
        return
    try:
        pending = asyncio.all_tasks(loop)
    except RuntimeError:
        pending = set()
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())
    asyncio.set_event_loop(None)
    loop.close()


@contextlib.contextmanager
def loop_context(loop_factory: Optional[Callable[[], asyncio.AbstractEventLoop]] = None) -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = setup_test_loop(loop_factory() if loop_factory else None)
    try:
        yield loop
    finally:
        teardown_test_loop(loop)


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return sock.getsockname()[1]


def unused_tcp_port() -> int:
    return unused_port()


def unused_tcp_port_factory() -> Callable[[], int]:
    def factory() -> int:
        return unused_port()

    return factory


class AioHTTPTestCase:
    """Minimal shim used by libraries expecting aiohttp's unittest helpers."""

    async def get_application(self) -> object:  # pragma: no cover - compatibility stub
        raise NotImplementedError

    def setUp(self) -> None:
        self.loop = setup_test_loop()

    def tearDown(self) -> None:
        teardown_test_loop(self.loop)


def unittest_run_loop(func: Callable[..., object]) -> Callable[..., object]:
    async def wrapper(*args: object, **kwargs: object) -> object:
        return await func(*args, **kwargs)

    return wrapper

