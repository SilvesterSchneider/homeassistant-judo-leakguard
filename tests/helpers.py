"""Test helpers and fixtures for the Judo Leakguard integration."""

from __future__ import annotations

from __future__ import annotations

import asyncio
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Deque, Dict, Iterable, List, Mapping, MutableMapping

import aiohttp

SERIAL = "SN123456"
INSTALLATION_DT = datetime(2023, 8, 12, 10, 30, 45, tzinfo=timezone.utc)
DEVICE_TIME_DT = datetime(2024, 2, 1, 6, 15, 30, tzinfo=timezone.utc)


def _base_payload() -> Dict[str, Any]:
    """Return a deep copy of a representative API payload."""

    return {
        "serial": SERIAL,
        "manufacturer": "JUDO",
        "model": "Leakguard Pro",
        "firmware": "3.2.1A",
        "pressure_bar": 3.8,
        "water_flow_l_min": 12.5,
        "total_water_l": 0x12345678,
        "total_water_m3": 0x12345678 / 1000.0,
        "temperature_c": 27.5,
        "battery_percent": 88,
        "last_update_seconds": 45,
        "sleep_hours": 6,
        "sleep_active": False,
        "vacation_active": True,
        "vacation_type": 2,
        "microleak_mode": 1,
        "absence_flow_l_h": 240,
        "absence_volume_l": 120,
        "absence_duration_min": 90,
        "learn_active": True,
        "learn_remaining_l": 1500,
        "learn_remaining_m3": 1.5,
        "installation_datetime": INSTALLATION_DT,
        "installation_timestamp": int(INSTALLATION_DT.timestamp()),
        "device_time_datetime": DEVICE_TIME_DT,
        "device_time": DEVICE_TIME_DT.isoformat(),
        "device_type_code": 0x44,
        "device_type_hex": "0x44",
        "device_type_label": "ZEWA i-SAFE",
        "device_serial": SERIAL,
        "device_firmware": "3.2.1A",
        "daily_usage_l": 123,
        "weekly_usage_l": 456,
        "monthly_usage_l": 789,
        "yearly_usage_l": 1024,
        "daily_usage_m3": 0.123,
        "weekly_usage_m3": 0.456,
        "monthly_usage_m3": 0.789,
        "yearly_usage_m3": 1.024,
        "sensors": {"pressure_bar": 3.8, "temperature_c": 27.5},
        "live": {"flow": 12.5},
        "meta": {
            "serial": SERIAL,
            "firmware": "3.2.1A",
            "manufacturer": "JUDO",
            "model": "Leakguard Pro",
        },
    }


@dataclass(slots=True)
class ServiceCallRecord:
    """Simple structure capturing service interactions with the mock API."""

    slot: int
    start_day: int
    start_hour: int
    start_minute: int
    end_day: int
    end_hour: int
    end_minute: int


class MockJudoApi:
    """Replacement for :class:`JudoLeakguardApi` used during tests."""

    default_payload: Dict[str, Any] = _base_payload()
    fetch_exception: Exception | None = None

    def __init__(
        self,
        session: Any,
        base_url: str,
        *,
        verify_ssl: bool = True,
        username: str | None = None,
        password: str | None = None,
        send_as_query: bool = False,
        request_timeout: float | None = None,
    ) -> None:
        self.session = session
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.username = username
        self.password = password
        self.send_as_query = send_as_query
        self.request_timeout = request_timeout

        self.data: Dict[str, Any] = deepcopy(self.default_payload)
        self.fetch_all_calls = 0
        self.command_log: List[str] = []
        self.sleep_duration_writes: List[int] = []
        self.absence_limit_writes: List[tuple[int, int, int]] = []
        self.vacation_type_writes: List[int] = []
        self.microleak_writes: List[int] = []
        self.datetime_writes: List[datetime] = []
        self.absence_schedule_writes: List[ServiceCallRecord] = []
        self.absence_schedule_deletes: List[int] = []

    async def fetch_all(self) -> Dict[str, Any]:
        if self.fetch_exception is not None:
            raise self.fetch_exception
        self.fetch_all_calls += 1
        return deepcopy(self.data)

    async def action_no_payload(self, command: int | str) -> None:
        command_str = str(command).upper()
        self.command_log.append(command_str)
        if command_str == "5400":
            self.data["sleep_active"] = True
        elif command_str == "5500":
            self.data["sleep_active"] = False
        elif command_str == "5700":
            self.data["vacation_active"] = True
        elif command_str == "5800":
            self.data["vacation_active"] = False
        elif command_str == "5200":
            self.data["valve_open"] = True
        elif command_str == "5100":
            self.data["valve_open"] = False
        elif command_str == "5D00":
            self.data["learn_active"] = True

    async def write_sleep_duration(self, hours: int) -> None:
        value = int(hours)
        self.sleep_duration_writes.append(value)
        self.data["sleep_hours"] = value

    async def write_absence_limits(self, flow: int, volume: int, duration: int) -> None:
        values = (int(flow), int(volume), int(duration))
        self.absence_limit_writes.append(values)
        self.data["absence_flow_l_h"], self.data["absence_volume_l"], self.data["absence_duration_min"] = values

    async def write_leak_settings(self, vacation_type: int, flow: int, volume: int, duration: int) -> None:
        await self.write_vacation_type(vacation_type)
        await self.write_absence_limits(flow, volume, duration)

    async def write_vacation_type(self, mode: int) -> None:
        value = max(0, min(int(mode), 3))
        self.vacation_type_writes.append(value)
        self.data["vacation_type"] = value

    async def write_microleak_mode(self, mode: int) -> None:
        value = max(0, min(int(mode), 2))
        self.microleak_writes.append(value)
        self.data["microleak_mode"] = value

    async def write_device_time(self, dt: datetime) -> None:
        self.datetime_writes.append(dt)
        localized = dt.astimezone(timezone.utc)
        self.data["device_time_datetime"] = localized
        self.data["device_time"] = localized.isoformat()

    async def write_absence_time(
        self,
        slot: int,
        start_day: int,
        start_hour: int,
        start_minute: int,
        end_day: int,
        end_hour: int,
        end_minute: int,
    ) -> None:
        record = ServiceCallRecord(
            slot=int(slot),
            start_day=int(start_day),
            start_hour=int(start_hour),
            start_minute=int(start_minute),
            end_day=int(end_day),
            end_hour=int(end_hour),
            end_minute=int(end_minute),
        )
        self.absence_schedule_writes.append(record)

    async def delete_absence_time(self, slot: int) -> None:
        self.absence_schedule_deletes.append(int(slot))


def fresh_payload() -> Dict[str, Any]:
    """Return a copy of the base payload so tests can mutate safely."""

    return deepcopy(_base_payload())


@dataclass(slots=True)
class ResponseSpec:
    """Specification for a queued HTTP response used by :class:`MockClientSession`."""

    status: int = 200
    body: str = ""
    headers: Mapping[str, str] | None = None
    exception: Exception | None = None


def make_client_response_error(
    status: int,
    message: str = "",
    headers: Mapping[str, str] | None = None,
) -> aiohttp.ClientResponseError:
    """Create an :class:`aiohttp.ClientResponseError` compatible with all versions."""

    request_info = SimpleNamespace(real_url="http://test")
    try:
        return aiohttp.ClientResponseError(
            request_info,
            (),
            status=status,
            message=message,
            headers=headers,
        )
    except TypeError:
        # Older or stubbed aiohttp versions accept the legacy signature.
        return aiohttp.ClientResponseError(status, message or f"HTTP status {status}")


def make_client_connector_error(message: str = "boom") -> aiohttp.ClientConnectorError:
    """Create an :class:`aiohttp.ClientConnectorError` across aiohttp versions."""

    fake_key = SimpleNamespace(
        host="example.com",
        port=443,
        ssl=None,
        family=0,
        proto=0,
        flags=0,
    )
    try:
        return aiohttp.ClientConnectorError(fake_key, OSError(message))
    except TypeError:
        return aiohttp.ClientConnectorError(message)


class MockResponse:
    """Lightweight stand-in for :class:`aiohttp.ClientResponse`."""

    def __init__(
        self, status: int, body: str, headers: Mapping[str, str] | None = None
    ) -> None:
        self.status = status
        self._body = body
        self.headers = dict(headers or {})

    async def text(self) -> str:
        await asyncio.sleep(0)
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise make_client_response_error(self.status, headers=self.headers)


class _RequestContext:
    def __init__(self, spec: ResponseSpec) -> None:
        self._spec = spec

    async def __aenter__(self) -> MockResponse:
        if self._spec.exception is not None:
            raise self._spec.exception
        return MockResponse(self._spec.status, self._spec.body, self._spec.headers)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class MockClientSession:
    """Minimal HTTP client that serves pre-registered responses."""

    def __init__(
        self, responses: Mapping[str, Iterable[ResponseSpec]] | None = None
    ) -> None:
        self._responses: MutableMapping[str, Deque[ResponseSpec]] = {
            url: deque(specs)
            for url, specs in (responses or {}).items()
        }
        self.calls: list[tuple[str, Dict[str, Any]]] = []
        self.closed = False

    def queue_response(self, url: str, spec: ResponseSpec) -> None:
        self._responses.setdefault(url, deque()).append(spec)

    def get(self, url: str, **kwargs: Any) -> _RequestContext:
        self.calls.append((url, dict(kwargs)))
        if url not in self._responses or not self._responses[url]:
            raise AssertionError(f"No queued response for {url}")
        spec = self._responses[url].popleft()
        return _RequestContext(spec)

    async def close(self) -> None:
        self.closed = True

    async def __aenter__(self) -> "MockClientSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
