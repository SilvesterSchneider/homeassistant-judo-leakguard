import aiohttp
import pytest
from aioresponses import aioresponses

from zewa_client.client import ZewaClient


def test_command_endpoints(client: ZewaClient, run_async) -> None:
    commands = [
        ("http://device/api/rest/6300", client.ack_alarm),
        ("http://device/api/rest/5100", client.close_valve),
        ("http://device/api/rest/5200", client.open_valve),
        ("http://device/api/rest/5400", client.sleep_start),
        ("http://device/api/rest/5500", client.sleep_end),
        ("http://device/api/rest/5700", client.vacation_start),
        ("http://device/api/rest/5800", client.vacation_end),
        ("http://device/api/rest/5C00", client.micro_leak_test),
        ("http://device/api/rest/5D00", client.learn_mode_start),
    ]

    with aioresponses() as mocked:
        for url, _ in commands:
            mocked.get(url, status=200, body="")

        for _, method in commands:
            run_async(method())

    for url, _ in commands:
        request_log = mocked.requests[("GET", url)]
        assert len(request_log) == 1
        kwargs = request_log[0].kwargs
        assert kwargs.get("data") is None
        assert isinstance(kwargs.get("auth"), aiohttp.BasicAuth)
