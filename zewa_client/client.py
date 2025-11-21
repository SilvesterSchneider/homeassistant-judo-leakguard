"""Asynchronous client for the ZEWA Leakguard REST API."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Awaitable, Callable, Optional

import aiohttp
from aiohttp.typedefs import LooseHeaders

from . import models
from .hex import from_u16be, from_u32be, from_u8, to_u16be, to_u32be, to_u8

_HEX_CHARS = set("0123456789ABCDEF")


class ZewaError(Exception):
    """Base class for all client errors."""


class ZewaConnectionError(ZewaError):
    """Raised when the HTTP request cannot be completed."""


class ZewaAuthenticationError(ZewaError):
    """Raised when authentication with the device fails."""


class ZewaRateLimitError(ZewaError):
    """Raised when the device continues to respond with 429."""


class ZewaInvalidCommandError(ZewaError):
    """Raised when an invalid command path is supplied."""


class ZewaRequestError(ZewaError):
    """Raised when the device returns an unexpected HTTP error."""


class ZewaResponseError(ZewaError):
    """Raised when the device returns malformed or unexpected data."""


SleepCallable = Callable[[float], Awaitable[None]]


class ZewaClient:
    """Async client with built-in rate-limit handling and hex parsing."""

    def __init__(
        self,
        base_url: str,
        auth: aiohttp.BasicAuth,
        session: Optional[aiohttp.ClientSession] = None,
        *,
        max_attempts: int = 4,
        sleep: Optional[SleepCallable] = None,
        max_backoff: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/") or base_url
        self._auth = auth
        self._session = session or aiohttp.ClientSession()
        self._owns_session = session is None
        self._max_attempts = max_attempts
        self._initial_backoff = 2.0
        self._max_backoff = max_backoff
        self._sleep: SleepCallable = sleep or asyncio.sleep
        self._semaphore = asyncio.Semaphore(1)

    async def close(self) -> None:
        """Close the underlying session if it was created by the client."""

        if self._owns_session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "ZewaClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        await self.close()

    # ---------------------------------------------------------------------
    # Request helpers
    # ---------------------------------------------------------------------

    def _normalise_path(self, path: str) -> tuple[str, str, str]:
        if not path:
            raise ZewaInvalidCommandError("path must not be empty")
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.startswith("/api/rest/"):
            raise ZewaInvalidCommandError("path must start with /api/rest/")
        command = path[len("/api/rest/") :].upper()
        if not command:
            raise ZewaInvalidCommandError("missing command in path")
        if "?" in command:
            raise ZewaInvalidCommandError("query parameters are not supported")
        if len(command) % 2 != 0:
            raise ZewaInvalidCommandError("command must be an even number of hex characters")
        if len(command) // 2 > 80:
            raise ZewaInvalidCommandError("command exceeds maximum allowed length of 80 bytes")
        if not set(command).issubset(_HEX_CHARS):
            raise ZewaInvalidCommandError(f"command contains non-hex characters: {command}")
        opcode = command[:2]
        payload = command[2:]
        return f"/api/rest/{command}", opcode, payload

    async def _request(self, path: str, expect_len: Optional[int] = None) -> bytes:
        """Perform a GET request with retry/backoff handling."""

        normalised, opcode, payload = self._normalise_path(path)
        url = f"{self._base_url}{normalised}"

        delay = self._initial_backoff
        attempt = 0
        async with self._semaphore:
            while attempt < self._max_attempts:
                attempt += 1
                try:
                    async with self._session.get(url, auth=self._auth) as resp:
                        if resp.status == 401 or resp.status == 403:
                            raise ZewaAuthenticationError("authentication failed")
                        if resp.status == 429:
                            if attempt >= self._max_attempts:
                                raise ZewaRateLimitError(f"Rate limited on {opcode}")
                            delay = await self._handle_rate_limit(resp.headers, delay)
                            continue
                        if resp.status >= 400:
                            message = await resp.text()
                            if resp.status in (400, 500):
                                raise ZewaInvalidCommandError(
                                    f"Device rejected command {opcode} with payload {payload or '00'}"
                                )
                            raise ZewaRequestError(
                                f"Unexpected HTTP status {resp.status} for command {opcode}: {message}"
                            )
                        raw = (await resp.text()).strip()
                except aiohttp.ClientError as exc:
                    raise ZewaConnectionError(str(exc)) from exc
                except asyncio.TimeoutError as exc:
                    raise ZewaConnectionError("request timed out") from exc
                else:
                    data = self._parse_hex_payload(raw)
                    if expect_len is not None and len(data) != expect_len:
                        raise ZewaResponseError(
                            f"Expected {expect_len} bytes for {opcode}, got {len(data)}"
                        )
                    return data
        raise ZewaRateLimitError(f"Exceeded retry attempts for {opcode}")

    async def _handle_rate_limit(self, headers: LooseHeaders, delay: float) -> float:
        wait_time = max(delay, self._initial_backoff)
        retry_after = headers.get("Retry-After") if headers else None
        if retry_after:
            try:
                wait_time = max(wait_time, float(retry_after))
            except (TypeError, ValueError):  # pragma: no cover - defensive
                pass
        await self._sleep(wait_time)
        return min(wait_time * 2, self._max_backoff)

    @staticmethod
    def _parse_hex_payload(raw: str) -> bytes:
        cleaned = raw.strip().upper()
        if not cleaned:
            return b""
        if len(cleaned) % 2 != 0:
            raise ZewaResponseError(f"Response has odd length: {cleaned}")
        if not set(cleaned).issubset(_HEX_CHARS):
            raise ZewaResponseError(f"Response contains non-hex characters: {cleaned}")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:  # pragma: no cover - hex validated above
            raise ZewaResponseError("Response contained invalid hex") from exc

    # ------------------------------------------------------------------
    # Core read helpers
    # ------------------------------------------------------------------

    async def get_device_type(self) -> str:
        data = await self._request("/api/rest/FF00", expect_len=1)
        code = data.hex().upper()
        info = models.DeviceInfo(code, models.DeviceType.from_hex(code))
        return info.device_type.value

    async def get_serial(self) -> int:
        data = await self._request("/api/rest/0600", expect_len=4)
        return from_u32be(data)

    async def get_fw_version(self) -> str:
        data = await self._request("/api/rest/0100", expect_len=3)
        version = models.FirmwareVersion(data[0], data[1], data[2])
        return version.as_string()

    async def get_commission_date(self) -> datetime:
        data = await self._request("/api/rest/0E00", expect_len=4)
        timestamp = from_u32be(data)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    async def get_total_water_l(self) -> int:
        data = await self._request("/api/rest/2800", expect_len=4)
        return from_u32be(data)

    # ------------------------------------------------------------------
    # Command helpers
    # ------------------------------------------------------------------

    async def ack_alarm(self) -> None:
        await self._request("/api/rest/6300", expect_len=0)

    async def close_valve(self) -> None:
        await self._request("/api/rest/5100", expect_len=0)

    async def open_valve(self) -> None:
        await self._request("/api/rest/5200", expect_len=0)

    async def sleep_start(self) -> None:
        await self._request("/api/rest/5400", expect_len=0)

    async def sleep_end(self) -> None:
        await self._request("/api/rest/5500", expect_len=0)

    async def vacation_start(self) -> None:
        await self._request("/api/rest/5700", expect_len=0)

    async def vacation_end(self) -> None:
        await self._request("/api/rest/5800", expect_len=0)

    async def micro_leak_test(self) -> None:
        await self._request("/api/rest/5C00", expect_len=0)

    async def learn_mode_start(self) -> None:
        await self._request("/api/rest/5D00", expect_len=0)

    # ------------------------------------------------------------------
    # Limits and settings
    # ------------------------------------------------------------------

    async def read_absence_limits(self) -> models.AbsenceLimits:
        data = await self._request("/api/rest/5E00", expect_len=6)
        return models.AbsenceLimits(
            from_u16be(data, 0),
            from_u16be(data, 2),
            from_u16be(data, 4),
        )

    async def write_absence_limits(self, flow_l_h: int, volume_l: int, duration_min: int) -> None:
        payload = to_u16be(flow_l_h) + to_u16be(volume_l) + to_u16be(duration_min)
        await self._request(f"/api/rest/5F00{payload.hex().upper()}", expect_len=0)

    async def write_leak_preset(
        self,
        vacation_type: int,
        max_flow_l_h: int,
        max_volume_l: int,
        max_duration_min: int,
    ) -> None:
        if vacation_type not in range(0, 4):
            raise ValueError("vacation_type must be between 0 and 3")
        payload = (
            to_u8(vacation_type)
            + to_u16be(max_flow_l_h)
            + to_u16be(max_volume_l)
            + to_u16be(max_duration_min)
        )
        await self._request(f"/api/rest/50{payload.hex().upper()}", expect_len=0)

    async def set_sleep_hours(self, hours: int) -> None:
        if hours < 1 or hours > 10:
            raise ValueError("sleep hours must be between 1 and 10")
        await self._request(f"/api/rest/53{hours:02X}", expect_len=0)

    async def get_sleep_hours(self) -> int:
        data = await self._request("/api/rest/6600", expect_len=1)
        return from_u8(data)

    async def get_learn_status(self) -> tuple[bool, int]:
        """Return whether learning is active and remaining water in litres."""

        data = await self._request("/api/rest/6400", expect_len=3)
        return bool(from_u8(data, 0)), from_u16be(data, 1)

    async def set_vacation_type(self, mode: int) -> None:
        if mode < 0 or mode > 3:
            raise ValueError("vacation type must be between 0 and 3")
        await self._request(f"/api/rest/56{mode:02X}", expect_len=0)

    async def get_vacation_type(self) -> int:
        data = await self._request("/api/rest/5600", expect_len=1)
        return from_u8(data)

    async def set_micro_leak_mode(self, mode: int) -> None:
        if mode < 0 or mode > 2:
            raise ValueError("micro leak mode must be 0, 1 or 2")
        await self._request(f"/api/rest/5B{mode:02X}", expect_len=0)

    async def get_micro_leak_mode(self) -> int:
        data = await self._request("/api/rest/6500", expect_len=1)
        return from_u8(data)

    # ------------------------------------------------------------------
    # Absence windows
    # ------------------------------------------------------------------

    def _validate_window_index(self, index: int) -> None:
        if index < 0 or index > 6:
            raise ValueError("window index must be between 0 and 6")

    async def get_absence_window(self, index: int) -> models.AbsenceWindow:
        self._validate_window_index(index)
        data = await self._request(f"/api/rest/60{index:02X}", expect_len=6)
        return models.AbsenceWindow(
            index,
            from_u8(data, 0),
            from_u8(data, 1),
            from_u8(data, 2),
            from_u8(data, 3),
            from_u8(data, 4),
            from_u8(data, 5),
        )

    async def set_absence_window(self, window: models.AbsenceWindow) -> None:
        self._validate_window_index(window.index)
        payload = bytes(
            [
                window.index,
                window.start_day,
                window.start_hour,
                window.start_minute,
                window.end_day,
                window.end_hour,
                window.end_minute,
            ]
        )
        await self._request(f"/api/rest/61{payload.hex().upper()}", expect_len=0)

    async def delete_absence_window(self, index: int) -> None:
        self._validate_window_index(index)
        await self._request(f"/api/rest/6200{index:02X}", expect_len=0)

    # ------------------------------------------------------------------
    # Clock management
    # ------------------------------------------------------------------

    async def get_clock(self) -> models.DeviceClock:
        data = await self._request("/api/rest/5900", expect_len=6)
        year_short = from_u8(data, 2)
        year = 2000 + year_short if year_short < 200 else year_short
        return models.DeviceClock(
            from_u8(data, 0),
            from_u8(data, 1),
            year,
            from_u8(data, 3),
            from_u8(data, 4),
            from_u8(data, 5),
        )

    async def set_clock(self, dt: datetime) -> None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        payload = bytes(
            [
                dt.day,
                dt.month,
                dt.year % 100,
                dt.hour,
                dt.minute,
                dt.second,
            ]
        )
        await self._request(f"/api/rest/5A{payload.hex().upper()}", expect_len=0)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_day_stats(self, day: int | date | datetime) -> models.DayStats:
        key = self._coerce_day_key(day)
        payload = to_u32be(key).hex().upper()
        data = await self._request(f"/api/rest/FB{payload}")
        values = tuple(from_u32be(data, offset) for offset in range(0, len(data), 4))
        if len(values) != 8:
            raise ZewaResponseError("expected eight values for day statistics")
        return models.DayStats(key, values)

    async def get_week_stats(self, week: int, year: int) -> models.WeekStats:
        if week < 1 or week > 53:
            raise ValueError("week must be between 1 and 53")
        payload = (to_u8(week) + to_u16be(year)).hex().upper()
        data = await self._request(f"/api/rest/FC{payload}")
        values = tuple(from_u32be(data, offset) for offset in range(0, len(data), 4))
        if len(values) != 7:
            raise ZewaResponseError("expected seven values for week statistics")
        return models.WeekStats(week, year, values)

    async def get_month_stats(self, month: int, year: int) -> models.MonthStats:
        if month < 1 or month > 12:
            raise ValueError("month must be between 1 and 12")
        payload = (to_u8(month) + to_u16be(year)).hex().upper()
        data = await self._request(f"/api/rest/FD{payload}")
        if len(data) % 4 != 0:
            raise ZewaResponseError("expected multiples of four bytes for month statistics")
        values = tuple(from_u32be(data, offset) for offset in range(0, len(data), 4))
        if not 0 < len(values) <= 31:
            raise ZewaResponseError("expected between 1 and 31 entries for month statistics")
        return models.MonthStats(month, year, values)

    async def get_year_stats(self, year: int) -> models.YearStats:
        payload = to_u16be(year).hex().upper()
        data = await self._request(f"/api/rest/FE{payload}")
        values = tuple(from_u32be(data, offset) for offset in range(0, len(data), 4))
        if len(values) != 12:
            raise ZewaResponseError("expected twelve values for year statistics")
        return models.YearStats(year, values)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_day_key(day: int | date | datetime) -> int:
        if isinstance(day, int):
            return day
        if isinstance(day, datetime):
            dt = day.astimezone(timezone.utc)
        else:
            dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        return int(dt.timestamp())


__all__ = [
    "ZewaClient",
    "ZewaError",
    "ZewaAuthenticationError",
    "ZewaConnectionError",
    "ZewaInvalidCommandError",
    "ZewaRateLimitError",
    "ZewaRequestError",
    "ZewaResponseError",
]
