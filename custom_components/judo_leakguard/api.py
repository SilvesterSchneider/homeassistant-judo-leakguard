"""Client helper für die lokale Judo-Leakguard-REST-API."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
import string
from enum import IntEnum
from typing import Final
from urllib.parse import urlparse

from aiohttp import BasicAuth, ClientError, ClientSession

# Die PDF beschreibt nur den Pfad `/api/rest/<kommando>` und nennt keinen TLS-Endpunkt.
# Deshalb verwenden wir HTTP als Standard und akzeptieren optional eine manuell
# angegebene HTTPS-URL.
DEFAULT_SCHEME: Final = "http"
DEFAULT_USERNAME: Final = "admin"
DEFAULT_PASSWORD: Final = "Connectivity"
EXPECTED_DEVICE_TYPE: Final = "44"
MAX_ATTEMPTS: Final = 3
BACKOFF_SECONDS: Final = 2

CMD_DEVICE_TYPE: Final = "FF00"
CMD_SERIAL_NUMBER: Final = "0600"
CMD_FIRMWARE_VERSION: Final = "0100"
CMD_COMMISSION_DATE: Final = "0E00"
CMD_TOTAL_WATER: Final = "2800"
CMD_ACK_ALARM: Final = "6300"
CMD_CLOSE_VALVE: Final = "5100"
CMD_OPEN_VALVE: Final = "5200"
CMD_SLEEP_START: Final = "5400"
CMD_SLEEP_END: Final = "5500"
CMD_VACATION_START: Final = "5700"
CMD_VACATION_END: Final = "5800"
CMD_MICROLEAK_TEST: Final = "5C00"
CMD_LEARN_MODE: Final = "5D00"
CMD_READ_ABSENCE_LIMITS: Final = "5E00"
CMD_WRITE_ABSENCE_LIMITS: Final = "5F00"
CMD_WRITE_LEAK_PRESET: Final = "50"
CMD_SET_SLEEP_HOURS: Final = "53"
CMD_READ_SLEEP_HOURS: Final = "6600"
CMD_SET_VACATION_TYPE: Final = "56"
CMD_READ_LEARN_STATUS: Final = "6400"
CMD_READ_MICROLEAK_MODE: Final = "6500"
CMD_SET_MICROLEAK_MODE: Final = "5B"
CMD_READ_ABSENCE_WINDOW: Final = "60"
CMD_WRITE_ABSENCE_WINDOW: Final = "61"
CMD_DELETE_ABSENCE_WINDOW: Final = "6200"
CMD_READ_CLOCK: Final = "5900"
CMD_SET_CLOCK: Final = "5A"
CMD_DAY_STATS: Final = "FB"
CMD_WEEK_STATS: Final = "FC"
CMD_MONTH_STATS: Final = "FD"
CMD_YEAR_STATS: Final = "FE"


@dataclass(frozen=True)
class DeviceInfo:
    """Geräteinformationen, die beim Einrichtungs-Check zurückgegeben werden."""

    device_type: str


@dataclass(frozen=True)
class FirmwareInfo:
    """Darstellung der Firmwareversion als Major/Minor/Patch."""

    major: int
    minor: int
    patch: int

    @property
    def version(self) -> str:
        """Liefert die menschenlesbare Version als Zeichenkette."""

        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class CommissionInfo:
    """Zeitpunkt der Inbetriebnahme."""

    timestamp: int
    commissioned_at: datetime


@dataclass(frozen=True)
class TotalWaterUsage:
    """Gesamtverbrauch in Litern seit Inbetriebnahme."""

    liters: int


class VacationType(IntEnum):
    """Mögliche Vacation-Profile."""

    OFF = 0
    U1 = 1
    U2 = 2
    U3 = 3


class MicroLeakMode(IntEnum):
    """Modus für die Mikro-Leckage-Erkennung."""

    OFF = 0
    NOTIFY = 1
    NOTIFY_AND_CLOSE = 2


@dataclass(frozen=True)
class LearnStatus:
    """Status des Lernmodus."""

    active: bool
    remaining_liters: int


@dataclass(frozen=True)
class AbsenceLimits:
    """Grenzwerte für Abwesenheitsüberwachung (Flow/Volumen/Dauer)."""

    max_flow_lph: int
    max_volume_l: int
    max_duration_min: int


@dataclass(frozen=True)
class LeakPreset:
    """Kapselt das Payload für den 0x50-Kommando-Aufruf."""

    vacation_type: VacationType
    max_flow_lph: int
    max_volume_l: int
    max_duration_min: int

    def as_hex(self) -> str:
        """Buildet das Hex-Payload laut Spezifikation."""

        return (
            HexCodec.to_u8(int(self.vacation_type))
            + HexCodec.to_u16(self.max_flow_lph)
            + HexCodec.to_u16(self.max_volume_l)
            + HexCodec.to_u16(self.max_duration_min)
        )


@dataclass(frozen=True)
class AbsenceWindow:
    """Konfiguration eines Abwesenheitszeitfensters."""

    index: int
    start_day: int
    start_hour: int
    start_minute: int
    stop_day: int
    stop_hour: int
    stop_minute: int

    def as_hex(self) -> str:
        """Serialisiert das Fenster zu 7 Bytes."""

        return (
            HexCodec.to_u8(self.index)
            + HexCodec.to_u8(self.start_day)
            + HexCodec.to_u8(self.start_hour)
            + HexCodec.to_u8(self.start_minute)
            + HexCodec.to_u8(self.stop_day)
            + HexCodec.to_u8(self.stop_hour)
            + HexCodec.to_u8(self.stop_minute)
        )

    @staticmethod
    def from_hex(index: int, payload: str) -> AbsenceWindow:
        """Erzeugt eine Instanz aus dem 6-Byte-Read-Resultat."""

        if len(payload) != 12:
            raise JudoLeakguardApiError("Absence window payload must be 6 bytes")
        start_day = HexCodec.from_u8(payload[0:2])
        start_hour = HexCodec.from_u8(payload[2:4])
        start_minute = HexCodec.from_u8(payload[4:6])
        stop_day = HexCodec.from_u8(payload[6:8])
        stop_hour = HexCodec.from_u8(payload[8:10])
        stop_minute = HexCodec.from_u8(payload[10:12])
        return AbsenceWindow(
            index=index,
            start_day=start_day,
            start_hour=start_hour,
            start_minute=start_minute,
            stop_day=stop_day,
            stop_hour=stop_hour,
            stop_minute=stop_minute,
        )


@dataclass(frozen=True)
class ClockState:
    """Aktuelle Uhrzeit des Geräts."""

    timestamp: datetime

    @property
    def day(self) -> int:
        return self.timestamp.day

    @property
    def month(self) -> int:
        return self.timestamp.month

    @property
    def year(self) -> int:
        return self.timestamp.year

    @property
    def hour(self) -> int:
        return self.timestamp.hour

    @property
    def minute(self) -> int:
        return self.timestamp.minute

    @property
    def second(self) -> int:
        return self.timestamp.second


@dataclass(frozen=True)
class DayStatistics:
    """Verbrauch pro 3-Stunden-Block eines Tages."""

    liters_per_three_hours: list[int]


@dataclass(frozen=True)
class WeekStatistics:
    """Verbrauch pro Wochentag."""

    liters_per_day: list[int]


@dataclass(frozen=True)
class MonthStatistics:
    """Verbrauch pro Kalendertag eines Monats."""

    liters_per_day: list[int]


@dataclass(frozen=True)
class YearStatistics:
    """Verbrauch pro Monat eines Jahres."""

    liters_per_month: list[int]


class JudoLeakguardApiError(Exception):
    """Basisfehler für alle Kommunikationsprobleme mit der REST-API."""


class UnsupportedDeviceError(JudoLeakguardApiError):
    """Spezifischer Fehler, wenn der Typ nicht dem erwarteten ZEWA i-SAFE entspricht."""


class HexCodec:
    """Hilfsfunktionen für Hex-Parsing und -Serialisierung."""

    @staticmethod
    def normalize(raw: str | None) -> str:
        """Filtert Whitespace/Quotes und validiert die Hex-Länge."""

        if raw is None:
            return ""
        text = str(raw).strip().strip('"').replace(" ", "")
        if text.startswith("0x") or text.startswith("0X"):
            text = text[2:]
        if not text:
            return ""
        if len(text) % 2 != 0 or any(ch not in string.hexdigits for ch in text):
            raise ValueError("invalid hex payload")
        return text.upper()

    @staticmethod
    def to_u8(value: int) -> str:
        HexCodec._validate_range(value, 0xFF)
        return f"{value:02X}"

    @staticmethod
    def to_u16(value: int) -> str:
        HexCodec._validate_range(value, 0xFFFF)
        return value.to_bytes(2, "big").hex().upper()

    @staticmethod
    def to_u32(value: int) -> str:
        HexCodec._validate_range(value, 0xFFFFFFFF)
        return value.to_bytes(4, "big").hex().upper()

    @staticmethod
    def from_u8(value: str) -> int:
        return int(value, 16)

    @staticmethod
    def from_u16(value: str) -> int:
        return int.from_bytes(bytes.fromhex(value), "big")

    @staticmethod
    def from_u32(value: str) -> int:
        return int.from_bytes(bytes.fromhex(value), "big")

    @staticmethod
    def chunks(payload: str, size_bytes: int) -> list[str]:
        step = size_bytes * 2
        if step == 0:
            return []
        return [payload[i : i + step] for i in range(0, len(payload), step)]

    @staticmethod
    def _validate_range(value: int, max_value: int) -> None:
        if value < 0 or value > max_value:
            raise ValueError(f"value {value} out of range 0..{max_value}")


class JudoLeakguardApi:
    """Schlanker REST-Client für die lokale ZEWA-i-SAFE-API."""

    def __init__(self, host: str, username: str, password: str) -> None:
        parsed = urlparse(host)
        if not parsed.scheme:
            host = f"{DEFAULT_SCHEME}://{host}"
        self._base_url = host.rstrip("/")
        self._auth = BasicAuth(username, password)

    async def async_get_device_info(self, session: ClientSession) -> DeviceInfo:
        """Prüft den Gerätetyp und stellt sicher, dass es ein ZEWA i-SAFE ist."""

        device_type = await self.async_read_device_type(session)
        if device_type != EXPECTED_DEVICE_TYPE:
            raise UnsupportedDeviceError(
                f"Unexpected device type '{device_type}', expected '{EXPECTED_DEVICE_TYPE}'"
            )
        return DeviceInfo(device_type=device_type)

    async def async_read_device_type(self, session: ClientSession) -> str:
        """Ruft den Gerätetyp (FF00) ab."""

        payload = await self._async_request_hex(session, CMD_DEVICE_TYPE)
        return payload or ""

    async def async_read_serial_number(self, session: ClientSession) -> str:
        """Liest die Seriennummer (0600) als Hex-String."""

        return await self._async_request_hex(session, CMD_SERIAL_NUMBER)

    async def async_read_firmware(self, session: ClientSession) -> FirmwareInfo:
        """Liest die Firmwareversion (0100) und gibt sie typisiert zurück."""

        payload = await self._async_request_hex(session, CMD_FIRMWARE_VERSION)
        bytes_value = bytes.fromhex(payload.ljust(6, "0"))[:3]
        major, minor, patch = bytes_value
        return FirmwareInfo(major=major, minor=minor, patch=patch)

    async def async_read_commission_info(self, session: ClientSession) -> CommissionInfo:
        """Liest das Inbetriebnahme-Datum (0E00) als Unix-Zeitstempel."""

        payload = await self._async_request_hex(session, CMD_COMMISSION_DATE)
        timestamp = HexCodec.from_u32(payload)
        commissioned_at = datetime.fromtimestamp(timestamp, tz=UTC)
        return CommissionInfo(timestamp=timestamp, commissioned_at=commissioned_at)

    async def async_read_total_water(self, session: ClientSession) -> TotalWaterUsage:
        """Liest den Gesamtwasserverbrauch (2800)."""

        payload = await self._async_request_hex(session, CMD_TOTAL_WATER)
        return TotalWaterUsage(liters=HexCodec.from_u32(payload))

    async def async_acknowledge_alarm(self, session: ClientSession) -> None:
        """Bestätigt einen Alarm (6300)."""

        await self._async_request(session, CMD_ACK_ALARM)

    async def async_close_valve(self, session: ClientSession) -> None:
        """Schließt das Ventil (5100)."""

        await self._async_request(session, CMD_CLOSE_VALVE)

    async def async_open_valve(self, session: ClientSession) -> None:
        """Öffnet das Ventil (5200)."""

        await self._async_request(session, CMD_OPEN_VALVE)

    async def async_start_sleep_mode(self, session: ClientSession) -> None:
        """Aktiviert den Schlafmodus (5400)."""

        await self._async_request(session, CMD_SLEEP_START)

    async def async_end_sleep_mode(self, session: ClientSession) -> None:
        """Beendet den Schlafmodus (5500)."""

        await self._async_request(session, CMD_SLEEP_END)

    async def async_start_vacation_mode(self, session: ClientSession) -> None:
        """Aktiviert den Urlaubsmodus (5700)."""

        await self._async_request(session, CMD_VACATION_START)

    async def async_end_vacation_mode(self, session: ClientSession) -> None:
        """Beendet den Urlaubsmodus (5800)."""

        await self._async_request(session, CMD_VACATION_END)

    async def async_trigger_micro_leak_test(self, session: ClientSession) -> None:
        """Startet einen Mikro-Lecktest (5C00)."""

        await self._async_request(session, CMD_MICROLEAK_TEST)

    async def async_start_learn_mode(self, session: ClientSession) -> None:
        """Startet den Learn-Mode (5D00)."""

        await self._async_request(session, CMD_LEARN_MODE)

    async def async_read_learn_status(self, session: ClientSession) -> LearnStatus:
        """Liest den Lernstatus (6400)."""

        payload = await self._async_request_hex(session, CMD_READ_LEARN_STATUS)
        if len(payload) != 6:
            # Fallback/Safety if response is unexpected
            return LearnStatus(active=False, remaining_liters=0)

        active_byte = HexCodec.from_u8(payload[0:2])
        remaining = HexCodec.from_u16(payload[2:6])
        return LearnStatus(active=(active_byte == 1), remaining_liters=remaining)

    async def async_read_absence_limits(self, session: ClientSession) -> AbsenceLimits:
        """Liest die Abwesenheitsgrenzen (5E00)."""

        payload = await self._async_request_hex(session, CMD_READ_ABSENCE_LIMITS)
        if len(payload) != 12:
            raise JudoLeakguardApiError("Absence limits payload must be 6 bytes")
        flow = HexCodec.from_u16(payload[0:4])
        volume = HexCodec.from_u16(payload[4:8])
        minutes = HexCodec.from_u16(payload[8:12])
        return AbsenceLimits(flow, volume, minutes)

    async def async_write_absence_limits(
        self, session: ClientSession, limits: AbsenceLimits
    ) -> None:
        """Schreibt die Abwesenheitsgrenzen (5F00)."""

        payload = (
            HexCodec.to_u16(limits.max_flow_lph)
            + HexCodec.to_u16(limits.max_volume_l)
            + HexCodec.to_u16(limits.max_duration_min)
        )
        await self._async_request(session, CMD_WRITE_ABSENCE_LIMITS, payload)

    async def async_write_leak_preset(self, session: ClientSession, preset: LeakPreset) -> None:
        """Konfiguriert das Leak-Preset (50xx)."""

        await self._async_request(session, CMD_WRITE_LEAK_PRESET, preset.as_hex())

    async def async_set_sleep_hours(self, session: ClientSession, hours: int) -> None:
        """Setzt die Schlafstunden (53xx)."""

        if not 1 <= hours <= 10:
            raise ValueError("Sleep hours must be between 1 and 10")
        await self._async_request(session, CMD_SET_SLEEP_HOURS, HexCodec.to_u8(hours))

    async def async_read_sleep_hours(self, session: ClientSession) -> int:
        """Liest die Schlafdauer (6600)."""

        payload = await self._async_request_hex(session, CMD_READ_SLEEP_HOURS)
        return HexCodec.from_u8(payload or "00")

    async def async_set_vacation_type(self, session: ClientSession, vacation_type: VacationType) -> None:
        """Setzt den Vacation-Typ (56xx)."""

        await self._async_request(session, CMD_SET_VACATION_TYPE, HexCodec.to_u8(int(vacation_type)))

    async def async_read_micro_leak_mode(self, session: ClientSession) -> MicroLeakMode:
        """Gibt den Mikro-Leckmodus (6500) zurück."""

        payload = await self._async_request_hex(session, CMD_READ_MICROLEAK_MODE)
        return MicroLeakMode(HexCodec.from_u8(payload or "00"))

    async def async_set_micro_leak_mode(self, session: ClientSession, mode: MicroLeakMode) -> None:
        """Setzt den Mikro-Leckmodus (5Bxx)."""

        await self._async_request(session, CMD_SET_MICROLEAK_MODE, HexCodec.to_u8(int(mode)))

    async def async_read_absence_window(self, session: ClientSession, index: int) -> AbsenceWindow:
        """Liest ein Abwesenheitsfenster (60xx)."""

        self._ensure_window_index(index)
        payload = await self._async_request_hex(session, CMD_READ_ABSENCE_WINDOW, HexCodec.to_u8(index))
        return AbsenceWindow.from_hex(index, payload or "000000000000")

    async def async_write_absence_window(self, session: ClientSession, window: AbsenceWindow) -> None:
        """Schreibt ein Abwesenheitsfenster (61xx)."""

        self._ensure_window_index(window.index)
        await self._async_request(session, CMD_WRITE_ABSENCE_WINDOW, window.as_hex())

    async def async_delete_absence_window(self, session: ClientSession, index: int) -> None:
        """Löscht ein Abwesenheitsfenster (6200xx)."""

        self._ensure_window_index(index)
        await self._async_request(session, CMD_DELETE_ABSENCE_WINDOW, HexCodec.to_u8(index))

    async def async_read_clock(self, session: ClientSession) -> ClockState:
        """Liest die Geräteuhr (5900)."""

        payload = await self._async_request_hex(session, CMD_READ_CLOCK)
        if len(payload) != 12:
            raise JudoLeakguardApiError("Clock payload must be 6 bytes")
        day = HexCodec.from_u8(payload[0:2])
        month = HexCodec.from_u8(payload[2:4])
        year = 2000 + HexCodec.from_u8(payload[4:6])
        hour = HexCodec.from_u8(payload[6:8])
        minute = HexCodec.from_u8(payload[8:10])
        second = HexCodec.from_u8(payload[10:12])
        return ClockState(datetime(year, month, day, hour, minute, second, tzinfo=UTC))

    async def async_set_clock(self, session: ClientSession, when: datetime | ClockState) -> None:
        """Stellt die Geräteuhr (5Axx)."""

        if isinstance(when, ClockState):
            dt = when.timestamp
        else:
            dt = when
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.astimezone(UTC)
        if dt.year < 2000 or dt.year > 2255:
            raise ValueError("Device clock only supports years 2000..2255")
        payload = (
            HexCodec.to_u8(dt.day)
            + HexCodec.to_u8(dt.month)
            + HexCodec.to_u8(dt.year - 2000)
            + HexCodec.to_u8(dt.hour)
            + HexCodec.to_u8(dt.minute)
            + HexCodec.to_u8(dt.second)
        )
        await self._async_request(session, CMD_SET_CLOCK, payload)

    async def async_read_day_statistics(self, session: ClientSession, target_day: date) -> DayStatistics:
        """Holt Tagesstatistiken (FB)."""

        payload = await self._async_request_hex(session, CMD_DAY_STATS, self._encode_day(target_day))
        buckets = self._parse_u32_sequence(payload, expected_blocks=8)
        return DayStatistics(liters_per_three_hours=buckets)

    async def async_read_week_statistics(self, session: ClientSession, target_day: date) -> WeekStatistics:
        """Holt Wochenstatistiken (FC)."""

        payload = await self._async_request_hex(session, CMD_WEEK_STATS, self._encode_week(target_day))
        buckets = self._parse_u32_sequence(payload, expected_blocks=7)
        return WeekStatistics(liters_per_day=buckets)

    async def async_read_month_statistics(self, session: ClientSession, target_day: date) -> MonthStatistics:
        """Holt Monatsstatistiken (FD)."""

        payload = await self._async_request_hex(session, CMD_MONTH_STATS, self._encode_month(target_day))
        buckets = self._parse_u32_sequence(payload)
        return MonthStatistics(liters_per_day=buckets)

    async def async_read_year_statistics(self, session: ClientSession, year: int) -> YearStatistics:
        """Holt Jahresstatistiken (FE)."""

        payload = await self._async_request_hex(
            session, CMD_YEAR_STATS, HexCodec.to_u16(year)
        )
        buckets = self._parse_u32_sequence(payload, expected_blocks=12)
        return YearStatistics(liters_per_month=buckets)

    async def _async_request_hex(self, session: ClientSession, command: str, payload: str = "") -> str:
        """Sendet einen Befehl und liefert die geparste Hex-Antwort."""

        text = await self._async_request(session, command, payload)
        try:
            return HexCodec.normalize(self._extract_data_field(text))
        except ValueError as exc:
            raise JudoLeakguardApiError("Received malformed hex payload") from exc

    async def _async_request(self, session: ClientSession, command: str, payload: str = "") -> str:
        """Sendet einen einzelnen API-Aufruf mit Backoff und Fehlerbehandlung."""

        url = f"{self._base_url}/api/rest/{command}{payload}"
        delay = BACKOFF_SECONDS
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with session.get(url, auth=self._auth) as response:
                    if response.status == 429 and attempt < MAX_ATTEMPTS:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    response.raise_for_status()
                    return await response.text()
            except ClientError as err:
                if attempt == MAX_ATTEMPTS:
                    raise JudoLeakguardApiError(f"Request failed for {command} ({url}): {err}") from err
                await asyncio.sleep(delay)
                delay *= 2
        raise JudoLeakguardApiError(f"Request failed for {command} ({url}) after {MAX_ATTEMPTS} attempts")

    @staticmethod
    def _extract_data_field(payload: str) -> str:
        """Extrahiert das `data`-Feld aus der Antwort (Fallback: roh)."""

        try:
            parsed = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return payload
        return parsed.get("data", "")

    @staticmethod
    def _parse_u32_sequence(payload: str, expected_blocks: int | None = None) -> list[int]:
        """Zerlegt ein Hex-Payload in 32-Bit-Werte."""

        if expected_blocks is not None and len(payload) != expected_blocks * 8:
            raise JudoLeakguardApiError("Unexpected length for statistics payload")
        return [HexCodec.from_u32(part) for part in HexCodec.chunks(payload, 4)]

    @staticmethod
    def _encode_day(target_day: date) -> str:
        return (
            HexCodec.to_u16(target_day.year)
            + HexCodec.to_u8(target_day.month)
            + HexCodec.to_u8(target_day.day)
        )

    @staticmethod
    def _encode_week(target_day: date) -> str:
        iso_year, iso_week, _ = target_day.isocalendar()
        return HexCodec.to_u16(iso_year) + HexCodec.to_u8(iso_week)

    @staticmethod
    def _encode_month(target_day: date) -> str:
        return HexCodec.to_u16(target_day.year) + HexCodec.to_u8(target_day.month)

    @staticmethod
    def _ensure_window_index(index: int) -> None:
        if not 0 <= index <= 6:
            raise ValueError("Absence window index must be between 0 and 6")
