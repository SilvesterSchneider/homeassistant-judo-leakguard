"""Typed models describing responses from the ZEWA REST API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Tuple


class DeviceType(str, Enum):
    """Known device type identifiers."""

    ZEWA_I_SAFE = "ZEWA_I_SAFE"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_hex(cls, code: str) -> "DeviceType":
        if code.upper() == "44":
            return cls.ZEWA_I_SAFE
        return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Information about the connected device."""

    raw_code: str
    device_type: DeviceType


@dataclass(frozen=True, slots=True)
class FirmwareVersion:
    """Semantic representation of the firmware version returned by the device."""

    major: int
    minor: int
    patch: int

    def as_string(self) -> str:
        return f"{self.major:02d}.{self.minor:02d}.{self.patch:02d}"

    def __str__(self) -> str:  # pragma: no cover - trivial passthrough
        return self.as_string()


@dataclass(frozen=True, slots=True)
class AbsenceLimits:
    """Absence monitoring thresholds."""

    max_flow_l_h: int
    max_volume_l: int
    max_duration_min: int


@dataclass(frozen=True, slots=True)
class LeakPreset:
    """Leak preset parameters transmitted to the device."""

    vacation_type: int
    max_flow_l_h: int
    max_volume_l: int
    max_duration_min: int


@dataclass(frozen=True, slots=True)
class AbsenceWindow:
    """Scheduled absence window definition."""

    index: int
    start_day: int
    start_hour: int
    start_minute: int
    end_day: int
    end_hour: int
    end_minute: int

    @property
    def is_configured(self) -> bool:
        return any(
            value != 0
            for value in (
                self.start_day,
                self.start_hour,
                self.start_minute,
                self.end_day,
                self.end_hour,
                self.end_minute,
            )
        )


@dataclass(frozen=True, slots=True)
class DeviceClock:
    """Clock information returned by the device."""

    day: int
    month: int
    year: int
    hour: int
    minute: int
    second: int

    def as_datetime(self) -> datetime:
        tz_aware = datetime(
            self.year,
            max(self.month, 1),
            max(self.day, 1),
            self.hour,
            self.minute,
            self.second,
            tzinfo=timezone.utc,
        )
        return tz_aware


@dataclass(frozen=True, slots=True)
class DayStats:
    """Water usage per three-hour slot of a single day."""

    day_key: int
    values: Tuple[int, ...]


@dataclass(frozen=True, slots=True)
class WeekStats:
    """Water usage per day of a specific ISO week."""

    week: int
    year: int
    values: Tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MonthStats:
    """Water usage per day of a month."""

    month: int
    year: int
    values: Tuple[int, ...]


@dataclass(frozen=True, slots=True)
class YearStats:
    """Water usage per month of a year."""

    year: int
    values: Tuple[int, ...]


__all__ = [
    "AbsenceLimits",
    "AbsenceWindow",
    "DayStats",
    "DeviceClock",
    "DeviceInfo",
    "DeviceType",
    "FirmwareVersion",
    "LeakPreset",
    "MonthStats",
    "WeekStats",
    "YearStats",
]
