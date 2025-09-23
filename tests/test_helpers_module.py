from __future__ import annotations

import pytest

from custom_components.judo_leakguard import helpers
from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.parametrize(
    "value, maximum, expected",
    [(-5, helpers.U8_MAX, 0), (helpers.U16_MAX + 10, helpers.U16_MAX, helpers.U16_MAX), (42, helpers.U8_MAX, 42)],
)
def test_clamp_behaviour(value: int, maximum: int, expected: int) -> None:
    assert helpers._clamp(value, maximum) == expected


def test_integer_serialisation_and_parsing() -> None:
    assert helpers.toU8(-1) == b"\x00"
    assert helpers.toU8(999) == b"\xff"
    assert helpers.toU16BE(-1) == b"\x00\x00"
    assert helpers.toU16BE(0x123456) == b"\xff\xff"
    assert helpers.toU32BE(-1) == b"\x00\x00\x00\x00"
    assert helpers.toU32BE(0x1FFFFFFFF) == b"\xff\xff\xff\xff"

    assert helpers.fromU16BE(b"\x12\x34") == 0x1234
    assert helpers.fromU32BE(b"\x00\x00\x01\x02") == 0x0102

    with pytest.raises(ValueError):
        helpers.fromU16BE(b"\x01")
    with pytest.raises(ValueError):
        helpers.fromU32BE(b"\x01\x02\x03")


def test_nested_helpers_and_defaults() -> None:
    payload = {
        "device": {"serial": "ABC"},
        "meta": {"manufacturer": "JUDO", "firmware": "1.0"},
        "values": {"present": 1},
    }

    assert helpers.get_nested(payload, "device.serial") == "ABC"
    assert helpers.get_nested(payload, "device.missing", default="x") == "x"
    assert helpers.first_present(payload, ("values.present", "device.serial")) == 1
    assert helpers.first_present(payload, ("values.absent", "device.serial")) == "ABC"
    assert helpers.first_present({}, ("values.absent",), default="fallback") == "fallback"

    assert helpers.extract_serial(payload) == "ABC"
    assert helpers.extract_model({}) == "ZEWA i-SAFE"
    assert helpers.extract_firmware({}) is None
    assert helpers.extract_manufacturer({}) == "JUDO"

    info = helpers.build_device_info(payload)
    assert info.identifiers == {(DOMAIN, "ABC")}
    assert info.manufacturer == "JUDO"
    assert info.model == "ZEWA i-SAFE"
    assert info.sw_version == "1.0"

    assert helpers.build_unique_id(payload, "sensor") == "ABC_sensor"


def test_build_unique_id_with_unknown_serial() -> None:
    info = helpers.build_device_info(None)
    assert info.identifiers == {(DOMAIN, "unknown")}
    unique = helpers.build_unique_id({}, "button")
    assert unique == "unknown_button"
