"""REST-API-Client für JUDO ZEWA i-SAFE mit Basic Auth und Exponential Backoff."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Maximale Retries bei HTTP 429
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # Sekunden (mindestens 2 s laut Spezifikation)


# ── Hex-Hilfsfunktionen ───────────────────────────────────────────────────────

def to_u8_hex(value: int) -> str:
    """Kodiert einen Byte-Wert als 2-stelligen Hex-String."""
    return f"{value & 0xFF:02X}"


def to_u16_le_hex(value: int) -> str:
    """Kodiert einen 16-bit-Wert Little-Endian als 4-stelligen Hex-String."""
    lo = value & 0xFF
    hi = (value >> 8) & 0xFF
    return f"{lo:02X}{hi:02X}"


def to_u16_be_hex(value: int) -> str:
    """Kodiert einen 16-bit-Wert Big-Endian als 4-stelligen Hex-String."""
    hi = (value >> 8) & 0xFF
    lo = value & 0xFF
    return f"{hi:02X}{lo:02X}"


def from_u16_le(data: bytes, offset: int = 0) -> int:
    """Liest einen 16-bit-Wert Little-Endian aus einem Byte-Array."""
    return data[offset] | (data[offset + 1] << 8)


def from_u32_le(data: bytes, offset: int = 0) -> int:
    """Liest einen 32-bit-Wert Little-Endian aus einem Byte-Array."""
    return (
        data[offset]
        | (data[offset + 1] << 8)
        | (data[offset + 2] << 16)
        | (data[offset + 3] << 24)
    )


def from_u32_be(data: bytes, offset: int = 0) -> int:
    """Liest einen 32-bit-Wert Big-Endian aus einem Byte-Array."""
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3]
    )


def hex_to_bytes(hex_str: str) -> bytes:
    """Wandelt einen Hex-String in Bytes um."""
    return bytes.fromhex(hex_str)


# ── Datenmodelle ──────────────────────────────────────────────────────────────

@dataclass
class DeviceInfo:
    device_type: int
    serial_number: int
    fw_version: str
    commission_date: datetime | None


@dataclass
class DeviceStatus:
    total_water_liters: int
    sleep_hours: int
    learn_active: bool
    learning_remaining_water: int   # Liter
    microleak_mode: int             # 0=off, 1=notify, 2=notify+close
    absence_flow_limit: int         # l/h
    absence_volume_limit: int       # Liter
    absence_duration_limit: int     # Minuten
    device_datetime: datetime | None


@dataclass
class AbsenceWindow:
    index: int
    start_day: int    # 0=So..6=Sa
    start_hour: int
    start_minute: int
    stop_day: int
    stop_hour: int
    stop_minute: int


# ── API-Client ────────────────────────────────────────────────────────────────

class JudoApiError(Exception):
    """Allgemeiner API-Fehler."""


class JudoAuthError(JudoApiError):
    """Authentifizierungsfehler."""


class JudoApiClient:
    """Asynchroner REST-API-Client für JUDO ZEWA i-SAFE."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._base_url = f"http://{host}"
        self._auth = aiohttp.BasicAuth(username, password)
        self._session = session
        self._lock = asyncio.Lock()  # nur eine Anfrage gleichzeitig

    # ── Interne Hilfsmethoden ─────────────────────────────────────────────────

    async def _request(self, command: str) -> str:
        """Führt einen GET-Request gegen /api/rest/<command> aus.

        Gibt den Wert des 'data'-Felds als Hex-String zurück.
        Wiederholt die Anfrage bei HTTP 429 mit Backoff.
        """
        url = f"{self._base_url}/api/rest/{command}"
        delay = _RETRY_DELAY

        async with self._lock:
            for attempt in range(_MAX_RETRIES):
                try:
                    async with self._session.get(
                        url,
                        auth=self._auth,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 401:
                            raise JudoAuthError("Ungültige Zugangsdaten")
                        if resp.status == 429:
                            _LOGGER.warning(
                                "HTTP 429 – Retry nach %.1f s (Versuch %d/%d)",
                                delay,
                                attempt + 1,
                                _MAX_RETRIES,
                            )
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        if resp.status >= 400:
                            text = await resp.text()
                            raise JudoApiError(
                                f"HTTP {resp.status} für {url}: {text}"
                            )
                        payload: dict[str, Any] = await resp.json(
                            content_type=None
                        )
                        return payload.get("data", "")
                except aiohttp.ClientError as exc:
                    raise JudoApiError(f"Verbindungsfehler: {exc}") from exc

            raise JudoApiError(f"Maximale Retries erreicht für {url}")

    # ── Geräteinfo ────────────────────────────────────────────────────────────

    async def get_device_type(self) -> int:
        raw = await self._request("FF00")
        return int(raw, 16)

    async def get_serial_number(self) -> int:
        raw = await self._request("0600")
        b = hex_to_bytes(raw)
        return from_u32_le(b)

    async def get_fw_version(self) -> str:
        raw = await self._request("0100")
        b = hex_to_bytes(raw)
        return f"{b[2]}.{b[1]}{chr(b[0])}"

    async def get_commission_date(self) -> datetime | None:
        raw = await self._request("0E00")
        try:
            b = hex_to_bytes(raw)
            ts = from_u32_be(b)
            return datetime.utcfromtimestamp(ts)
        except Exception:
            return None

    async def get_device_info(self) -> DeviceInfo:
        device_type, serial, fw, commission = await asyncio.gather(
            self.get_device_type(),
            self.get_serial_number(),
            self.get_fw_version(),
            self.get_commission_date(),
        )
        return DeviceInfo(
            device_type=device_type,
            serial_number=serial,
            fw_version=fw,
            commission_date=commission,
        )

    # ── Betriebsstatus ────────────────────────────────────────────────────────

    async def get_total_water(self) -> int:
        """Gesamtwasser in Litern."""
        raw = await self._request("2800")
        b = hex_to_bytes(raw)
        return from_u32_le(b)

    async def get_sleep_hours(self) -> int:
        raw = await self._request("6600")
        return int(raw, 16)

    async def get_learn_status(self) -> tuple[bool, int]:
        """Gibt (aktiv, rest_liter) zurück."""
        raw = await self._request("6400")
        b = hex_to_bytes(raw)
        active = bool(b[0])
        remaining = from_u16_le(b, 1)
        return active, remaining

    async def get_microleak_mode(self) -> int:
        raw = await self._request("6500")
        return int(raw, 16)

    async def get_absence_limits(self) -> tuple[int, int, int]:
        """Gibt (flow_l_h, volume_l, duration_min) zurück."""
        raw = await self._request("5E00")
        b = hex_to_bytes(raw)
        flow = from_u16_le(b, 0)
        volume = from_u16_le(b, 2)
        duration = from_u16_le(b, 4)
        return flow, volume, duration

    async def get_device_datetime(self) -> datetime | None:
        raw = await self._request("5900")
        try:
            b = hex_to_bytes(raw)
            day, month, year, hour, minute, second = b[0], b[1], b[2], b[3], b[4], b[5]
            return datetime(2000 + year, month, day, hour, minute, second)
        except Exception:
            return None

    async def get_status(self) -> DeviceStatus:
        """Liest alle Statuswerte in parallelen Requests."""
        (
            total_water,
            sleep_hours,
            learn_status,
            microleak_mode,
            absence_limits,
            device_datetime,
        ) = await asyncio.gather(
            self.get_total_water(),
            self.get_sleep_hours(),
            self.get_learn_status(),
            self.get_microleak_mode(),
            self.get_absence_limits(),
            self.get_device_datetime(),
        )
        learn_active, learn_remaining = learn_status
        flow, volume, duration = absence_limits
        return DeviceStatus(
            total_water_liters=total_water,
            sleep_hours=sleep_hours,
            learn_active=learn_active,
            learning_remaining_water=learn_remaining,
            microleak_mode=microleak_mode,
            absence_flow_limit=flow,
            absence_volume_limit=volume,
            absence_duration_limit=duration,
            device_datetime=device_datetime,
        )

    # ── Aktoren ───────────────────────────────────────────────────────────────

    async def valve_close(self) -> None:
        await self._request("5100")

    async def valve_open(self) -> None:
        await self._request("5200")

    async def sleep_start(self) -> None:
        await self._request("5400")

    async def sleep_stop(self) -> None:
        await self._request("5500")

    async def vacation_start(self) -> None:
        await self._request("5700")

    async def vacation_stop(self) -> None:
        await self._request("5800")

    async def start_microleak_test(self) -> None:
        await self._request("5C00")

    async def start_learning(self) -> None:
        await self._request("5D00")

    async def ack_alarm(self) -> None:
        await self._request("6300")

    # ── Konfiguration ─────────────────────────────────────────────────────────

    async def set_sleep_hours(self, hours: int) -> None:
        """Setzt die Schlafdauer (1–10 h). Starten mit sleep_start()."""
        cmd = f"53{to_u8_hex(hours):0>2}00"
        await self._request(cmd)

    async def set_vacation_type(self, vtype: int) -> None:
        """Setzt den Urlaubstyp (0=aus, 1=U1, 2=U2, 3=U3)."""
        cmd = f"56{to_u8_hex(vtype):0>2}00"
        await self._request(cmd)

    async def set_microleak_mode(self, mode: int) -> None:
        """Setzt den Mikroleck-Modus (0=off, 1=notify, 2=notify+close)."""
        cmd = f"5B{to_u8_hex(mode):0>2}00"
        await self._request(cmd)

    async def set_absence_limits(
        self, flow: int, volume: int, duration: int
    ) -> None:
        """Setzt Abwesenheitslimits: flow (l/h), volume (l), duration (min)."""
        payload = (
            to_u16_le_hex(flow)
            + to_u16_le_hex(volume)
            + to_u16_le_hex(duration)
        )
        await self._request(f"5F00{payload}")

    async def set_datetime(self, dt: datetime) -> None:
        """Schreibt Datum/Zeit auf das Gerät."""
        year_offset = dt.year - 2000
        payload = (
            to_u8_hex(dt.day)
            + to_u8_hex(dt.month)
            + to_u8_hex(year_offset)
            + to_u8_hex(dt.hour)
            + to_u8_hex(dt.minute)
            + to_u8_hex(dt.second)
        )
        await self._request(f"5A00{payload}")

    # ── Abwesenheitszeitpläne ─────────────────────────────────────────────────

    async def read_absence_schedule(self, index: int) -> AbsenceWindow:
        """Liest einen Abwesenheitszeitraum (Index 0–6)."""
        raw = await self._request(f"60{to_u8_hex(index):0>2}00")
        b = hex_to_bytes(raw)
        return AbsenceWindow(
            index=index,
            start_day=b[0],
            start_hour=b[1],
            start_minute=b[2],
            stop_day=b[3],
            stop_hour=b[4],
            stop_minute=b[5],
        )

    async def write_absence_schedule(self, window: AbsenceWindow) -> None:
        """Schreibt einen Abwesenheitszeitraum."""
        payload = (
            to_u8_hex(window.index)
            + to_u8_hex(window.start_day)
            + to_u8_hex(window.start_hour)
            + to_u8_hex(window.start_minute)
            + to_u8_hex(window.stop_day)
            + to_u8_hex(window.stop_hour)
            + to_u8_hex(window.stop_minute)
        )
        await self._request(f"6100{payload}")

    async def delete_absence_schedule(self, index: int) -> None:
        """Löscht einen Abwesenheitszeitraum."""
        await self._request(f"62{to_u8_hex(index):0>2}00")

    # ── Statistiken ───────────────────────────────────────────────────────────

    async def get_daily_usage(self, day: int, month: int, year: int) -> list[int]:
        """Tagesstatistik: 8 Werte à 3h (0:00, 3:00, …, 21:00) in Litern."""
        yr_hi = (year >> 8) & 0xFF
        yr_lo = year & 0xFF
        cmd = f"FB00{to_u8_hex(day)}{to_u8_hex(month)}{yr_lo:02X}{yr_hi:02X}"
        raw = await self._request(cmd)
        b = hex_to_bytes(raw)
        return [from_u32_le(b, i * 4) for i in range(8)]

    async def get_weekly_usage(self, week: int, year: int) -> list[int]:
        """Wochenstatistik: 7 Werte (Mo–So) in Litern."""
        yr_hi = (year >> 8) & 0xFF
        yr_lo = year & 0xFF
        cmd = f"FC00{to_u8_hex(week)}{yr_lo:02X}{yr_hi:02X}"
        raw = await self._request(cmd)
        b = hex_to_bytes(raw)
        return [from_u32_le(b, i * 4) for i in range(7)]

    async def get_monthly_usage(self, month: int, year: int) -> list[int]:
        """Monatsstatistik: bis zu 31 Tageswerte in Litern."""
        yr_hi = (year >> 8) & 0xFF
        yr_lo = year & 0xFF
        cmd = f"FD00{to_u8_hex(month)}{yr_lo:02X}{yr_hi:02X}"
        raw = await self._request(cmd)
        b = hex_to_bytes(raw)
        count = len(b) // 4
        return [from_u32_le(b, i * 4) for i in range(count)]

    async def get_yearly_usage(self, year: int) -> list[int]:
        """Jahresstatistik: 12 Monatswerte in Litern."""
        yr_hi = (year >> 8) & 0xFF
        yr_lo = year & 0xFF
        cmd = f"FE00{yr_lo:02X}{yr_hi:02X}"
        raw = await self._request(cmd)
        b = hex_to_bytes(raw)
        return [from_u32_le(b, i * 4) for i in range(12)]
