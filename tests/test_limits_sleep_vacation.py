import pytest
from aioresponses import aioresponses

from zewa_client.client import ZewaClient


def test_limits_sleep_and_vacation(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/5E00", status=200, body="000A0014001E")
        mocked.get("http://device/api/rest/6600", status=200, body="05")
        mocked.get("http://device/api/rest/5600", status=200, body="")
        mocked.get("http://device/api/rest/5600", status=200, body="02")
        mocked.get("http://device/api/rest/6500", status=200, body="01")
        mocked.get("http://device/api/rest/5F00000A0014001E", status=200, body="")
        mocked.get("http://device/api/rest/500100C8012C0190", status=200, body="")
        mocked.get("http://device/api/rest/5301", status=200, body="")
        mocked.get("http://device/api/rest/530A", status=200, body="")
        mocked.get("http://device/api/rest/5603", status=200, body="")
        mocked.get("http://device/api/rest/5B02", status=200, body="")

        limits = run_async(client.read_absence_limits())
        run_async(client.write_absence_limits(10, 20, 30))
        run_async(client.write_leak_preset(1, 200, 300, 400))
        run_async(client.set_sleep_hours(1))
        run_async(client.set_sleep_hours(10))
        sleep_hours = run_async(client.get_sleep_hours())
        run_async(client.set_vacation_type(0))
        run_async(client.set_vacation_type(3))
        vacation_type = run_async(client.get_vacation_type())
        run_async(client.set_micro_leak_mode(2))
        micro_mode = run_async(client.get_micro_leak_mode())

    assert limits.max_flow_l_h == 10
    assert limits.max_volume_l == 20
    assert limits.max_duration_min == 30
    assert sleep_hours == 5
    assert vacation_type == 2
    assert micro_mode == 1

    assert ("GET", "http://device/api/rest/5F00000A0014001E") in mocked.requests
    assert ("GET", "http://device/api/rest/500100C8012C0190") in mocked.requests
    assert ("GET", "http://device/api/rest/530A") in mocked.requests
    assert len(mocked.requests[("GET", "http://device/api/rest/5600")]) == 2
    assert ("GET", "http://device/api/rest/5B02") in mocked.requests

def test_invalid_sleep_hours(client: ZewaClient, run_async) -> None:
    with pytest.raises(ValueError):
        run_async(client.set_sleep_hours(0))
    with pytest.raises(ValueError):
        run_async(client.set_sleep_hours(11))


def test_invalid_vacation_type(client: ZewaClient, run_async) -> None:
    with pytest.raises(ValueError):
        run_async(client.set_vacation_type(-1))
    with pytest.raises(ValueError):
        run_async(client.set_vacation_type(4))


def test_invalid_micro_mode(client: ZewaClient, run_async) -> None:
    with pytest.raises(ValueError):
        run_async(client.set_micro_leak_mode(-1))
    with pytest.raises(ValueError):
        run_async(client.set_micro_leak_mode(3))
