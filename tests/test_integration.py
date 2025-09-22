from __future__ import annotations


import pytest
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.judo_leakguard.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_creates_entities(hass, setup_integration, sample_api_data):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)

    # Verify sensor entity is registered with unique id and state
    sensor_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{sample_api_data['serial']}_pressure_bar")
    assert sensor_id is not None
    state = hass.states.get(sensor_id)
    assert state is not None
    assert float(state.state) == pytest.approx(sample_api_data["pressure_bar"])

    # Device registry should contain the Leakguard device
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device({(DOMAIN, sample_api_data["serial"])})
    assert device is not None
    assert device.manufacturer == "JUDO"
    assert device.model == "Leakguard"
    assert device.sw_version == "1.2.3"


@pytest.mark.asyncio
async def test_button_calls_api(hass, setup_integration):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)
    button_id = ent_reg.async_get_entity_id("button", DOMAIN, "ABC123_alarm_reset")
    assert button_id is not None

    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: button_id},
        blocking=True,
    )

    api.action_no_payload.assert_awaited_once_with("6300")


@pytest.mark.asyncio
async def test_switch_turns_on_and_off(hass, setup_integration):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)
    switch_id = ent_reg.async_get_entity_id("switch", DOMAIN, "ABC123_sleep_mode")
    assert switch_id is not None

    await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: switch_id}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: switch_id}, blocking=True)

    called = [call.args[0] for call in api.action_no_payload.await_args_list]
    assert "5500" in called
    assert "5400" in called


@pytest.mark.asyncio
async def test_number_updates_limits(hass, setup_integration):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)
    flow_id = ent_reg.async_get_entity_id("number", DOMAIN, "ABC123_absence_flow")
    assert flow_id is not None

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: flow_id, "value": 55},
        blocking=True,
    )

    api.write_absence_limits.assert_awaited_once_with(55, 250, 45)


@pytest.mark.asyncio
async def test_sleep_hours_number_calls_api(hass, setup_integration):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)
    hours_id = ent_reg.async_get_entity_id("number", DOMAIN, "ABC123_sleep_hours")
    assert hours_id is not None

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: hours_id, "value": 8},
        blocking=True,
    )

    api.write_sleep_duration.assert_awaited_once_with(8)


@pytest.mark.asyncio
async def test_select_updates_modes(hass, setup_integration):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)
    vac_id = ent_reg.async_get_entity_id("select", DOMAIN, "ABC123_vacation_type")
    micro_id = ent_reg.async_get_entity_id("select", DOMAIN, "ABC123_microleak_mode")
    assert vac_id is not None
    assert micro_id is not None

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: vac_id, "option": "U3"},
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: micro_id, "option": "notify_close"},
        blocking=True,
    )

    api.write_vacation_type.assert_awaited_once_with(3)
    api.write_microleak_mode.assert_awaited_once_with(2)


@pytest.mark.asyncio
async def test_unload_cleans_up(hass, setup_integration):
    entry, api = setup_integration
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})

@pytest.mark.asyncio
async def test_coordinator_refresh_updates_state(hass, setup_integration, sample_api_data):
    entry, api = setup_integration
    ent_reg = er.async_get(hass)
    sensor_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{sample_api_data['serial']}_pressure_bar")
    assert sensor_id is not None
    initial = hass.states.get(sensor_id)
    assert initial is not None

    updated = dict(sample_api_data)
    updated["pressure_bar"] = 5.6

    api.fetch_all.reset_mock()
    api.fetch_all.return_value = updated

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(sensor_id)
    assert state is not None
    assert float(state.state) == pytest.approx(5.6)
