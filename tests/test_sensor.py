from __future__ import annotations

from datetime import datetime

import pytest

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN
from custom_components.judo_leakguard.sensor import SENSOR_DESCRIPTIONS

from .helpers import SERIAL


@pytest.mark.usefixtures("mock_judo_api")
async def test_sensor_entities_have_unique_ids(
    hass,
    setup_integration,
) -> None:
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    serial = SERIAL

    for description in SENSOR_DESCRIPTIONS:
        unique_id = f"{serial}_{description.key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id, f"Missing entity for {description.key}"
        entry = entity_registry.async_get(entity_id)
        assert entry is not None
        assert entry.unique_id == unique_id
        assert entry.device_id is not None
        device = device_registry.async_get(entry.device_id)
        assert device is not None
        assert (DOMAIN, serial) in device.identifiers


@pytest.mark.usefixtures("mock_judo_api")
async def test_sensor_states_match_payload(hass, setup_integration) -> None:
    entity_registry = er.async_get(hass)
    data = setup_integration["api"].data
    serial = data["serial"]

    for description in SENSOR_DESCRIPTIONS:
        unique_id = f"{serial}_{description.key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None

        expected = None
        for path in description.paths or (description.key,):
            parts = path.split(".")
            cursor = data
            for part in parts:
                if isinstance(cursor, dict) and part in cursor:
                    cursor = cursor[part]
                else:
                    cursor = None
                    break
            if cursor is not None:
                expected = cursor
                break

        if expected is None:
            assert state.state == STATE_UNKNOWN
            continue

        if isinstance(expected, datetime):
            assert state.state == expected.isoformat()
        elif isinstance(expected, float):
            assert float(state.state) == pytest.approx(expected)
        else:
            assert state.state == str(expected)

        if description.native_unit_of_measurement:
            assert (
                state.attributes.get("unit_of_measurement")
                == description.native_unit_of_measurement
            )
        if description.device_class:
            assert state.attributes.get("device_class") == description.device_class
        if description.state_class:
            assert state.attributes.get("state_class") == description.state_class
