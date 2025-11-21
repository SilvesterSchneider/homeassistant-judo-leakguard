from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from custom_components.judo_zewa_isafe.const import DOMAIN


async def test_setup_entry(hass: HomeAssistant, setup_integration, mock_client: AsyncMock):
    data = hass.data[DOMAIN][setup_integration.entry_id]
    assert data["coordinator"].data.serial == 123456
    assert len(hass.states.async_entity_ids()) > 0


async def test_unload_entry(hass: HomeAssistant, setup_integration, mock_client: AsyncMock):
    await hass.config_entries.async_remove(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN not in hass.data
    mock_client.close.assert_awaited()
