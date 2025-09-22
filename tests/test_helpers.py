from __future__ import annotations

import pytest

from custom_components.judo_leakguard import helpers
from custom_components.judo_leakguard.const import DOMAIN


def test_get_nested_success():
    data = {"a": {"b": {"c": 42}}}
    assert helpers.get_nested(data, "a.b.c") == 42


def test_get_nested_default_when_missing():
    data = {"a": {"b": {"c": 42}}}
    assert helpers.get_nested(data, "a.b.x", default="fallback") == "fallback"


def test_first_present_returns_first_value():
    data = {"a": None, "b": 7, "c": 8}
    assert helpers.first_present(data, ("a", "b", "c")) == 7


def test_first_present_returns_default():
    assert helpers.first_present({}, ("x", "y"), default=0) == 0


def test_build_device_info_defaults():
    info = helpers.build_device_info({})
    assert info.identifiers == {(DOMAIN, "unknown")}
    assert info.manufacturer == "JUDO"
    assert info.model == "ZEWA i-SAFE"
    assert info.sw_version is None


def test_build_device_info_overrides():
    payload = {
        "serial": "123456",
        "manufacturer": "MyBrand",
        "model": "Leakguard Pro",
        "firmware": "1.2.3",
    }
    info = helpers.build_device_info(payload)
    assert info.identifiers == {(DOMAIN, "123456")}
    assert info.manufacturer == "MyBrand"
    assert info.model == "Leakguard Pro"
    assert info.sw_version == "1.2.3"


def test_build_unique_id_uses_serial():
    assert helpers.build_unique_id({"serial": "ABC"}, "sensor") == "ABC_sensor"


def test_build_unique_id_falls_back_to_unknown():
    assert helpers.build_unique_id({}, "sensor") == "unknown_sensor"


def test_big_endian_helpers_roundtrip():
    assert helpers.toU8(300) == b"\xff"
    assert helpers.toU16BE(0x1234) == b"\x12\x34"
    assert helpers.fromU16BE(b"\x12\x34") == 0x1234
    assert helpers.toU32BE(0x01020304) == b"\x01\x02\x03\x04"
    assert helpers.fromU32BE(b"\x01\x02\x03\x04") == 0x01020304
    with pytest.raises(ValueError):
        helpers.fromU16BE(b"\x01")
