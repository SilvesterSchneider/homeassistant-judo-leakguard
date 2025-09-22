from datetime import datetime, timezone

import pytest
from aioresponses import aioresponses

from zewa_client.client import ZewaClient
from zewa_client.hex import to_u16be, to_u32be, to_u8


def test_clock_and_stats(client: ZewaClient, run_async) -> None:
    clock_dt = datetime(2023, 10, 9, 11, 12, 13, tzinfo=timezone.utc)
    day = datetime(2024, 1, 2, tzinfo=timezone.utc)
    day_key = int(day.timestamp())
    day_payload = to_u32be(day_key).hex().upper()
    week_payload = (to_u8(12) + to_u16be(2024)).hex().upper()
    month_payload = (to_u8(5) + to_u16be(2024)).hex().upper()
    year_payload = to_u16be(2023).hex().upper()

    day_values = [1, 2, 3, 4, 5, 6, 7, 8]
    week_values = [10, 20, 30, 40, 50, 60, 70]
    month_values = list(range(1, 6))
    year_values = [100 * i for i in range(1, 13)]

    with aioresponses() as mocked:
        mocked.get("http://device/api/rest/5900", status=200, body="090A170B0C0D")
        mocked.get("http://device/api/rest/5A090A170B0C0D", status=200, body="")
        mocked.get(f"http://device/api/rest/FB{day_payload}", status=200, body="".join(f"{v:08X}" for v in day_values))
        mocked.get(f"http://device/api/rest/FC{week_payload}", status=200, body="".join(f"{v:08X}" for v in week_values))
        mocked.get(f"http://device/api/rest/FD{month_payload}", status=200, body="".join(f"{v:08X}" for v in month_values))
        mocked.get(f"http://device/api/rest/FE{year_payload}", status=200, body="".join(f"{v:08X}" for v in year_values))

        clock = run_async(client.get_clock())
        run_async(client.set_clock(clock_dt))
        day_stats = run_async(client.get_day_stats(day))
        week_stats = run_async(client.get_week_stats(12, 2024))
        month_stats = run_async(client.get_month_stats(5, 2024))
        year_stats = run_async(client.get_year_stats(2023))

    assert clock.day == 9
    assert clock.month == 10
    assert clock.year == 2023
    assert clock.hour == 11
    assert clock.minute == 12
    assert clock.second == 13
    assert clock.as_datetime() == clock_dt

    assert day_stats.day_key == day_key
    assert day_stats.values == tuple(day_values)
    assert week_stats.week == 12
    assert week_stats.year == 2024
    assert week_stats.values == tuple(week_values)
    assert month_stats.month == 5
    assert month_stats.year == 2024
    assert month_stats.values == tuple(month_values)
    assert year_stats.year == 2023
    assert year_stats.values == tuple(year_values)

    assert ("GET", "http://device/api/rest/5A090A170B0C0D") in mocked.requests
