from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.judo_leakguard.api import JudoClient


@pytest.fixture
def client() -> JudoClient:
    return JudoClient(MagicMock(), "http://device")


@pytest.mark.asyncio
async def test_total_water_parsing(client: JudoClient) -> None:
    client._rest_bytes = AsyncMock(return_value=b"\x12\x34\x56\x78")  # type: ignore[attr-defined]
    result = await client.read_total_water()
    assert result is not None
    assert result.liters == 0x12345678
    assert result.to_dict()["total_water_m3"] == pytest.approx(0x12345678 / 1000.0)


@pytest.mark.asyncio
async def test_absence_limits_parsing(client: JudoClient) -> None:
    client._rest_bytes = AsyncMock(return_value=b"\x00\x64\x01\x2C\x03\xE8")  # type: ignore[attr-defined]
    limits = await client.read_absence_limits()
    assert limits is not None
    assert limits.flow_l_h == 100
    assert limits.volume_l == 300
    assert limits.duration_min == 1000


@pytest.mark.asyncio
@pytest.mark.parametrize("payload, expected", [(b"", None), (b"\x00", 0), (b"\x01", 1), (b"\xFF", 255)])
async def test_sleep_duration_values(client: JudoClient, payload: bytes, expected: int | None) -> None:
    client._rest_bytes = AsyncMock(return_value=payload)  # type: ignore[attr-defined]
    result = await client.read_sleep_duration()
    assert result == expected


@pytest.mark.asyncio
async def test_learn_status_parsing(client: JudoClient) -> None:
    client._rest_bytes = AsyncMock(return_value=b"\x01\x03\xE8")  # type: ignore[attr-defined]
    status = await client.read_learn_status()
    assert status is not None
    assert status.active is True
    assert status.remaining_l == 1000


@pytest.mark.asyncio
async def test_device_clock_parsing(client: JudoClient) -> None:
    client._rest_bytes = AsyncMock(return_value=bytes([2, 3, 24, 10, 45, 30]))  # type: ignore[attr-defined]
    clock = await client.read_device_time()
    assert clock is not None
    assert clock.day == 2
    assert clock.month == 3
    assert clock.year == 2024
    assert clock.hour == 10
    assert clock.minute == 45
    assert clock.second == 30
    assert clock.as_datetime().year == 2024


@pytest.mark.asyncio
async def test_statistics_parsing(client: JudoClient) -> None:
    client._rest_bytes = AsyncMock(return_value=b"\x00\x00\x00\x01\x00\x00\x00\x02")  # type: ignore[attr-defined]
    assert await client.read_day_stats(1, 1, 2024) == [1, 2]

    client._rest_bytes = AsyncMock(return_value=b"\x00\x00\x03\xE8" * 7)  # type: ignore[attr-defined]
    assert await client.read_week_stats(12, 2024) == [1000] * 7

    client._rest_bytes = AsyncMock(return_value=b"\x00\x00\x00\x64" * 4)  # type: ignore[attr-defined]
    assert await client.read_month_stats(5, 2024) == [100] * 4

    client._rest_bytes = AsyncMock(return_value=b"\x00\x00\x01\xF4" * 12)  # type: ignore[attr-defined]
    assert await client.read_year_stats(2024) == [500] * 12
