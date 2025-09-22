import pytest
from aioresponses import aioresponses

from zewa_client.client import ZewaClient


def test_example_open_close_valve(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/5200", status=200, body="")
        mocked.get("http://device/api/rest/5100", status=200, body="")
        run_async(client.open_valve())
        run_async(client.close_valve())
    assert ("GET", "http://device/api/rest/5200") in mocked.requests
    assert ("GET", "http://device/api/rest/5100") in mocked.requests


def test_example_configure_sleep(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/5306", status=200, body="")
        mocked.get("http://device/api/rest/5400", status=200, body="")
        run_async(client.set_sleep_hours(6))
        run_async(client.sleep_start())
    assert ("GET", "http://device/api/rest/5306") in mocked.requests
    assert ("GET", "http://device/api/rest/5400") in mocked.requests


def test_example_write_limits(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/5F00001E0002000F", status=200, body="")
        mocked.get("http://device/api/rest/5002009601F4005A", status=200, body="")
        run_async(client.write_absence_limits(30, 2, 15))
        run_async(client.write_leak_preset(2, 150, 500, 90))
    assert ("GET", "http://device/api/rest/5F00001E0002000F") in mocked.requests
    assert ("GET", "http://device/api/rest/5002009601F4005A") in mocked.requests
