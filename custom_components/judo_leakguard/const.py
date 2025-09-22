from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "judo_leakguard"

DEFAULT_SCAN_INTERVAL: Final[timedelta] = timedelta(seconds=30)

# Optionale Keys - nur benutzt, falls im ConfigEntry vorhanden
CONF_PROTOCOL: Final[str] = "protocol"   # "http" | "https"
CONF_PORT: Final[str] = "port"           # int
CONF_VERIFY_SSL: Final[str] = "verify_ssl"  # bool
CONF_SEND_AS_QUERY: Final[str] = "send_data_as_query"  # bool
