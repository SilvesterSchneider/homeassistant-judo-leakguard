import pytest
from aioresponses import aioresponses

from zewa_client.client import (
    ZewaAuthenticationError,
    ZewaClient,
    ZewaInvalidCommandError,
    ZewaResponseError,
)


def test_http_error_responses(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/FF00", status=400, body="")
        mocked.get("http://device/api/rest/0600", status=500, body="")

        with pytest.raises(ZewaInvalidCommandError):
            run_async(client.get_device_type())
        with pytest.raises(ZewaInvalidCommandError):
            run_async(client.get_serial())


def test_authentication_error(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/FF00", status=401, body="unauthorized")
        with pytest.raises(ZewaAuthenticationError):
            run_async(client.get_device_type())


def test_invalid_hex_response(client: ZewaClient, run_async) -> None:
    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/0600", status=200, body="GGGG")
        with pytest.raises(ZewaResponseError):
            run_async(client.get_serial())
