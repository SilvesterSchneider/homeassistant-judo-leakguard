from __future__ import annotations

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.usefixtures("mock_judo_api")
async def test_switch_commands_and_states(hass, setup_integration) -> None:
    api = setup_integration["api"]
    entity_registry = er.async_get(hass)
    serial = api.data["serial"]

    valve_entity = entity_registry.async_get_entity_id("switch", DOMAIN, f"{serial}_valve")
    sleep_entity = entity_registry.async_get_entity_id("switch", DOMAIN, f"{serial}_sleep_mode")
    vacation_entity = entity_registry.async_get_entity_id("switch", DOMAIN, f"{serial}_vacation_mode")

    assert valve_entity and sleep_entity and vacation_entity

    # Initial states reflect payload
    assert hass.states.get(sleep_entity).state == "off"
    assert hass.states.get(vacation_entity).state == "on"

    await hass.services.async_call("switch", "turn_on", {"entity_id": valve_entity}, blocking=True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": valve_entity}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": sleep_entity}, blocking=True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": sleep_entity}, blocking=True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": vacation_entity}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": vacation_entity}, blocking=True)

    assert "5200" in api.command_log
    assert "5100" in api.command_log
    assert "5400" in api.command_log
    assert "5500" in api.command_log
    assert "5800" in api.command_log
    assert "5700" in api.command_log

    assert hass.states.get(sleep_entity).state == "off"
    assert hass.states.get(vacation_entity).state == "on"
