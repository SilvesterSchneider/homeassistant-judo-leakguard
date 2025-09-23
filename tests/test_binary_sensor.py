from __future__ import annotations

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.usefixtures("mock_judo_api")
async def test_binary_sensor_updates_with_coordinator(hass, setup_integration) -> None:
    api = setup_integration["api"]
    coordinator = setup_integration["coordinator"]
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{api.data['serial']}_learn_active")
    assert entity_id is not None

    assert hass.states.get(entity_id).state == "on"

    api.data["learn_active"] = False
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "off"
