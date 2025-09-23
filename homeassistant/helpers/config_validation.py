"""Re-export the lightweight :mod:`voluptuous` helpers under Home Assistant's alias."""

from __future__ import annotations

from datetime import datetime as datetime_cls

from voluptuous import All, In, Invalid, Optional, Range, Required, Schema

string = str
boolean = bool
entity_id = str


def datetime(value):
    if isinstance(value, datetime_cls):
        return value
    raise Invalid(f"Expected datetime, got {value!r}")


__all__ = [
    "All",
    "In",
    "Invalid",
    "Optional",
    "Range",
    "Required",
    "Schema",
    "boolean",
    "datetime",
    "entity_id",
    "string",
]
