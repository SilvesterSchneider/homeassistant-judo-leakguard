from __future__ import annotations

from homeassistant.helpers import entity_registry as er

from custom_components.judo_zewa_isafe.const import DOMAIN


async def _get_entity(hass, domain: str, unique_id: str):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
    component = hass.data["entity_components"][domain]
    return component.entities[entity_id]


async def test_sensor_states(hass, setup_integration):
    registry = er.async_get(hass)
    serial = "123456"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_total_water_l")
    state = hass.states.get(entity_id)
    assert state.state == "1234"

    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_total_water_cubic_m")
    state = hass.states.get(entity_id)
    assert state.state == "1.234"

    entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{serial}_learn_active")
    state = hass.states.get(entity_id)
    assert state.state == "on"


async def test_selects(hass, setup_integration):
    serial = "123456"
    vacation = await _get_entity(hass, "select", f"{serial}_vacation_type")
    assert vacation.current_option == "u2"
    await vacation.async_select_option("u3")
    vacation._client.set_vacation_type.assert_awaited_with(3)

    micro = await _get_entity(hass, "select", f"{serial}_micro_leak_mode")
    assert micro.current_option == "notify"
    await micro.async_select_option("notify_close")
    micro._client.set_micro_leak_mode.assert_awaited_with(2)


async def test_numbers(hass, setup_integration):
    serial = "123456"
    sleep_hours = await _get_entity(hass, "number", f"{serial}_sleep_hours")
    assert sleep_hours.native_value == 6
    await sleep_hours.async_set_native_value(8)
    sleep_hours._client.set_sleep_hours.assert_awaited_with(8)

    flow_limit = await _get_entity(hass, "number", f"{serial}_absence_flow_limit")
    assert flow_limit.native_value == 150
    await flow_limit.async_set_native_value(200)
    flow_limit._client.write_absence_limits.assert_awaited()


async def test_switches(hass, setup_integration):
    serial = "123456"
    valve = await _get_entity(hass, "switch", f"{serial}_valve_open")
    assert valve.is_on is False
    await valve.async_turn_on()
    valve._client.open_valve.assert_awaited()
    assert valve.is_on is True

    await valve.async_turn_off()
    valve._client.close_valve.assert_awaited()
    assert valve.is_on is False


async def test_buttons(hass, setup_integration):
    serial = "123456"
    reset = await _get_entity(hass, "button", f"{serial}_ack_alarm")
    await reset.async_press()
    reset._client.ack_alarm.assert_awaited()
