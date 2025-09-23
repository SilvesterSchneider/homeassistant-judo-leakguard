"""Small subset of Home Assistant date/time helpers."""

from __future__ import annotations

from datetime import datetime, timezone

try:  # pragma: no cover - zoneinfo is available on Python 3.9+
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for older environments
    ZoneInfo = None  # type: ignore


if ZoneInfo is not None:  # pragma: no branch
    DEFAULT_TIME_ZONE = ZoneInfo("UTC")
else:  # pragma: no cover
    DEFAULT_TIME_ZONE = timezone.utc


def utcnow() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


__all__ = ["DEFAULT_TIME_ZONE", "utcnow"]
