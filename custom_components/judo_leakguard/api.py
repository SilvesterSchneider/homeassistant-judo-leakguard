from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

import aiohttp
from homeassistant.util.dt import DEFAULT_TIME_ZONE, utcnow

from .helpers import fromU16BE, fromU32BE, toU16BE, toU32BE, toU8

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class AbsenceLimits:
    """Absence monitoring thresholds reported by the device."""

    flow_l_h: int
    volume_l: int
    duration_min: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "absence_flow_l_h": self.flow_l_h,
            "absence_volume_l": self.volume_l,
            "absence_duration_min": self.duration_min,
        }


@dataclass(slots=True, frozen=True)
class LearnStatus:
    """Status information for the learn mode."""

    active: bool
    remaining_l: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"learn_active": self.active}
        if self.remaining_l is not None:
            data["learn_remaining_l"] = self.remaining_l
            data["learn_remaining_m3"] = self.remaining_l / 1000.0
        return data


@dataclass(slots=True, frozen=True)
class DeviceClock:
    """Current device clock information."""

    day: int
    month: int
    year: int
    hour: int
    minute: int
    second: int

    def as_datetime(self) -> Optional[datetime]:
        try:
            naive = datetime(
                self.year,
                max(self.month, 1),
                max(self.day, 1),
                self.hour,
                self.minute,
                self.second,
            )
        except ValueError:
            return None
        tz = DEFAULT_TIME_ZONE
        if hasattr(tz, "localize"):
            return tz.localize(naive)  # type: ignore[attr-defined]
        return naive.replace(tzinfo=tz)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "device_time_day": self.day,
            "device_time_month": self.month,
            "device_time_year": self.year,
            "device_time_hour": self.hour,
            "device_time_minute": self.minute,
            "device_time_second": self.second,
        }
        dt = self.as_datetime()
        if dt is not None:
            data["device_time"] = dt.isoformat()
            data["device_time_datetime"] = dt
        return data


@dataclass(slots=True, frozen=True)
class InstallationInfo:
    """Installation timestamp reported by the device."""

    timestamp: int

    def as_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        dt = self.as_datetime()
        return {
            "installation_timestamp": self.timestamp,
            "installation_datetime": dt,
        }


@dataclass(slots=True, frozen=True)
class TotalWater:
    """Accumulated water usage."""

    liters: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_water_l": self.liters,
            "total_water_m3": self.liters / 1000.0,
        }


@dataclass(slots=True, frozen=True)
class AbsenceWindow:
    """Absence schedule entry."""

    slot: int
    start_day: int
    start_hour: int
    start_minute: int
    end_day: int
    end_hour: int
    end_minute: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "start_day": self.start_day,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_day": self.end_day,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
        }


class JudoApiError(Exception):
    """Base exception for Judo API errors."""


class JudoAuthenticationError(JudoApiError):
    """Raised when authentication fails."""


class JudoConnectionError(JudoApiError):
    """Raised when the device cannot be reached."""


class JudoClient:
    """Low-level REST client for the ZEWA i-SAFE / Judo Leakguard device."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        verify_ssl: bool = True,
        request_timeout: float = 5.0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        send_as_query: bool = False,
    ) -> None:
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self._session = session
        self._base_url = base_url
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)
        self._auth = aiohttp.BasicAuth(username or "", password or "") if username or password else None
        self._send_as_query = send_as_query
        self._request_lock = asyncio.Lock()
        self._max_attempts = 5
        self._initial_retry_delay = 2.0
        self._max_retry_delay = 30.0

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base_url}{path}"

    async def _fetch_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON from the device. Returns None for 404 responses."""

        url = self._url(path)
        delay = self._initial_retry_delay
        attempt = 0
        async with self._request_lock:
            while attempt < self._max_attempts:
                attempt += 1
                try:
                    async with self._session.get(
                        url,
                        timeout=self._timeout,
                        ssl=self._verify_ssl,
                        auth=self._auth,
                    ) as resp:
                        if resp.status == 404:
                            return None
                        if resp.status in (401, 403):
                            raise JudoAuthenticationError(
                                f"Authentication failed for {url} (status={resp.status})"
                            )
                        if resp.status == 429:
                            if attempt >= self._max_attempts:
                                raise JudoConnectionError(f"Rate limited on {url}")
                            delay = await self._handle_rate_limit(url, attempt, delay, resp.headers)
                            continue
                        resp.raise_for_status()
                        text = await resp.text()
                        if not text:
                            return None
                        return json.loads(text)
                except JudoAuthenticationError:
                    raise
                except asyncio.TimeoutError as exc:
                    raise JudoConnectionError(f"Timeout while requesting {url}") from exc
                except aiohttp.ClientConnectorError as exc:
                    raise JudoConnectionError(f"Cannot connect to {url}: {exc}") from exc
                except aiohttp.ClientResponseError as exc:
                    if exc.status == 404:
                        return None
                    if exc.status in (401, 403):
                        raise JudoAuthenticationError(
                            f"Authentication failed for {url} (status={exc.status})"
                        ) from exc
                    if exc.status == 429:
                        if attempt >= self._max_attempts:
                            raise JudoConnectionError(f"Rate limited on {url}") from exc
                        delay = await self._handle_rate_limit(
                            url,
                            attempt,
                            delay,
                            getattr(exc, "headers", None),
                        )
                        continue
                    _LOGGER.debug("Unexpected response from %s: %s", url, exc)
                    return None
                except aiohttp.ClientError as exc:
                    raise JudoConnectionError(f"Client error while requesting {url}: {exc}") from exc
                except json.JSONDecodeError as exc:
                    _LOGGER.debug("Invalid JSON from %s: %s", url, exc)
                    return None
                except Exception as exc:  # pylint: disable=broad-except
                    _LOGGER.debug("Fetch failed for %s: %s", url, exc)
                    return None
        raise JudoConnectionError(f"Exceeded retry budget for {url}")

    @staticmethod
    def _format_command(command: int | str) -> str:
        if isinstance(command, int):
            if 0 <= command <= 0xFF:
                return f"{command:02X}00"
            if 0 <= command <= 0xFFFF:
                return f"{command:04X}"
            raise ValueError(f"Command out of range: {command}")
        if isinstance(command, str):
            cleaned = command.strip().replace(" ", "").upper()
            if not cleaned:
                raise ValueError("Empty command string")
            if len(cleaned) == 2:
                return f"{cleaned}00"
            return cleaned
        raise TypeError(f"Unsupported command type: {type(command)}")

    @staticmethod
    def _encode_payload(payload: Optional[bytes | Sequence[int] | str]) -> str:
        if payload is None:
            return ""
        if isinstance(payload, bytes):
            return payload.hex().upper()
        if isinstance(payload, str):
            return payload.strip().replace(" ", "").upper()
        try:
            data = bytes(int(x) & 0xFF for x in payload)
            return data.hex().upper()
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"Cannot encode payload {payload}") from exc

    @staticmethod
    def _parse_rest_text(text: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        cleaned = text.strip()
        if not cleaned:
            return payload
        try:
            js = json.loads(cleaned)
            if isinstance(js, dict):
                return js
        except json.JSONDecodeError:
            pass
        if cleaned.lower().startswith("data="):
            payload["data"] = cleaned.split("=", 1)[1].strip()
            return payload
        for part in cleaned.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                payload[key.strip()] = value.strip()
        if not payload:
            payload["raw"] = cleaned
        return payload

    @staticmethod
    def _extract_data_field(payload: Dict[str, Any]) -> Optional[str]:
        for key in ("data", "Data", "DATA", "value", "Value"):
            if key in payload and payload[key] is not None:
                value = payload[key]
                if isinstance(value, list):
                    try:
                        return "".join(f"{int(v) & 0xFF:02X}" for v in value)
                    except Exception:  # pylint: disable=broad-except
                        continue
                return str(value)
        raw = payload.get("raw")
        if isinstance(raw, str):
            candidate = raw.strip()
            if all(ch in "0123456789ABCDEFabcdef" for ch in candidate) and candidate:
                return candidate
        return None

    async def _handle_rate_limit(
        self,
        url: str,
        attempt: int,
        delay: float,
        headers: Optional[Mapping[str, str]],
    ) -> float:
        """Handle 429 responses by sleeping and returning the next delay."""

        wait_time = max(delay, self._initial_retry_delay)
        if headers:
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    parsed = float(retry_after)
                    wait_time = max(wait_time, parsed)
                except ValueError:
                    _LOGGER.debug("Invalid Retry-After header '%s' from %s", retry_after, url)
        _LOGGER.debug(
            "Rate limited on %s (attempt %s/%s), waiting %.1fs",
            url,
            attempt,
            self._max_attempts,
            wait_time,
        )
        await asyncio.sleep(wait_time)
        return min(wait_time * 2, self._max_retry_delay)

    async def _rest_request(
        self,
        command: int | str,
        payload: Optional[bytes | Sequence[int] | str] = None,
    ) -> Dict[str, Any]:
        cmd_hex = self._format_command(command)
        payload_hex = self._encode_payload(payload)
        if self._send_as_query and payload_hex:
            path = f"/api/rest/{cmd_hex}?data={payload_hex}"
        else:
            path = f"/api/rest/{cmd_hex}{payload_hex}"
        url = self._url(path)
        delay = self._initial_retry_delay
        attempt = 0
        text = ""
        success = False
        async with self._request_lock:
            while attempt < self._max_attempts:
                attempt += 1
                try:
                    async with self._session.get(
                        url,
                        timeout=self._timeout,
                        ssl=self._verify_ssl,
                        auth=self._auth,
                    ) as resp:
                        if resp.status == 404:
                            return {}
                        if resp.status in (401, 403):
                            raise JudoAuthenticationError(
                                f"Authentication failed for {url} (status={resp.status})"
                            )
                        if resp.status == 429:
                            if attempt >= self._max_attempts:
                                raise JudoConnectionError(f"Rate limited on {url}")
                            delay = await self._handle_rate_limit(url, attempt, delay, resp.headers)
                            continue
                        resp.raise_for_status()
                        text = await resp.text()
                        success = True
                except JudoAuthenticationError:
                    raise
                except asyncio.TimeoutError as exc:
                    raise JudoConnectionError(f"Timeout while requesting {url}") from exc
                except aiohttp.ClientConnectorError as exc:
                    raise JudoConnectionError(f"Cannot connect to {url}: {exc}") from exc
                except aiohttp.ClientResponseError as exc:
                    if exc.status == 404:
                        return {}
                    if exc.status in (401, 403):
                        raise JudoAuthenticationError(
                            f"Authentication failed for {url} (status={exc.status})"
                        ) from exc
                    if exc.status == 429:
                        if attempt >= self._max_attempts:
                            raise JudoConnectionError(f"Rate limited on {url}") from exc
                        delay = await self._handle_rate_limit(
                            url,
                            attempt,
                            delay,
                            getattr(exc, "headers", None),
                        )
                        continue
                    _LOGGER.debug("REST command %s failed: %s", url, exc)
                    return {}
                except aiohttp.ClientError as exc:
                    raise JudoConnectionError(f"Client error while requesting {url}: {exc}") from exc
                except Exception as exc:  # pylint: disable=broad-except
                    _LOGGER.debug("REST command %s raised %s", url, exc)
                    return {}
                if success:
                    break
        if not success:
            raise JudoConnectionError(f"Exceeded retry budget for {url}")

        if not text:
            return {}
        parsed = self._parse_rest_text(text)
        parsed.setdefault("_url", url)
        return parsed

    async def _rest_bytes(
        self,
        command: int | str,
        payload: Optional[bytes | Sequence[int] | str] = None,
        *,
        allow_empty: bool = False,
    ) -> bytes:
        response = await self._rest_request(command, payload)
        data_hex = self._extract_data_field(response)
        if not data_hex:
            if allow_empty:
                return b""
            raise JudoApiError(f"No data returned for command {command}")
        cleaned = data_hex.strip().replace(" ", "")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise JudoApiError(f"Invalid hex payload for command {command}: {cleaned}") from exc

    async def action_no_payload(self, command: int | str) -> None:
        await self._rest_request(command, None)

    async def write_sleep_duration(self, hours: int) -> None:
        value = max(1, min(int(hours), 10))
        await self._rest_request(0x53, toU8(value))

    async def read_sleep_duration(self) -> Optional[int]:
        data = await self._rest_bytes(0x66, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def read_absence_limits(self) -> Optional[AbsenceLimits]:
        data = await self._rest_bytes(0x5E, allow_empty=True)
        if len(data) < 6:
            return None
        flow = fromU16BE(data, 0)
        volume = fromU16BE(data, 2)
        duration = fromU16BE(data, 4)
        return AbsenceLimits(flow, volume, duration)

    async def write_absence_limits(self, flow: int, volume: int, duration: int) -> None:
        payload = toU16BE(flow) + toU16BE(volume) + toU16BE(duration)
        await self._rest_request(0x5F, payload)

    async def write_leak_settings(
        self,
        vacation_type: int,
        flow: int,
        volume: int,
        duration: int,
    ) -> None:
        payload = toU8(max(0, min(int(vacation_type), 3)))
        payload += toU16BE(flow)
        payload += toU16BE(volume)
        payload += toU16BE(duration)
        await self._rest_request(0x50, payload)

    async def write_vacation_type(self, mode: int) -> None:
        value = max(0, min(int(mode), 3))
        await self._rest_request(0x56, toU8(value))

    async def read_vacation_type(self) -> Optional[int]:
        data = await self._rest_bytes(0x56, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def write_microleak_mode(self, mode: int) -> None:
        value = max(0, min(int(mode), 2))
        await self._rest_request(0x5B, toU8(value))

    async def read_microleak_mode(self) -> Optional[int]:
        data = await self._rest_bytes(0x65, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def read_learn_status(self) -> Optional[LearnStatus]:
        data = await self._rest_bytes(0x64, allow_empty=True)
        if not data:
            return None
        remaining: Optional[int] = None
        if len(data) >= 3:
            remaining = fromU16BE(data, 1)
        return LearnStatus(bool(data[0]), remaining)

    async def read_device_time(self) -> Optional[DeviceClock]:
        data = await self._rest_bytes(0x59, allow_empty=True)
        if len(data) != 6:
            return None
        day, month, year_short, hour, minute, second = [int(x) for x in data]
        year_full = year_short + 2000 if year_short < 200 else year_short
        return DeviceClock(day, month, year_full, hour, minute, second)

    async def write_device_time(self, dt: datetime) -> None:
        payload = bytes(
            [
                dt.day & 0xFF,
                dt.month & 0xFF,
                (dt.year % 100) & 0xFF,
                dt.hour & 0xFF,
                dt.minute & 0xFF,
                dt.second & 0xFF,
            ]
        )
        await self._rest_request(0x5A, payload)

    async def read_device_type(self) -> Optional[int]:
        data = await self._rest_bytes(0xFF, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def read_serial_number(self) -> Optional[str]:
        data = await self._rest_bytes(0x06, allow_empty=True)
        if len(data) < 4:
            return None
        return data[:4].hex().upper()

    async def read_firmware_version(self) -> Optional[str]:
        data = await self._rest_bytes(0x01, allow_empty=True)
        if len(data) >= 3:
            major = int(data[2])
            minor = int(data[1])
            suffix = data[0]
            if 32 <= suffix < 127:
                suffix_str = chr(suffix)
            else:
                suffix_str = f"{suffix:02X}"
            return f"{major}.{minor}{suffix_str}"
        if len(data) == 2:
            major = int(data[1])
            minor = int(data[0])
            return f"{major}.{minor}"
        if len(data) == 1:
            return str(int(data[0]))
        return None

    async def read_installation_timestamp(self) -> Optional[InstallationInfo]:
        data = await self._rest_bytes(0x0E, allow_empty=True)
        if len(data) < 4:
            return None
        timestamp = fromU32BE(data, 0)
        return InstallationInfo(timestamp)

    async def read_total_water(self) -> Optional[TotalWater]:
        data = await self._rest_bytes(0x28, allow_empty=True)
        if len(data) < 4:
            return None
        total_l = fromU32BE(data, 0)
        return TotalWater(total_l)

    async def read_absence_time(self, slot: int) -> Optional[AbsenceWindow]:
        slot_idx = max(0, min(int(slot), 6))
        payload = bytes([slot_idx])
        data = await self._rest_bytes(0x60, payload, allow_empty=True)
        if len(data) != 6:
            return None
        return AbsenceWindow(
            slot=slot_idx,
            start_day=int(data[0]),
            start_hour=int(data[1]),
            start_minute=int(data[2]),
            end_day=int(data[3]),
            end_hour=int(data[4]),
            end_minute=int(data[5]),
        )

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
        payload = bytes(
            [
                max(0, min(int(slot), 6)),
                max(0, min(int(start_day), 6)),
                max(0, min(int(start_hour), 23)),
                max(0, min(int(start_minute), 59)),
                max(0, min(int(end_day), 6)),
                max(0, min(int(end_hour), 23)),
                max(0, min(int(end_minute), 59)),
            ]
        )
        await self._rest_request(0x61, payload)

    async def delete_absence_time(self, slot: int) -> None:
        payload = bytes([max(0, min(int(slot), 6))])
        await self._rest_request(0x62, payload)

    async def read_day_stats(self, day: int, month: int, year: int) -> list[int]:
        payload = toU8(max(1, min(int(day), 31)))
        payload += toU8(max(1, min(int(month), 12)))
        payload += toU16BE(year)
        data = await self._rest_bytes(0xFB, payload, allow_empty=True)
        values: list[int] = []
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                values.append(fromU32BE(data, i))
        return values

    async def read_week_stats(self, week: int, year: int) -> list[int]:
        payload = toU8(max(1, min(int(week), 53))) + toU16BE(year)
        data = await self._rest_bytes(0xFC, payload, allow_empty=True)
        values: list[int] = []
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                values.append(fromU32BE(data, i))
        return values

    async def read_month_stats(self, month: int, year: int) -> list[int]:
        payload = toU8(max(1, min(int(month), 12))) + toU16BE(year)
        data = await self._rest_bytes(0xFD, payload, allow_empty=True)
        values: list[int] = []
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                values.append(fromU32BE(data, i))
        return values

    async def read_year_stats(self, year: int) -> list[int]:
        payload = toU16BE(year)
        data = await self._rest_bytes(0xFE, payload, allow_empty=True)
        values: list[int] = []
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                values.append(fromU32BE(data, i))
        return values


DEVICE_TYPE_NAMES: Dict[int, str] = {
    0x44: "ZEWA i-SAFE",
}


class JudoLeakguardApi(JudoClient):
    """High-level API that also fetches JSON endpoints for sensor data."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        verify_ssl: bool = True,
        request_timeout: float = 5.0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        send_as_query: bool = False,
    ) -> None:
        super().__init__(
            session=session,
            base_url=base_url,
            verify_ssl=verify_ssl,
            request_timeout=request_timeout,
            username=username,
            password=password,
            send_as_query=send_as_query,
        )
        self._status_candidates = [
            "/api/status",
            "/api/live",
            "/api/values",
            "/status",
            "/live",
            "/values",
            "/zewa/status",
            "/zewa/live",
            "/judo/leakguard/status",
        ]
        self._meta_candidates = [
            "/api/device",
            "/device",
            "/api/info",
            "/info",
        ]
        self._counter_candidates = [
            "/api/counters",
            "/counters",
        ]
    @staticmethod
    def _deep_merge(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(left)
        for key, value in (right or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = JudoLeakguardApi._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return data
        norm = dict(data)

        pressure = (
            norm.get("pressure_bar")
            or norm.get("pressure")
            or norm.get("sensors", {}).get("pressure_bar")
            or norm.get("live", {}).get("pressure_bar")
        )
        if pressure is not None:
            try:
                pressure_f = float(pressure)
                if 0 <= pressure_f < 20:
                    norm["pressure_bar"] = pressure_f
            except Exception:  # pylint: disable=broad-except
                pass

        flow = (
            norm.get("water_flow_l_min")
            or norm.get("flow_l_min")
            or norm.get("flow")
            or norm.get("sensors", {}).get("flow")
            or norm.get("live", {}).get("flow")
        )
        if flow is not None:
            try:
                flow_f = float(flow)
                if flow_f >= 0:
                    norm["water_flow_l_min"] = flow_f
            except Exception:  # pylint: disable=broad-except
                pass

        temp = (
            norm.get("temperature_c")
            or norm.get("temp_c")
            or norm.get("temperature")
            or norm.get("sensors", {}).get("temperature_c")
        )
        if temp is not None:
            try:
                norm["temperature_c"] = float(temp)
            except Exception:  # pylint: disable=broad-except
                pass

        total_m3 = norm.get("total_water_m3") or norm.get("counters", {}).get("total_water_m3")
        if total_m3 is None:
            total_l = norm.get("total_water_l") or norm.get("counters", {}).get("total_water_l")
            try:
                if total_l is not None:
                    norm["total_water_m3"] = float(total_l) / 1000.0
            except Exception:  # pylint: disable=broad-except
                pass

        bat = norm.get("battery_percent") or norm.get("battery") or norm.get("status", {}).get("battery_percent")
        if bat is not None:
            try:
                bat_f = float(bat)
                if 0 <= bat_f <= 100:
                    norm["battery_percent"] = bat_f
            except Exception:  # pylint: disable=broad-except
                pass

        manufacturer = norm.get("manufacturer") or norm.get("brand") or norm.get("meta", {}).get("manufacturer")
        if manufacturer:
            norm["manufacturer"] = manufacturer

        model = norm.get("model") or norm.get("device", {}).get("model") or norm.get("meta", {}).get("model")
        if model:
            norm["model"] = model

        serial = norm.get("serial") or norm.get("device", {}).get("serial") or norm.get("meta", {}).get("serial")
        if serial:
            norm["serial"] = serial

        fw = norm.get("firmware") or norm.get("sw_version") or norm.get("meta", {}).get("firmware")
        if fw:
            norm["firmware"] = fw

        ts = norm.get("last_update") or norm.get("meta", {}).get("last_update") or norm.get("timestamp")
        age = None
        try:
            now = utcnow().timestamp()
            if isinstance(ts, (int, float)) and ts > 1e12:
                age = now - (ts / 1000.0)
            elif isinstance(ts, (int, float)) and ts > 0:
                age = now - ts
            elif isinstance(ts, str):
                dt_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age = now - dt_obj.timestamp()
        except Exception:  # pylint: disable=broad-except
            age = None

        if age is not None and age >= 0:
            norm["last_update_seconds"] = round(age)

        return norm

    async def _collect_rest_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        try:
            sleep_hours = await self.read_sleep_duration()
            if sleep_hours is not None:
                data["sleep_hours"] = sleep_hours
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read sleep duration: %s", exc)

        try:
            absence = await self.read_absence_limits()
            if absence is not None:
                data.update(absence.to_dict())
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read absence limits: %s", exc)

        try:
            micro = await self.read_microleak_mode()
            if micro is not None:
                data["microleak_mode"] = micro
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read micro-leak mode: %s", exc)

        try:
            vacation_type = await self.read_vacation_type()
            if vacation_type is not None:
                data["vacation_type"] = vacation_type
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read vacation type: %s", exc)

        try:
            learn = await self.read_learn_status()
            if learn is not None:
                data.update(learn.to_dict())
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read learn status: %s", exc)

        device_clock: Optional[DeviceClock] = None
        try:
            device_time = await self.read_device_time()
            if device_time is not None:
                device_clock = device_time
                data.update(device_time.to_dict())
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read device time: %s", exc)

        try:
            device_type = await self.read_device_type()
            if device_type is not None:
                code_hex = f"0x{device_type:02X}"
                label = DEVICE_TYPE_NAMES.get(device_type, code_hex)
                data["device_type_code"] = device_type
                data["device_type_hex"] = code_hex
                data["device_type_label"] = label
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read device type: %s", exc)

        try:
            serial = await self.read_serial_number()
            if serial:
                data["serial"] = serial
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read serial number: %s", exc)

        try:
            firmware = await self.read_firmware_version()
            if firmware:
                data["firmware"] = firmware
                data["sw_version"] = firmware
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read firmware version: %s", exc)

        try:
            installation = await self.read_installation_timestamp()
            if installation is not None:
                data.update(installation.to_dict())
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read installation timestamp: %s", exc)

        try:
            total = await self.read_total_water()
            if total is not None:
                data.update(total.to_dict())
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read total water: %s", exc)

        reference_dt: datetime | None = None
        if device_clock is not None:
            reference_dt = device_clock.as_datetime()
        if reference_dt is None:
            reference_dt = utcnow()

        try:
            day_values = await self.read_day_stats(reference_dt.day, reference_dt.month, reference_dt.year)
            if day_values:
                day_total = sum(day_values)
                data["daily_usage_l"] = day_total
                data["daily_usage_m3"] = day_total / 1000.0
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read daily statistics: %s", exc)

        try:
            iso = reference_dt.isocalendar()
            week_year = getattr(iso, "year", iso[0])
            week_no = getattr(iso, "week", iso[1])
            week_values = await self.read_week_stats(week_no, week_year)
            if week_values:
                week_total = sum(week_values)
                data["weekly_usage_l"] = week_total
                data["weekly_usage_m3"] = week_total / 1000.0
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read weekly statistics: %s", exc)

        try:
            month_values = await self.read_month_stats(reference_dt.month, reference_dt.year)
            if month_values:
                month_total = sum(month_values)
                data["monthly_usage_l"] = month_total
                data["monthly_usage_m3"] = month_total / 1000.0
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read monthly statistics: %s", exc)

        try:
            year_values = await self.read_year_stats(reference_dt.year)
            if year_values:
                year_total = sum(year_values)
                data["yearly_usage_l"] = year_total
                data["yearly_usage_m3"] = year_total / 1000.0
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read yearly statistics: %s", exc)

        return data

    async def fetch_all(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}

        for endpoint in self._meta_candidates:
            js = await self._fetch_json(endpoint)
            if js:
                merged = self._deep_merge(merged, {"meta": js})

        for endpoint in self._status_candidates:
            js = await self._fetch_json(endpoint)
            if js:
                merged = self._deep_merge(merged, js)

        for endpoint in self._counter_candidates:
            js = await self._fetch_json(endpoint)
            if js:
                merged = self._deep_merge(merged, {"counters": js})

        rest_data = await self._collect_rest_data()
        if rest_data:
            merged = self._deep_merge(merged, rest_data)

        if not merged:
            _LOGGER.debug("No payload collected from any endpoint at %s", self._base_url)
            return {}

        normalized = self._normalize(merged)
        normalized.update(rest_data)
        _LOGGER.debug("Fetched payload keys: %s", list(normalized.keys()))
        return normalized
