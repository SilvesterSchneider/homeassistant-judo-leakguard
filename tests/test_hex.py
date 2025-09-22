import pytest

from zewa_client.hex import (
    from_u16be,
    from_u32be,
    from_u8,
    to_u16be,
    to_u32be,
    to_u8,
)


def test_u8_round_trip() -> None:
    value = 0xAB
    encoded = to_u8(value)
    assert encoded == b"\xAB"
    assert from_u8(encoded) == value


def test_u16_round_trip() -> None:
    value = 0xBEEF
    encoded = to_u16be(value)
    assert encoded == b"\xBE\xEF"
    assert from_u16be(encoded) == value


def test_u32_round_trip() -> None:
    value = 0x1234_5678
    encoded = to_u32be(value)
    assert encoded == b"\x12\x34\x56\x78"
    assert from_u32be(encoded) == value


@pytest.mark.parametrize(
    "func,value",
    [(to_u8, -1), (to_u8, 256), (to_u16be, 1 << 16), (to_u32be, 1 << 32)],
)
def test_encode_range_errors(func, value) -> None:
    with pytest.raises(ValueError):
        func(value)


@pytest.mark.parametrize(
    "func,data",
    [
        (from_u8, b""),
        (from_u16be, b"\x00"),
        (from_u32be, b"\x00\x01"),
    ],
)
def test_decode_length_errors(func, data) -> None:
    with pytest.raises(ValueError):
        func(data)
