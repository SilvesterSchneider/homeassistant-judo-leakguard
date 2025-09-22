"""Helpers for encoding and decoding integers to big-endian hex."""

from __future__ import annotations

from typing import ByteString


def _ensure_range(value: int, bits: int) -> None:
    if not isinstance(value, int):  # pragma: no cover - defensive
        raise TypeError("value must be an int")
    max_value = (1 << bits) - 1
    if value < 0 or value > max_value:
        raise ValueError(f"value {value} out of range for {bits}-bit unsigned integer")


def to_u8(value: int) -> bytes:
    """Encode *value* as an unsigned 8-bit integer."""

    _ensure_range(value, 8)
    return value.to_bytes(1, "big")


def to_u16be(value: int) -> bytes:
    """Encode *value* as a big-endian unsigned 16-bit integer."""

    _ensure_range(value, 16)
    return value.to_bytes(2, "big")


def to_u32be(value: int) -> bytes:
    """Encode *value* as a big-endian unsigned 32-bit integer."""

    _ensure_range(value, 32)
    return value.to_bytes(4, "big")


def _require_length(data: ByteString, offset: int, size: int) -> None:
    if offset < 0:
        raise ValueError("offset must be positive")
    if len(data) < offset + size:
        raise ValueError(
            f"buffer of length {len(data)} is too small for {size} bytes at offset {offset}"
        )


def from_u8(data: ByteString, offset: int = 0) -> int:
    """Decode an unsigned 8-bit integer from *data* starting at *offset*."""

    _require_length(data, offset, 1)
    return int(data[offset])


def from_u16be(data: ByteString, offset: int = 0) -> int:
    """Decode a big-endian unsigned 16-bit integer from *data* starting at *offset*."""

    _require_length(data, offset, 2)
    return int.from_bytes(bytes(data[offset : offset + 2]), "big")


def from_u32be(data: ByteString, offset: int = 0) -> int:
    """Decode a big-endian unsigned 32-bit integer from *data* starting at *offset*."""

    _require_length(data, offset, 4)
    return int.from_bytes(bytes(data[offset : offset + 4]), "big")


__all__ = [
    "to_u8",
    "to_u16be",
    "to_u32be",
    "from_u8",
    "from_u16be",
    "from_u32be",
]
