from __future__ import annotations

import copy
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.judo_leakguard.const import (
    CONF_PROTOCOL,
    CONF_SEND_AS_QUERY,
    CONF_VERIFY_SSL,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically load custom components for every test."""
    yield


@pytest.fixture
def config_entry_data() -> Dict[str, Any]:
    """Return typical config entry payload for the integration."""
    return {
        CONF_HOST: "leakguard.local",
        CONF_PROTOCOL: "http",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "Connectivity",
        CONF_VERIFY_SSL: False,
        CONF_SEND_AS_QUERY: False,
    }


@pytest.fixture
def mock_config_entry(config_entry_data: Dict[str, Any]) -> MockConfigEntry:
    """Provide a fully populated config entry for tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=config_entry_data,
        unique_id="judo_test_serial",
        title="Judo Leakguard (test)",
        version=1,
    )


@pytest.fixture
def sample_api_data() -> Dict[str, Any]:
    """Canonical payload returned by the mocked device API."""
    return {
        "serial": "ABC123",
        "pressure_bar": 3.4,
        "water_flow_l_min": 1.2,
        "total_water_m3": 1.5,
        "total_water_l": 1500,
        "temperature_c": 19.5,
        "battery_percent": 85,
        "last_update_seconds": 12,
        "sleep_hours": 6,
        "absence_flow_l_h": 40,
        "absence_volume_l": 250,
        "absence_duration_min": 45,
        "microleak_mode": 1,
        "vacation_type": 2,
        "learn_active": True,
        "sleep_active": True,
        "vacation_active": False,
        "meta": {
            "manufacturer": "JUDO",
            "model": "Leakguard",
            "serial": "ABC123",
            "firmware": "1.2.3",
        },
    }


@pytest.fixture
async def setup_integration(
    hass,
    monkeypatch,
    mock_config_entry: MockConfigEntry,
    sample_api_data: Dict[str, Any],
):
    """Set up the integration with a mocked API client and return it."""
    api = MagicMock()

    def _make_payload() -> Dict[str, Any]:
        return copy.deepcopy(sample_api_data)

    api.fetch_all = AsyncMock(side_effect=_make_payload)
    api.action_no_payload = AsyncMock()
    api.write_sleep_duration = AsyncMock()
    api.write_absence_limits = AsyncMock()
    api.write_vacation_type = AsyncMock()
    api.write_microleak_mode = AsyncMock()
    api.write_absence_time = AsyncMock()
    api.delete_absence_time = AsyncMock()
    api.write_leak_settings = AsyncMock()

    monkeypatch.setattr(
        "custom_components.judo_leakguard.__init__.JudoLeakguardApi",
        MagicMock(return_value=api),
    )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    yield mock_config_entry, api

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    if entry and entry.state == ConfigEntryState.LOADED:
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

