import pytest
from aioresponses import aioresponses

from zewa_client import models
from zewa_client.client import ZewaClient


def test_absence_window_read_write_delete(client: ZewaClient, run_async) -> None:
    read_url = "http://device/api/rest/6001"
    write_url = "http://device/api/rest/610101020F03121E"
    delete_url = "http://device/api/rest/620001"
    with aioresponses() as mocked:
        mocked.get(read_url, status=200, body="01020F03121E")
        mocked.get(read_url, status=200, body="000000000000")
        mocked.get(write_url, status=200, body="")
        mocked.get(delete_url, status=200, body="")

        window = run_async(client.get_absence_window(1))
        run_async(client.set_absence_window(window))
        run_async(client.delete_absence_window(1))
        cleared = run_async(client.get_absence_window(1))

    assert window.index == 1
    assert window.start_day == 1
    assert window.start_hour == 2
    assert window.start_minute == 15
    assert window.end_day == 3
    assert window.end_hour == 18
    assert window.end_minute == 30
    assert window.is_configured
    assert not cleared.is_configured

    assert ("GET", write_url) in mocked.requests
    assert ("GET", delete_url) in mocked.requests


def test_absence_window_index_validation(client: ZewaClient, run_async) -> None:
    with pytest.raises(ValueError):
        run_async(client.get_absence_window(-1))
    with pytest.raises(ValueError):
        run_async(client.delete_absence_window(7))
    with pytest.raises(ValueError):
        run_async(client.set_absence_window(models.AbsenceWindow(7, 0, 0, 0, 0, 0, 0)))
