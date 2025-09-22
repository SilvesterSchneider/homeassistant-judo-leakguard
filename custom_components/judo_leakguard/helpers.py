from __future__ import annotations

from typing import Any, Iterable

U8_MAX = 0xFF
U16_MAX = 0xFFFF
U32_MAX = 0xFFFFFFFF


def _clamp(value: int, maximum: int) -> int:
    """Clamp ``value`` to the range 0..maximum."""

    if value < 0:
        return 0
    if value > maximum:
        return maximum
    return int(value)


def toU8(value: int) -> bytes:
    """Serialize ``value`` as unsigned 8-bit big-endian bytes."""

    return bytes([_clamp(value, U8_MAX)])


def toU16BE(value: int) -> bytes:
    """Serialize ``value`` as unsigned 16-bit big-endian bytes."""

    return _clamp(value, U16_MAX).to_bytes(2, "big", signed=False)


def toU32BE(value: int) -> bytes:
    """Serialize ``value`` as unsigned 32-bit big-endian bytes."""

    return _clamp(value, U32_MAX).to_bytes(4, "big", signed=False)


def fromU16BE(data: bytes, offset: int = 0) -> int:
    """Parse an unsigned 16-bit big-endian integer from ``data`` at ``offset``."""

    end = offset + 2
    if end > len(data):
        raise ValueError("Not enough data for U16")
    return int.from_bytes(data[offset:end], "big", signed=False)


def fromU32BE(data: bytes, offset: int = 0) -> int:
    """Parse an unsigned 32-bit big-endian integer from ``data`` at ``offset``."""

    end = offset + 4
    if end > len(data):
        raise ValueError("Not enough data for U32")
    return int.from_bytes(data[offset:end], "big", signed=False)

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def get_nested(data: dict[str, Any] | None, path: str, default: Any | None = None) -> Any | None:
    """Return a nested value from ``data`` following ``path`` (dot separated)."""
    if not data:
        return default
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def first_present(
    data: dict[str, Any] | None,
    candidates: Iterable[str],
    default: Any | None = None,
) -> Any | None:
    """Return the first non-``None`` candidate found in ``data``."""
    for path in candidates:
        value = get_nested(data, path, default=None)
        if value is not None:
            return value
    return default


def extract_serial(data: dict[str, Any] | None) -> str:
    serial = first_present(data, ("serial", "device.serial", "meta.serial"))
    if serial is None:
        return "unknown"
    return str(serial)


def extract_model(data: dict[str, Any] | None) -> str:
    model = first_present(data, ("model", "device.model", "meta.model"))
    if model is None:
        return "ZEWA i-SAFE"
    return str(model)


def extract_firmware(data: dict[str, Any] | None) -> str | None:
    firmware = first_present(data, ("firmware", "sw_version", "meta.firmware"))
    if firmware is None:
        return None
    return str(firmware)


def extract_manufacturer(data: dict[str, Any] | None) -> str:
    manufacturer = first_present(data, ("manufacturer", "brand", "meta.manufacturer"))
    if manufacturer is None:
        return "JUDO"
    return str(manufacturer)


def build_device_info(data: dict[str, Any] | None) -> DeviceInfo:
    serial = extract_serial(data)
    manufacturer = extract_manufacturer(data)
    model = extract_model(data)
    firmware = extract_firmware(data)
    return DeviceInfo(
        identifiers={(DOMAIN, serial)},
        manufacturer=manufacturer,
        model=model,
        sw_version=firmware,
        name="Judo Leakguard",
    )


def build_unique_id(data: dict[str, Any] | None, suffix: str) -> str:
    serial = extract_serial(data)
    return f"{serial}_{suffix}"
