from __future__ import annotations

from datetime import datetime, timezone

import pytest

from homeassistant.helpers import device_registry as dr

from custom_components.judo_leakguard import (
    SERVICE_CLEAR_ABSENCE,
    SERVICE_SET_ABSENCE,
    SERVICE_SET_DATETIME,
)
from custom_components.judo_leakguard.const import DOMAIN

@pytest.mark.usefixtures("mock_judo_api")
async def test_domain_services_route_calls(hass, setup_integration) -> None:
    api = setup_integration["api"]
    entry = setup_integration["entry"]
    device_registry = dr.async_get(hass)
    device_id = next(iter(device_registry.devices))

    target_dt = datetime(2024, 3, 2, 1, 2, 3, tzinfo=timezone.utc)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_DATETIME,
        {"config_entry_id": entry.entry_id, "datetime": target_dt},
        blocking=True,
    )
    assert api.datetime_writes[-1].isoformat() == target_dt.isoformat()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_ABSENCE,
        {
            "device_id": device_id,
            "slot": 2,
            "start_day": 1,
            "start_hour": 6,
            "start_minute": 30,
            "end_day": 3,
            "end_hour": 7,
            "end_minute": 45,
        },
        blocking=True,
    )
    record = api.absence_schedule_writes[-1]
    assert record.slot == 2
    assert record.start_day == 1
    assert record.end_minute == 45

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_ABSENCE,
        {"device_id": device_id, "slot": 2},
        blocking=True,
    )
    assert api.absence_schedule_deletes[-1] == 2
