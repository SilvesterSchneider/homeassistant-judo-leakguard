from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.judo_leakguard.api import (
    AbsenceLimits,
    AbsenceWindow,
    DeviceClock,
    InstallationInfo,
    JudoApiError,
    JudoClient,
    LearnStatus,
    TotalWater,
)


class DummyResponse:
    def __init__(
        self,
        status: int = 200,
        body: str = "",
        raise_error: Exception | None = None,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._body = body
        self._raise_error = raise_error
        self.headers = headers or {}

    async def __aenter__(self) -> "DummyResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def text(self) -> str:
        return self._body

    def raise_for_status(self) -> None:
        if self._raise_error:
            raise self._raise_error
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
                message="error",
                headers={},
            )


class DummySession:
    def __init__(self) -> None:
        self.calls: deque[tuple[str, Dict[str, Any]]] = deque()
        self._responses: deque[DummyResponse] = deque()

    def queue(self, response: DummyResponse) -> None:
        self._responses.append(response)

    def get(self, url: str, **kwargs: Any) -> DummyResponse:
        self.calls.append((url, kwargs))
        if not self._responses:
            raise AssertionError("No queued response available")
        return self._responses.popleft()


@pytest.fixture
def dummy_session() -> DummySession:
    return DummySession()


def make_client(session: DummySession, **kwargs: Any) -> JudoClient:
    return JudoClient(session=session, base_url="http://device", **kwargs)


def test_format_command_variants():
    assert JudoClient._format_command(0x5A) == "5A00"
    assert JudoClient._format_command(0x1234) == "1234"
    assert JudoClient._format_command("5a") == "5A00"
    assert JudoClient._format_command("5a00") == "5A00"


@pytest.mark.parametrize("value", [-1, 0x10000])
def test_format_command_invalid_int(value):
    with pytest.raises(ValueError):
        JudoClient._format_command(value)


@pytest.mark.parametrize("value", [None, 1.2])
def test_format_command_invalid_type(value):
    with pytest.raises(TypeError):
        JudoClient._format_command(value)  # type: ignore[arg-type]


def test_encode_payload_variants():
    assert JudoClient._encode_payload(None) == ""
    assert JudoClient._encode_payload(b"\x01\x02") == "0102"
    assert JudoClient._encode_payload("01 02 ") == "0102"
    assert JudoClient._encode_payload([1, 255, 16]) == "01FF10"


def test_encode_payload_invalid_sequence():
    with pytest.raises(ValueError):
        JudoClient._encode_payload(["oops"])  # type: ignore[list-item]


def test_parse_rest_text_handles_variants():
    payload = JudoClient._parse_rest_text("{\"foo\": 1}")
    assert payload == {"foo": 1}

    payload = JudoClient._parse_rest_text("data=AB12")
    assert payload == {"data": "AB12"}

    payload = JudoClient._parse_rest_text("key=value&other=1")
    assert payload == {"key": "value", "other": "1"}

    payload = JudoClient._parse_rest_text("0A0B")
    assert payload == {"raw": "0A0B"}


def test_extract_data_field_prefers_named_keys():
    assert JudoClient._extract_data_field({"data": "AB"}) == "AB"
    assert JudoClient._extract_data_field({"Data": "CD"}) == "CD"
    assert JudoClient._extract_data_field({"value": [1, 2, 255]}) == "0102FF"


def test_extract_data_field_from_raw_hex():
    assert JudoClient._extract_data_field({"raw": "A1B2"}) == "A1B2"
    assert JudoClient._extract_data_field({"raw": "invalid"}) is None


@pytest.mark.asyncio
async def test_rest_request_builds_url(dummy_session: DummySession):
    dummy_session.queue(DummyResponse(status=200, body="data=0001"))
    client = make_client(dummy_session)
    result = await client._rest_request(0x52, b"\x00\x01")
    url, kwargs = dummy_session.calls.popleft()
    assert url == "http://device/api/rest/52000001"
    assert kwargs["timeout"] is not None
    assert result["data"] == "0001"
    assert result["_url"] == url


@pytest.mark.asyncio
async def test_rest_request_as_query(dummy_session: DummySession):
    dummy_session.queue(DummyResponse(status=200, body="data=AA"))
    client = make_client(dummy_session, send_as_query=True)
    await client._rest_request("52", "AA")
    url, _ = dummy_session.calls.popleft()
    assert url.endswith("/api/rest/5200?data=AA")


@pytest.mark.asyncio
async def test_rest_request_handles_404(dummy_session: DummySession):
    dummy_session.queue(DummyResponse(status=404, body=""))
    client = make_client(dummy_session)
    result = await client._rest_request(0x52)
    assert result == {}


@pytest.mark.asyncio
async def test_rest_request_retries_on_429(monkeypatch, dummy_session: DummySession):
    dummy_session.queue(DummyResponse(status=429, body="", headers={"Retry-After": "1"}))
    dummy_session.queue(DummyResponse(status=200, body="data=AA"))
    client = make_client(dummy_session)
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    sleep_mock = AsyncMock(side_effect=fake_sleep)
    monkeypatch.setattr("custom_components.judo_leakguard.api.asyncio.sleep", sleep_mock)

    result = await client._rest_request(0x52)
    assert result["data"] == "AA"
    assert sleep_mock.await_count == 1
    assert sleep_calls[0] >= 2.0


@pytest.mark.asyncio
async def test_rest_bytes_returns_payload(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_request", AsyncMock(return_value={"data": "0102"}))
    data = await client._rest_bytes(0x10)
    assert data == b"\x01\x02"


@pytest.mark.asyncio
async def test_rest_bytes_raises_on_missing(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_request", AsyncMock(return_value={}))
    with pytest.raises(JudoApiError):
        await client._rest_bytes(0x10)


@pytest.mark.asyncio
async def test_rest_bytes_allows_empty(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_request", AsyncMock(return_value={}))
    data = await client._rest_bytes(0x10, allow_empty=True)
    assert data == b""


@pytest.mark.asyncio
async def test_write_sleep_duration_clamps(monkeypatch):
    client = make_client(DummySession())
    mock = AsyncMock()
    monkeypatch.setattr(client, "_rest_request", mock)
    await client.write_sleep_duration(99)
    mock.assert_awaited_once()
    call = mock.await_args
    assert call.args == (0x53, bytes([10]))


@pytest.mark.asyncio
async def test_write_absence_limits_serializes(monkeypatch):
    client = make_client(DummySession())
    mock = AsyncMock()
    monkeypatch.setattr(client, "_rest_request", mock)
    await client.write_absence_limits(-1, 70000, 30)
    mock.assert_awaited_once()
    call = mock.await_args
    assert call.args == (0x5F, b"\x00\x00\xff\xff\x00\x1e")


@pytest.mark.asyncio
async def test_write_vacation_type_range(monkeypatch):
    client = make_client(DummySession())
    mock = AsyncMock()
    monkeypatch.setattr(client, "_rest_request", mock)
    await client.write_vacation_type(9)
    mock.assert_awaited_once_with(0x56, b"\x03")


@pytest.mark.asyncio
async def test_read_sleep_duration_returns_int(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x07"))
    assert await client.read_sleep_duration() == 7


@pytest.mark.asyncio
async def test_read_sleep_duration_none(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b""))
    assert await client.read_sleep_duration() is None


@pytest.mark.asyncio
async def test_read_absence_limits(monkeypatch):
    client = make_client(DummySession())
    payload = b"\x00d\x00\xc8\x00\x0f"
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    limits = await client.read_absence_limits()
    assert isinstance(limits, AbsenceLimits)
    assert limits.flow_l_h == 100
    assert limits.volume_l == 200
    assert limits.duration_min == 15
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x00"))
    assert await client.read_absence_limits() is None


@pytest.mark.asyncio
async def test_write_device_time(monkeypatch):
    client = make_client(DummySession())
    mock = AsyncMock()
    monkeypatch.setattr(client, "_rest_request", mock)
    ts = datetime(2023, 5, 1, 12, 30, 45)
    await client.write_device_time(ts)
    mock.assert_awaited_once()
    call = mock.await_args
    assert call.args == (0x5A, bytes([1, 5, 23, 12, 30, 45]))


@pytest.mark.asyncio
async def test_read_device_time(monkeypatch):
    client = make_client(DummySession())
    payload = bytes([1, 2, 23, 3, 4, 5])
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    clock = await client.read_device_time()
    assert isinstance(clock, DeviceClock)
    assert clock.year == 2023
    assert clock.to_dict()["device_time_day"] == 1
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x01"))
    assert await client.read_device_time() is None


@pytest.mark.asyncio
async def test_read_device_type(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x05"))
    assert await client.read_device_type() == 5
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b""))
    assert await client.read_device_type() is None


@pytest.mark.asyncio
async def test_read_serial_number(monkeypatch):
    client = make_client(DummySession())
    serial_bytes = b"\x39\x30\x00\x00"
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=serial_bytes))
    assert await client.read_serial_number() == serial_bytes.hex().upper()
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x01\x02"))
    assert await client.read_serial_number() is None


@pytest.mark.asyncio
async def test_read_firmware_version(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x41\x02\x03"))
    assert await client.read_firmware_version() == "3.2A"
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x05\x06"))
    assert await client.read_firmware_version() == "6.5"
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x07"))
    assert await client.read_firmware_version() == "7"
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b""))
    assert await client.read_firmware_version() is None


@pytest.mark.asyncio
async def test_read_installation_timestamp(monkeypatch):
    client = make_client(DummySession())
    timestamp = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp())
    payload = timestamp.to_bytes(4, "big")
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    result = await client.read_installation_timestamp()
    assert isinstance(result, InstallationInfo)
    assert result.timestamp == timestamp
    assert result.as_datetime().year == 2022
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x01"))
    assert await client.read_installation_timestamp() is None


@pytest.mark.asyncio
async def test_read_total_water(monkeypatch):
    client = make_client(DummySession())
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=(1234).to_bytes(4, "big")))
    result = await client.read_total_water()
    assert isinstance(result, TotalWater)
    assert result.liters == 1234
    assert result.to_dict()["total_water_m3"] == pytest.approx(1.234)
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x01"))
    assert await client.read_total_water() is None


@pytest.mark.asyncio
async def test_read_learn_status(monkeypatch):
    client = make_client(DummySession())
    payload = b"\x01\x00d"
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    status = await client.read_learn_status()
    assert isinstance(status, LearnStatus)
    assert status.active is True
    assert status.remaining_l == 100
    assert status.to_dict()["learn_remaining_m3"] == pytest.approx(0.1)
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b""))
    assert await client.read_learn_status() is None


@pytest.mark.asyncio
async def test_read_absence_time(monkeypatch):
    client = make_client(DummySession())
    payload = bytes([1, 2, 30, 3, 4, 45])
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    result = await client.read_absence_time(2)
    assert isinstance(result, AbsenceWindow)
    assert result.slot == 2
    assert result.start_day == 1
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=b"\x00"))
    assert await client.read_absence_time(1) is None


@pytest.mark.asyncio
async def test_write_absence_time_and_delete(monkeypatch):
    client = make_client(DummySession())
    mock = AsyncMock()
    monkeypatch.setattr(client, "_rest_request", mock)
    await client.write_absence_time(7, -1, 30, 99, 6, 24, 61)
    first_call = mock.await_args
    assert first_call.args == (0x61, b"\x06\x00\x17\x3b\x06\x17\x3b")
    mock.reset_mock()
    await client.delete_absence_time(9)
    mock.assert_awaited_once_with(0x62, b"\x06")


@pytest.mark.asyncio
async def test_read_stats_helpers(monkeypatch):
    client = make_client(DummySession())
    payload = b"".join(i.to_bytes(4, "big") for i in range(1, 4))
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    assert await client.read_day_stats(32, 13, 2025) == [1, 2, 3]
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    assert await client.read_week_stats(99, 2025) == [1, 2, 3]
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    assert await client.read_month_stats(15, 2025) == [1, 2, 3]
    monkeypatch.setattr(client, "_rest_bytes", AsyncMock(return_value=payload))
    assert await client.read_year_stats(2025) == [1, 2, 3]

