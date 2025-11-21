from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.judo_zewa_isafe.const import CONF_BASE_URL, DOMAIN
from custom_components.judo_zewa_isafe.coordinator import JudoDataUpdateCoordinator
from zewa_client import models


@pytest.fixture
def mock_absence_limits() -> models.AbsenceLimits:
    return models.AbsenceLimits(150, 250, 350)


@pytest.fixture
def mock_device_clock() -> models.DeviceClock:
    return models.DeviceClock(1, 1, 2024, 12, 0, 0)


@pytest.fixture
def mock_client(mock_absence_limits: models.AbsenceLimits, mock_device_clock: models.DeviceClock):
    client = AsyncMock()
    client.get_device_type.return_value = "ZEWA_I_SAFE"
    client.get_serial.return_value = 123456
    client.get_fw_version.return_value = "01.02.03"
    client.get_commission_date.return_value = datetime(2023, 1, 1, tzinfo=timezone.utc)
    client.get_total_water_l.return_value = 1234
    client.get_sleep_hours.return_value = 6
    client.read_absence_limits.return_value = mock_absence_limits
    client.get_vacation_type.return_value = 2
    client.get_micro_leak_mode.return_value = 1
    client.get_clock.return_value = mock_device_clock
    client.get_learn_status.return_value = (True, 42)
    return client


@pytest.fixture
async def setup_integration(hass: HomeAssistant, mock_client: AsyncMock):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_BASE_URL: "http://example",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
        },
    )
    entry.add_to_hass(hass)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "custom_components.judo_zewa_isafe.__init__.async_create_client",
            AsyncMock(return_value=mock_client),
        )
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


@pytest.fixture
async def coordinator(hass: HomeAssistant, mock_client: AsyncMock) -> JudoDataUpdateCoordinator:
    coordinator = JudoDataUpdateCoordinator(hass, mock_client)
    await coordinator.async_config_entry_first_refresh()
    return coordinator
