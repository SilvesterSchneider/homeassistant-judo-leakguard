from datetime import datetime, timezone

import pytest
from aioresponses import aioresponses

from zewa_client.client import ZewaClient


def test_core_reads(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/FF00", status=200, body="44")
        mocked.get("http://device/api/rest/0600", status=200, body="00112233")
        mocked.get("http://device/api/rest/0100", status=200, body="010203")
        mocked.get("http://device/api/rest/0E00", status=200, body="6566A680")
        mocked.get("http://device/api/rest/2800", status=200, body="000F4240")

        device_type = run_async(client.get_device_type())
        serial = run_async(client.get_serial())
        fw_version = run_async(client.get_fw_version())
        commission = run_async(client.get_commission_date())
        total_water = run_async(client.get_total_water_l())

    assert device_type == "ZEWA_I_SAFE"
    assert serial == 0x00112233
    assert fw_version == "01.02.03"
    assert commission == datetime.fromtimestamp(0x6566A680, tz=timezone.utc)
    assert total_water == 1_000_000

    assert len(mocked.requests[("GET", "http://device/api/rest/FF00")]) == 1
