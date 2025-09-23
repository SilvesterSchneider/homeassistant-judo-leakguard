from __future__ import annotations

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN
from custom_components.judo_leakguard.select import MicroLeakMode, VacationType


@pytest.mark.usefixtures("mock_judo_api")
@pytest.mark.parametrize(
    ("option", "expected_index"),
    [("off", 0), ("u1", 1), ("u2", 2), ("u3", 3)],
)
async def test_vacation_select_options(
    hass,
    setup_integration,
    option: str,
    expected_index: int,
) -> None:
    api = setup_integration["api"]
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, f"{api.data['serial']}_vacation_type")
    assert entity_id is not None

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": option},
        blocking=True,
    )
    assert api.vacation_type_writes[-1] == expected_index
    assert hass.states.get(entity_id).state == option


@pytest.mark.usefixtures("mock_judo_api")
@pytest.mark.parametrize(
    ("option", "expected_index"),
    [("off", 0), ("notify", 1), ("notify_close", 2)],
)
async def test_microleak_select_options(
    hass,
    setup_integration,
    option: str,
    expected_index: int,
) -> None:
    api = setup_integration["api"]
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, f"{api.data['serial']}_microleak_mode")
    assert entity_id is not None

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": option},
        blocking=True,
    )
    assert api.microleak_writes[-1] == expected_index
    assert hass.states.get(entity_id).state == option


@pytest.mark.usefixtures("mock_judo_api")
async def test_select_entities_handle_invalid_values(setup_integration) -> None:
    coordinator = setup_integration["coordinator"]
    entry = setup_integration["entry"]
    client = setup_integration["api"]

    vac_entity = VacationType(coordinator, client, entry)
    coordinator.data["vacation_type"] = "invalid"
    assert vac_entity.current_option is None
    coordinator.data["vacation_type"] = 99
    assert vac_entity.current_option is None
    with pytest.raises(ValueError):
        await vac_entity.async_select_option("unsupported")

    leak_entity = MicroLeakMode(coordinator, client, entry)
    coordinator.data["microleak_mode"] = "oops"
    assert leak_entity.current_option is None
    coordinator.data["microleak_mode"] = 42
    assert leak_entity.current_option is None
    with pytest.raises(ValueError):
        await leak_entity.async_select_option("invalid")
