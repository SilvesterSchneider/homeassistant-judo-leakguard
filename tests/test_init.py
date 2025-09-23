from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.judo_leakguard import (
    SERVICE_CLEAR_ABSENCE,
    SERVICE_SET_ABSENCE,
    SERVICE_SET_DATETIME,
    async_unload_entry,
)
from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.usefixtures("mock_judo_api")
async def test_async_setup_entry_registers_services(
    hass: HomeAssistant,
    setup_integration: dict[str, object],
) -> None:
    assert hass.services.has_service(DOMAIN, SERVICE_SET_DATETIME)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_ABSENCE)
    assert hass.services.has_service(DOMAIN, SERVICE_CLEAR_ABSENCE)

    domain_bucket = hass.data[DOMAIN]
    assert setup_integration["entry"].entry_id in domain_bucket
    stored = domain_bucket[setup_integration["entry"].entry_id]
    assert stored["serial"] == "SN123456"


@pytest.mark.usefixtures("mock_judo_api")
async def test_async_unload_entry_removes_services(
    hass: HomeAssistant,
    setup_integration: dict[str, object],
) -> None:
    entry = setup_integration["entry"]
    assert await async_unload_entry(hass, entry)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, SERVICE_SET_DATETIME)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_ABSENCE)
    assert not hass.services.has_service(DOMAIN, SERVICE_CLEAR_ABSENCE)
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
