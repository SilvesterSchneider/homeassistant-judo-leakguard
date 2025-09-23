"""Subset of Home Assistant constants required for the tests."""

from __future__ import annotations

from enum import Enum


CONF_HOST = "host"
CONF_PASSWORD = "password"
CONF_USERNAME = "username"
CONF_PORT = "port"
CONF_PROTOCOL = "protocol"
CONF_VERIFY_SSL = "verify_ssl"

STATE_UNKNOWN = "unknown"
PERCENTAGE = "%"


class UnitOfTime(str, Enum):
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"


class UnitOfVolume(str, Enum):
    LITERS = "L"
    CUBIC_METERS = "m³"


class UnitOfVolumeFlowRate(str, Enum):
    LITERS_PER_HOUR = "L/h"
    LITERS_PER_MINUTE = "L/min"


class UnitOfPressure(str, Enum):
    BAR = "bar"


class UnitOfTemperature(str, Enum):
    CELSIUS = "°C"


class Platform(str, Enum):
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    NUMBER = "number"
    SELECT = "select"
    SENSOR = "sensor"
    SWITCH = "switch"


__all__ = [
    "CONF_HOST",
    "CONF_PASSWORD",
    "CONF_PORT",
    "CONF_PROTOCOL",
    "CONF_USERNAME",
    "CONF_VERIFY_SSL",
    "PERCENTAGE",
    "Platform",
    "STATE_UNKNOWN",
    "UnitOfPressure",
    "UnitOfTemperature",
    "UnitOfTime",
    "UnitOfVolume",
    "UnitOfVolumeFlowRate",
]
