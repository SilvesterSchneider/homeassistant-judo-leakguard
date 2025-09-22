from __future__ import annotations

import asyncio

import aiohttp
import pytest

from zewa_client.client import ZewaClient


@pytest.fixture
def http_session() -> aiohttp.ClientSession:
    session = aiohttp.ClientSession()
    yield session
    asyncio.run(session.close())


@pytest.fixture
def client(http_session: aiohttp.ClientSession) -> ZewaClient:
    client = ZewaClient("http://device", aiohttp.BasicAuth("user", "pass"), session=http_session)
    yield client
    asyncio.run(client.close())


@pytest.fixture
def run_async():
    def _run(coro):
        return asyncio.run(coro)

    return _run
