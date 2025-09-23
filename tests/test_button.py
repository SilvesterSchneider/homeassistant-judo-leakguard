from __future__ import annotations

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.usefixtures("mock_judo_api")
async def test_button_presses_trigger_commands(hass, setup_integration) -> None:
    api = setup_integration["api"]
    entity_registry = er.async_get(hass)
    serial = api.data["serial"]

    reset_entity = entity_registry.async_get_entity_id("button", DOMAIN, f"{serial}_alarm_reset")
    micro_entity = entity_registry.async_get_entity_id("button", DOMAIN, f"{serial}_microleak_test")
    learn_entity = entity_registry.async_get_entity_id("button", DOMAIN, f"{serial}_learn_start")

    assert reset_entity and micro_entity and learn_entity

    await hass.services.async_call("button", "press", {"entity_id": reset_entity}, blocking=True)
    await hass.services.async_call("button", "press", {"entity_id": micro_entity}, blocking=True)
    await hass.services.async_call("button", "press", {"entity_id": learn_entity}, blocking=True)

    assert api.command_log[-3:] == ["6300", "5C00", "5D00"]
