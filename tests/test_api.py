"""Tests for helpers exposed by :mod:`custom_components.judo_leakguard.api`."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from custom_components.judo_leakguard.api import (
    AbsenceLimits,
    AbsenceWindow,
    DeviceClock,
    InstallationInfo,
    JudoApiError,
    JudoAuthenticationError,
    JudoClient,
    JudoConnectionError,
    JudoLeakguardApi,
    LearnStatus,
    TotalWater,
)
from custom_components.judo_leakguard.helpers import toU16BE, toU32BE
from tests.helpers import (
    MockClientSession,
    ResponseSpec,
    make_client_connector_error,
)


def test_format_command_and_encode_payload() -> None:
    """Verify helpers for encoding REST commands and payloads."""

    assert JudoClient._format_command(0x12) == "1200"
    assert JudoClient._format_command(0x1234) == "1234"
    assert JudoClient._format_command(" ab cd ") == "ABCD"
    assert JudoClient._format_command("aa") == "AA00"
    with pytest.raises(ValueError):
        JudoClient._format_command(0x10000)
    with pytest.raises(TypeError):
        JudoClient._format_command(3.14)

    assert JudoClient._encode_payload(None) == ""
    assert JudoClient._encode_payload(b"\x01\x02") == "0102"
    assert JudoClient._encode_payload(" 0a 1b ") == "0A1B"
    assert JudoClient._encode_payload([1, 255, 16]) == "01FF10"
    with pytest.raises(ValueError):
        JudoClient._encode_payload(["oops"])  # type: ignore[list-item]


def test_parse_and_extract_helpers() -> None:
    """The lightweight parsers should handle multiple input forms."""

    assert JudoClient._parse_rest_text("{\"value\": 1}") == {"value": 1}
    assert JudoClient._parse_rest_text("data=abcd") == {"data": "abcd"}
    assert JudoClient._parse_rest_text("foo=1&bar=2") == {"foo": "1", "bar": "2"}
    assert JudoClient._parse_rest_text("") == {}
    assert JudoClient._parse_rest_text("something") == {"raw": "something"}

    payload = {"data": [1, 2, 3]}
    assert JudoClient._extract_data_field(payload) == "010203"
    payload = {"Value": "A1B2"}
    assert JudoClient._extract_data_field(payload) == "A1B2"
    payload = {"raw": "CAFEBABE"}
    assert JudoClient._extract_data_field(payload) == "CAFEBABE"
    assert JudoClient._extract_data_field({}) is None


@pytest.mark.asyncio
async def test_handle_rate_limit_respects_retry_after(bypass_throttle: list[float]) -> None:
    """Rate-limit handling should honour Retry-After headers."""

    async with MockClientSession() as session:
        client = JudoClient(session, "https://example")
        next_delay = await client._handle_rate_limit(
            "https://example/path",
            attempt=1,
            delay=1.0,
            headers={"Retry-After": "3"},
        )

    assert bypass_throttle == [3.0]
    assert next_delay == 6.0


@pytest.mark.asyncio
async def test_handle_rate_limit_with_invalid_header(bypass_throttle: list[float]) -> None:
    """Invalid Retry-After headers should be ignored gracefully."""

    async with MockClientSession() as session:
        client = JudoClient(session, "https://example")
        next_delay = await client._handle_rate_limit(
            "https://example/path",
            attempt=2,
            delay=4.0,
            headers={"Retry-After": "invalid"},
        )

    assert bypass_throttle == [4.0]
    assert next_delay == 8.0


@pytest.mark.asyncio
async def test_rest_request_retries_on_rate_limit(bypass_throttle: list[float]) -> None:
    """The client should retry after rate-limit responses."""

    responses = {
        "https://example/api/rest/5300": [
            ResponseSpec(status=429, headers={"Retry-After": "1"}),
            ResponseSpec(status=200, body="{\"ok\": true}"),
        ]
    }
    async with MockClientSession(responses) as session:
        client = JudoClient(session, "https://example", verify_ssl=False)
        payload = await client._rest_request(0x53)

    assert payload["_url"].endswith("/api/rest/5300")
    assert payload["ok"] is True
    delays = [delay for delay in bypass_throttle if delay > 0]
    assert delays == [2.0]


@pytest.mark.asyncio
async def test_rest_request_handles_errors() -> None:
    """Error responses should be converted into API exceptions."""

    async with MockClientSession(
        {"https://example/api/rest/0000": [ResponseSpec(status=404)]}
    ) as session:
        client = JudoClient(session, "https://example")
        result = await client._rest_request(0x00)
    assert result == {}

    async with MockClientSession(
        {"https://example/api/rest/5300": [ResponseSpec(status=401)]}
    ) as session:
        client = JudoClient(session, "https://example")
        with pytest.raises(JudoAuthenticationError):
            await client._rest_request(0x53)

    async with MockClientSession(
        {"https://example/api/rest/5300": [ResponseSpec(status=500)]}
    ) as session:
        client = JudoClient(session, "https://example")
        result = await client._rest_request(0x53)
    assert result == {}

    long_payload = bytes(range(81))
    async with MockClientSession() as session:
        client = JudoClient(session, "https://example")
        with pytest.raises(JudoApiError):
            await client._rest_request(0x10, long_payload)


@pytest.mark.asyncio
async def test_rest_bytes_handles_hex_payloads() -> None:
    """_rest_bytes should decode hexadecimal payloads or raise errors."""

    async with MockClientSession() as session:
        client = JudoClient(session, "https://example")

        async def fake_request(command: int, payload: bytes | None) -> dict[str, str]:
            return {"data": "0A0B"}

        client._rest_request = AsyncMock(side_effect=fake_request)
        data = await client._rest_bytes(0x10)
        assert data == b"\x0a\x0b"

        client._rest_request = AsyncMock(return_value={})
        assert await client._rest_bytes(0x10, allow_empty=True) == b""

        client._rest_request = AsyncMock(return_value={"data": "zz"})
        with pytest.raises(JudoApiError):
            await client._rest_bytes(0x10)


def test_deep_merge_merges_nested_dicts() -> None:
    left = {"a": 1, "nested": {"b": 2}}
    right = {"nested": {"c": 3}, "d": 4}
    assert JudoLeakguardApi._deep_merge(left, right) == {"a": 1, "nested": {"b": 2, "c": 3}, "d": 4}


def test_device_clock_and_dataclasses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dataclass helpers should provide deterministic conversions."""

    from custom_components.judo_leakguard import api as api_module

    class DummyZone:
        def __init__(self) -> None:
            self.calls: list[datetime] = []

        def localize(self, dt_obj: datetime) -> datetime:
            self.calls.append(dt_obj)
            return dt_obj.replace(tzinfo=timezone.utc)

    dummy_tz = DummyZone()
    monkeypatch.setattr(api_module, "DEFAULT_TIME_ZONE", dummy_tz)

    clock = DeviceClock(day=2, month=3, year=2024, hour=5, minute=6, second=7)
    localized = clock.as_datetime()
    assert localized.tzinfo == timezone.utc
    assert dummy_tz.calls
    info = clock.to_dict()
    assert info["device_time_day"] == 2
    assert "device_time" in info

    invalid_clock = DeviceClock(day=1, month=13, year=2024, hour=0, minute=0, second=0)
    assert invalid_clock.as_datetime() is None

    install = InstallationInfo(1_600_000_000)
    install_dict = install.to_dict()
    assert install_dict["installation_timestamp"] == 1_600_000_000
    assert install_dict["installation_datetime"].tzinfo == timezone.utc

    total = TotalWater(2500)
    assert total.to_dict()["total_water_m3"] == pytest.approx(2.5)

    window = AbsenceWindow(1, 2, 3, 4, 5, 6, 7)
    assert window.to_dict()["end_hour"] == 6


@pytest.mark.asyncio
async def test_normalize_converts_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """_normalize should coerce types and compute derived metrics."""

    async with MockClientSession() as session:
        api = JudoLeakguardApi(session, "https://example")

        reference = datetime(2024, 1, 1, 0, 0, 10, tzinfo=timezone.utc)
        monkeypatch.setattr("custom_components.judo_leakguard.api.utcnow", lambda: reference)

        assert api._normalize({}) == {}

        data = {
            "pressure": "3.5",
            "flow": "1.25",
            "temperature": "20.0",
            "total_water_l": 2000,
            "battery": "50",
            "meta": {"manufacturer": "JUDO", "model": "Leakguard", "serial": "SN"},
            "timestamp": reference.timestamp() - 5,
            "firmware": "1.2.3",
        }

        normalized = api._normalize(data)
        assert normalized["pressure_bar"] == 3.5
        assert normalized["water_flow_l_min"] == 1.25
        assert normalized["temperature_c"] == 20.0
        assert normalized["total_water_m3"] == pytest.approx(2.0)
        assert normalized["battery_percent"] == 50.0
        assert normalized["manufacturer"] == "JUDO"
        assert normalized["model"] == "Leakguard"
        assert normalized["serial"] == "SN"
        assert normalized["firmware"] == "1.2.3"
    assert normalized["last_update_seconds"] == 5


@pytest.mark.asyncio
async def test_client_url_generation() -> None:
    async with MockClientSession() as session:
        client = JudoClient(session, "https://example/")
        assert client._base_url == "https://example"
        assert client._url("path") == "https://example/path"
        assert client._url("/status") == "https://example/status"


@pytest.mark.asyncio
async def test_collect_rest_data_gathers_information() -> None:
    """_collect_rest_data should aggregate readings and handle errors."""

    async with MockClientSession() as session:
        api = JudoLeakguardApi(session, "https://example")

        api.read_sleep_duration = AsyncMock(return_value=7)
        api.read_absence_limits = AsyncMock(return_value=AbsenceLimits(1, 2, 3))
        api.read_microleak_mode = AsyncMock(side_effect=JudoApiError("oops"))
        api.read_vacation_type = AsyncMock(return_value=2)
        api.read_learn_status = AsyncMock(return_value=LearnStatus(True, 120))
        api.read_device_time = AsyncMock(
            return_value=DeviceClock(day=1, month=1, year=2024, hour=12, minute=0, second=0)
        )
        api.read_device_type = AsyncMock(return_value=0x44)
        api.read_serial_number = AsyncMock(return_value="SERIAL")
        api.read_firmware_version = AsyncMock(return_value="3.2.1")
        installation_dt = datetime(2023, 8, 12, tzinfo=timezone.utc)
        api.read_installation_timestamp = AsyncMock(return_value=InstallationInfo(int(installation_dt.timestamp())))
        api.read_total_water = AsyncMock(return_value=TotalWater(3210))
        api.read_day_stats = AsyncMock(return_value=[1, 2, 3])
        api.read_week_stats = AsyncMock(return_value=[4, 5])
        api.read_month_stats = AsyncMock(return_value=[6, 7])
        api.read_year_stats = AsyncMock(return_value=[8, 9])

        data = await api._collect_rest_data()

    assert data["sleep_hours"] == 7
    assert data["absence_volume_l"] == 2
    assert "microleak_mode" not in data
    assert data["vacation_type"] == 2
    assert data["learn_active"] is True
    assert data["device_type_label"] == "ZEWA i-SAFE"
    assert data["serial"] == "SERIAL"
    assert data["firmware"] == "3.2.1"
    assert data["installation_timestamp"] == int(installation_dt.timestamp())
    assert data["daily_usage_l"] == 6
    assert data["weekly_usage_l"] == 9
    assert data["monthly_usage_l"] == 13
    assert data["yearly_usage_l"] == 17


@pytest.mark.asyncio
async def test_fetch_json_error_handling(
    bypass_throttle: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    """_fetch_json should cope with a variety of error responses."""

    async with MockClientSession(
        {"https://example/status": [ResponseSpec(status=404)]}
    ) as session:
        client = JudoClient(session, "https://example")
        assert await client._fetch_json("/status") is None

    async with MockClientSession(
        {"https://example/status": [ResponseSpec(status=200, body="not-json")]}
    ) as session:
        client = JudoClient(session, "https://example")
        assert await client._fetch_json("/status") is None

    async with MockClientSession(
        {"https://example/status": [ResponseSpec(status=401)]}
    ) as session:
        client = JudoClient(session, "https://example")
        with pytest.raises(JudoAuthenticationError):
            await client._fetch_json("/status")

    async with MockClientSession(
        {
            "https://example/status": [
                ResponseSpec(status=429, headers={"Retry-After": "1"}),
                ResponseSpec(status=200, body='{"ok": true}'),
            ]
        }
    ) as session:
        client = JudoClient(session, "https://example")
        payload = await client._fetch_json("/status")
        assert payload == {"ok": True}
    assert any(delay >= 2.0 for delay in bypass_throttle)
    bypass_throttle.clear()

    async with MockClientSession(
        {"https://example/status": [ResponseSpec(status=500)]}
    ) as session:
        client = JudoClient(session, "https://example")
        assert await client._fetch_json("/status") is None

    async with MockClientSession() as session:
        client = JudoClient(session, "https://example")

        def raise_connector(*_: object, **__: object):
            raise make_client_connector_error("boom")

        monkeypatch.setattr(client._session, "get", raise_connector)
        with pytest.raises(JudoConnectionError):
            await client._fetch_json("/status")

    async with MockClientSession() as session:
        client = JudoClient(session, "https://example")

        class FailingContext:
            async def __aenter__(self):
                raise RuntimeError("failure")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(client._session, "get", lambda *args, **kwargs: FailingContext())
        assert await client._fetch_json("/status") is None


@pytest.mark.asyncio
async def test_fetch_all_merges_all_sources() -> None:
    """fetch_all should merge REST data with JSON endpoints."""

    async with MockClientSession() as session:
        api = JudoLeakguardApi(session, "https://example")

        responses = {
            "/api/device": {"model": "Leakguard"},
            "/api/status": {"sensors": {"pressure_bar": "4.2"}},
            "/api/counters": {"total_water_l": 4000},
        }

        async def fake_fetch_json(path: str):
            return responses.get(path)

        api._fetch_json = fake_fetch_json  # type: ignore[assignment]
        api._collect_rest_data = AsyncMock(return_value={"sleep_hours": 6})

        result = await api.fetch_all()

    assert result["pressure_bar"] == 4.2
    assert result["total_water_m3"] == 4.0
    assert result["sleep_hours"] == 6
    assert result["model"] == "Leakguard"


@pytest.mark.asyncio
async def test_fetch_all_returns_empty_when_no_sources() -> None:
    """If no endpoints return payloads the API should yield an empty dict."""

    async with MockClientSession() as session:
        api = JudoLeakguardApi(session, "https://example")
        api._fetch_json = AsyncMock(return_value=None)
        api._collect_rest_data = AsyncMock(return_value={})
        result = await api.fetch_all()

    assert result == {}


@pytest.mark.asyncio
async def test_read_write_methods_cover_branches() -> None:
    """Exercise individual read and write helpers in the API client."""

    async with MockClientSession() as session:
        api = JudoLeakguardApi(session, "https://example")
        api._rest_request = AsyncMock()
        api._rest_bytes = AsyncMock(return_value=b"")

        await api.action_no_payload("AA")
        await api.write_sleep_duration(25)
        await api.write_absence_limits(1, 2, 3)
        await api.write_leak_settings(4, 5, 6, 7)
        await api.write_vacation_type(99)
        await api.write_microleak_mode(7)
        await api.write_absence_time(10, 11, 12, 13, 14, 15, 16)
        await api.delete_absence_time(9)

        assert await api.read_sleep_duration() is None
        api._rest_bytes.return_value = b"\x05"
        assert await api.read_sleep_duration() == 5

        api._rest_bytes.return_value = b"\x00"
        assert await api.read_absence_limits() is None
        api._rest_bytes.return_value = toU16BE(1) + toU16BE(2) + toU16BE(3)
        limits = await api.read_absence_limits()
        assert limits == AbsenceLimits(1, 2, 3)

        api._rest_bytes.return_value = b""
        assert await api.read_learn_status() is None
        api._rest_bytes.return_value = b"\x01\x00\x05"
        status = await api.read_learn_status()
        assert status == LearnStatus(True, 5)

        api._rest_bytes.return_value = b""
        assert await api.read_device_time() is None
        api._rest_bytes.return_value = bytes([1, 2, 30, 4, 5, 6])
        clock = await api.read_device_time()
        assert isinstance(clock, DeviceClock)

        api._rest_bytes.return_value = b""
        assert await api.read_device_type() is None
        api._rest_bytes.return_value = b"\x44"
        assert await api.read_device_type() == 0x44

        api._rest_bytes.return_value = b"\x00"
        assert await api.read_serial_number() is None
        api._rest_bytes.return_value = bytes.fromhex("ABCD1234")
        assert await api.read_serial_number() == "ABCD1234"

        api._rest_bytes.return_value = b"\x41\x02\x03"
        assert await api.read_firmware_version() == "3.2A"
        api._rest_bytes.return_value = b"\x01\x02"
        assert await api.read_firmware_version() == "2.1"
        api._rest_bytes.return_value = b"\x05"
        assert await api.read_firmware_version() == "5"
        api._rest_bytes.return_value = b""
        assert await api.read_firmware_version() is None

        api._rest_bytes.return_value = b"\x00\x00\x00"
        assert await api.read_installation_timestamp() is None
        api._rest_bytes.return_value = toU32BE(1234)
        install = await api.read_installation_timestamp()
        assert install == InstallationInfo(1234)

        api._rest_bytes.return_value = b"\x00\x00\x00"
        assert await api.read_total_water() is None
        api._rest_bytes.return_value = toU32BE(4321)
        total = await api.read_total_water()
        assert total == TotalWater(4321)

        api._rest_bytes.return_value = b""
        assert await api.read_absence_time(0) is None
        api._rest_bytes.return_value = bytes([1, 2, 3, 4, 5, 6])
        absence = await api.read_absence_time(8)
        assert isinstance(absence, AbsenceWindow)

        api._rest_bytes.return_value = toU32BE(1) + toU32BE(2)
        assert await api.read_day_stats(1, 1, 2024) == [1, 2]
        api._rest_bytes.return_value = toU32BE(3) + toU32BE(4)
        assert await api.read_week_stats(2, 2024) == [3, 4]
        api._rest_bytes.return_value = toU32BE(5) + toU32BE(6)
        assert await api.read_month_stats(13, 2024) == [5, 6]
        api._rest_bytes.return_value = toU32BE(7) + toU32BE(8)
        assert await api.read_year_stats(2024) == [7, 8]
