from __future__ import annotations

import pytest

from custom_components.judo_leakguard.api import JudoApiError, JudoClient
from tests.helpers import MockClientSession, ResponseSpec


@pytest.mark.asyncio
async def test_fetch_json_rate_limit_backoff(bypass_throttle) -> None:
    async with MockClientSession(
        {
            "http://device/api/status": [
                ResponseSpec(status=429, headers={"Retry-After": "3"}),
                ResponseSpec(status=200, body="{\"ok\": true}"),
            ]
        }
    ) as session:
        client = JudoClient(session, "http://device")
        data = await client._fetch_json("/api/status")
    assert data == {"ok": True}
    assert bypass_throttle and bypass_throttle[0] >= 2


@pytest.mark.asyncio
async def test_rest_request_rate_limit_backoff(bypass_throttle) -> None:
    async with MockClientSession(
        {
            "http://device/api/rest/5100": [
                ResponseSpec(status=429, headers={"Retry-After": "2"}),
                ResponseSpec(status=200, body="raw=ABCD"),
            ]
        }
    ) as session:
        client = JudoClient(session, "http://device")
        payload = await client._rest_request("5100")
    assert payload["raw"] == "ABCD"
    assert bypass_throttle and bypass_throttle[0] >= 2


@pytest.mark.asyncio
async def test_fetch_json_handles_server_error() -> None:
    async with MockClientSession(
        {"http://device/api/status": [ResponseSpec(status=500, body="boom")]}
    ) as session:
        client = JudoClient(session, "http://device")
        data = await client._fetch_json("/api/status")
    assert data is None


@pytest.mark.asyncio
async def test_rest_request_handles_server_error() -> None:
    async with MockClientSession(
        {"http://device/api/rest/5200": [ResponseSpec(status=500, body="fail")]}
    ) as session:
        client = JudoClient(session, "http://device")
        payload = await client._rest_request("5200")
    assert payload == {}


@pytest.mark.asyncio
async def test_rest_request_validates_payload_length(caplog) -> None:
    async with MockClientSession() as session:
        client = JudoClient(session, "http://device")
        too_long = bytes(range(0, 90))
        with pytest.raises(JudoApiError):
            await client._rest_request("5000", too_long)
    assert "exceeds 80 bytes" in caplog.text
