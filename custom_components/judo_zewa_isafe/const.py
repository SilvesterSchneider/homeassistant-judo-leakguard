"""Constants for the Judo ZEWA i-SAFE integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "judo_zewa_isafe"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

PLATFORMS: list[str] = [
    "binary_sensor",
    "button",
    "number",
    "select",
    "sensor",
    "switch",
]
