from __future__ import annotations

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.usefixtures("mock_judo_api")
async def test_numbers_track_and_write_limits(hass, setup_integration) -> None:
    api = setup_integration["api"]
    entity_registry = er.async_get(hass)
    serial = api.data["serial"]

    sleep_entity = entity_registry.async_get_entity_id("number", DOMAIN, f"{serial}_sleep_hours")
    flow_entity = entity_registry.async_get_entity_id("number", DOMAIN, f"{serial}_absence_flow")
    volume_entity = entity_registry.async_get_entity_id("number", DOMAIN, f"{serial}_absence_volume")
    duration_entity = entity_registry.async_get_entity_id("number", DOMAIN, f"{serial}_absence_duration")

    assert sleep_entity and flow_entity and volume_entity and duration_entity

    assert hass.states.get(sleep_entity).state == "6"
    assert hass.states.get(flow_entity).state == "240"
    assert hass.states.get(volume_entity).state == "120"
    assert hass.states.get(duration_entity).state == "90"

    await hass.services.async_call("number", "set_value", {"entity_id": sleep_entity, "value": 8}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": flow_entity, "value": 321}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": volume_entity, "value": 654}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": duration_entity, "value": 987}, blocking=True)

    assert api.sleep_duration_writes[-1] == 8
    assert api.absence_limit_writes[-1] == (321, 654, 987)

    assert hass.states.get(sleep_entity).state == "8"
    assert hass.states.get(flow_entity).state == "321"
    assert hass.states.get(volume_entity).state == "654"
    assert hass.states.get(duration_entity).state == "987"


@pytest.mark.usefixtures("mock_judo_api")
@pytest.mark.parametrize(
    ("entity_suffix", "service_value", "expected_index"),
    [
        ("absence_flow", 111, 0),
        ("absence_volume", 222, 1),
        ("absence_duration", 333, 2),
    ],
)
async def test_absence_numbers_parameterized(
    hass,
    setup_integration,
    entity_suffix: str,
    service_value: int,
    expected_index: int,
) -> None:
    api = setup_integration["api"]
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("number", DOMAIN, f"{api.data['serial']}_{entity_suffix}")
    assert entity_id is not None

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": service_value},
        blocking=True,
    )
    assert api.absence_limit_writes[-1][expected_index] == service_value
