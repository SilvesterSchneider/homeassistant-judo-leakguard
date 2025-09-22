from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

import aiohttp
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)


class JudoApiError(Exception):
    """Base exception for Judo API errors."""


class JudoAuthenticationError(JudoApiError):
    """Raised when authentication fails."""


class JudoConnectionError(JudoApiError):
    """Raised when the device cannot be reached."""


class JudoClient:
    """Low-level REST client for the ZEWA i-SAFE / Judo Leakguard device."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, verify_ssl: bool = True, request_timeout: float = 5.0) -> None:
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self._session = session
        self._base_url = base_url
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base_url}{path}"

    async def _fetch_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON; gibt None bei 404/Fehlern zurück, ohne Exceptions nach außen zu werfen."""
        url = self._url(path)
        try:
            async with self._session.get(url, timeout=self._timeout, ssl=self._verify_ssl) as resp:
                if resp.status == 404:
                    return None
                if resp.status in (401, 403):
                    raise JudoAuthenticationError(
                        f"Authentication failed for {url} (status={resp.status})"
                    )
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
                resp.raise_for_status()
                text = await resp.text()
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
            _LOGGER.debug("REST command %s failed: %s", url, exc)
            return {}
        except aiohttp.ClientError as exc:
            raise JudoConnectionError(f"Client error while requesting {url}: {exc}") from exc
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug("REST command %s raised %s", url, exc)
            return {}

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
        await self._rest_request(0x53, bytes([value]))

    async def read_sleep_duration(self) -> Optional[int]:
        data = await self._rest_bytes(0x66, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def read_absence_limits(self) -> Optional[tuple[int, int, int]]:
        data = await self._rest_bytes(0x5E, allow_empty=True)
        if len(data) < 6:
            return None
        flow = int.from_bytes(data[0:2], "little", signed=False)
        volume = int.from_bytes(data[2:4], "little", signed=False)
        duration = int.from_bytes(data[4:6], "little", signed=False)
        return flow, volume, duration

    async def write_absence_limits(self, flow: int, volume: int, duration: int) -> None:
        payload = (
            max(0, min(int(flow), 0xFFFF)).to_bytes(2, "little")
            + max(0, min(int(volume), 0xFFFF)).to_bytes(2, "little")
            + max(0, min(int(duration), 0xFFFF)).to_bytes(2, "little")
        )
        await self._rest_request(0x5F, payload)

    async def write_leak_settings(
        self,
        vacation_type: int,
        flow: int,
        volume: int,
        duration: int,
    ) -> None:
        payload = bytes([max(0, min(int(vacation_type), 3))])
        payload += max(0, min(int(flow), 0xFFFF)).to_bytes(2, "little")
        payload += max(0, min(int(volume), 0xFFFF)).to_bytes(2, "little")
        payload += max(0, min(int(duration), 0xFFFF)).to_bytes(2, "little")
        await self._rest_request(0x50, payload)

    async def write_vacation_type(self, mode: int) -> None:
        value = max(0, min(int(mode), 3))
        await self._rest_request(0x56, bytes([value]))

    async def read_vacation_type(self) -> Optional[int]:
        data = await self._rest_bytes(0x56, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def write_microleak_mode(self, mode: int) -> None:
        value = max(0, min(int(mode), 2))
        await self._rest_request(0x5B, bytes([value]))

    async def read_microleak_mode(self) -> Optional[int]:
        data = await self._rest_bytes(0x65, allow_empty=True)
        if not data:
            return None
        return int(data[0])

    async def read_learn_status(self) -> Dict[str, Any]:
        data = await self._rest_bytes(0x64, allow_empty=True)
        if not data:
            return {}
        result: Dict[str, Any] = {
            "learn_active": bool(data[0]),
        }
        if len(data) >= 3:
            remaining_l = int.from_bytes(data[1:3], "little", signed=False)
            result["learn_remaining_l"] = remaining_l
            result["learn_remaining_m3"] = remaining_l / 1000.0
        return result

    async def read_device_time(self) -> Dict[str, Any]:
        data = await self._rest_bytes(0x59, allow_empty=True)
        if len(data) != 6:
            return {}
        day, month, year, hour, minute, second = [int(x) for x in data]
        year_full = year + 2000 if year < 200 else year
        try:
            dt = datetime(year_full, max(month, 1), max(day, 1), hour, minute, second)
        except ValueError:
            dt = None
        result: Dict[str, Any] = {
            "device_time_day": day,
            "device_time_month": month,
            "device_time_year": year_full,
            "device_time_hour": hour,
            "device_time_minute": minute,
            "device_time_second": second,
        }
        if dt is not None:
            result["device_time"] = dt.isoformat()
            result["device_time_datetime"] = dt
        return result

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
        value = int.from_bytes(data[:4], "little", signed=False)
        return str(value)

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

    async def read_installation_timestamp(self) -> Dict[str, Any]:
        data = await self._rest_bytes(0x0E, allow_empty=True)
        if len(data) < 4:
            return {}
        timestamp = int.from_bytes(data[:4], "big", signed=False)
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return {
            "installation_timestamp": timestamp,
            "installation_datetime": dt,
        }

    async def read_total_water(self) -> Dict[str, Any]:
        data = await self._rest_bytes(0x28, allow_empty=True)
        if len(data) < 4:
            return {}
        total_l = int.from_bytes(data[:4], "little", signed=False)
        return {
            "total_water_l": total_l,
            "total_water_m3": total_l / 1000.0,
        }

    async def read_absence_time(self, slot: int) -> Dict[str, Any]:
        payload = bytes([max(0, min(int(slot), 6))])
        data = await self._rest_bytes(0x60, payload, allow_empty=True)
        if len(data) != 6:
            return {}
        return {
            "slot": slot,
            "start_day": int(data[0]),
            "start_hour": int(data[1]),
            "start_minute": int(data[2]),
            "end_day": int(data[3]),
            "end_hour": int(data[4]),
            "end_minute": int(data[5]),
        }

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
        payload = bytes([
            max(1, min(int(day), 31)),
            max(1, min(int(month), 12)),
        ]) + int(year).to_bytes(2, "little", signed=False)
        data = await self._rest_bytes(0xFB, payload, allow_empty=True)
        return [int.from_bytes(data[i : i + 4], "little", signed=False) for i in range(0, len(data), 4)]

    async def read_week_stats(self, week: int, year: int) -> list[int]:
        payload = bytes([max(1, min(int(week), 53))]) + int(year).to_bytes(2, "little", signed=False)
        data = await self._rest_bytes(0xFC, payload, allow_empty=True)
        return [int.from_bytes(data[i : i + 4], "little", signed=False) for i in range(0, len(data), 4)]

    async def read_month_stats(self, month: int, year: int) -> list[int]:
        payload = bytes([max(1, min(int(month), 12))]) + int(year).to_bytes(2, "little", signed=False)
        data = await self._rest_bytes(0xFD, payload, allow_empty=True)
        return [int.from_bytes(data[i : i + 4], "little", signed=False) for i in range(0, len(data), 4)]

    async def read_year_stats(self, year: int) -> list[int]:
        payload = int(year).to_bytes(2, "little", signed=False)
        data = await self._rest_bytes(0xFE, payload, allow_empty=True)
        return [int.from_bytes(data[i : i + 4], "little", signed=False) for i in range(0, len(data), 4)]


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
                flow, volume, duration = absence
                data["absence_flow_l_h"] = flow
                data["absence_volume_l"] = volume
                data["absence_duration_min"] = duration
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
            if learn:
                data.update(learn)
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read learn status: %s", exc)

        try:
            device_time = await self.read_device_time()
            if device_time:
                data.update(device_time)
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read device time: %s", exc)

        try:
            device_type = await self.read_device_type()
            if device_type is not None:
                data["device_type"] = device_type
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
            if installation:
                data.update(installation)
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read installation timestamp: %s", exc)

        try:
            total = await self.read_total_water()
            if total:
                data.update(total)
        except (JudoAuthenticationError, JudoConnectionError):
            raise
        except JudoApiError as exc:
            _LOGGER.debug("Failed to read total water: %s", exc)

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
