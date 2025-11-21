from __future__ import annotations

from datetime import datetime, timezone

import pytest

from zewa_client.client import (
    ZewaAuthenticationError,
    ZewaClient,
    ZewaRateLimitError,
    ZewaResponseError,
)
from zewa_client import hex as hexutils
from zewa_client import models


class DummyResponse:
    def __init__(self, status: int, text: str, headers: dict | None = None):
        self.status = status
        self._text = text
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return self._text


class DummySession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.closed = False

    def get(self, url, auth=None):
        return self.responses.pop(0)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_request_success():
    session = DummySession([DummyResponse(200, "0A0B")])
    client = ZewaClient("http://host", auth=None, session=session)  # type: ignore[arg-type]
    data = await client._request("/api/rest/AA00", expect_len=2)
    assert data == b"\x0a\x0b"


@pytest.mark.asyncio
async def test_request_auth_error():
    session = DummySession([DummyResponse(401, "")])
    client = ZewaClient("http://host", auth=None, session=session)  # type: ignore[arg-type]
    with pytest.raises(ZewaAuthenticationError):
        await client._request("/api/rest/AA00")


@pytest.mark.asyncio
async def test_rate_limit_retry():
    responses = [DummyResponse(429, "", {"Retry-After": "0"}), DummyResponse(200, "01")]
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    session = DummySession(responses)
    client = ZewaClient("http://host", auth=None, session=session, max_attempts=2, sleep=fake_sleep)  # type: ignore[arg-type]
    data = await client._request("/api/rest/AA00", expect_len=1)
    assert data == b"\x01"
    assert sleep_calls


@pytest.mark.asyncio
async def test_parse_error():
    session = DummySession([DummyResponse(200, "XYZ")])
    client = ZewaClient("http://host", auth=None, session=session)  # type: ignore[arg-type]
    with pytest.raises(ZewaResponseError):
        await client._request("/api/rest/AA00")


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    session = DummySession([DummyResponse(429, "", {}), DummyResponse(429, "", {})])
    client = ZewaClient("http://host", auth=None, session=session, max_attempts=2)  # type: ignore[arg-type]
    with pytest.raises(ZewaRateLimitError):
        await client._request("/api/rest/AA00")


def test_hex_helpers():
    assert hexutils.to_u8(5) == b"\x05"
    assert hexutils.to_u16be(5) == b"\x00\x05"
    assert hexutils.to_u32be(5) == b"\x00\x00\x00\x05"
    with pytest.raises(ValueError):
        hexutils.to_u8(300)
    assert hexutils.from_u8(b"\x01") == 1
    assert hexutils.from_u16be(b"\x00\x02") == 2
    assert hexutils.from_u32be(b"\x00\x00\x00\x03") == 3


def test_models():
    assert models.DeviceType.from_hex("44") == models.DeviceType.ZEWA_I_SAFE
    assert models.FirmwareVersion(1, 2, 3).as_string() == "01.02.03"
    clock = models.DeviceClock(1, 1, 2024, 0, 0, 0)
    assert clock.as_datetime().year == 2024
