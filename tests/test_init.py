from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.judo_leakguard import (
    SERVICE_CLEAR_ABSENCE,
    SERVICE_SET_ABSENCE,
    SERVICE_SET_DATETIME,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DATETIME,
    ATTR_DEVICE_ID,
    ATTR_END_DAY,
    ATTR_END_HOUR,
    ATTR_END_MINUTE,
    ATTR_SLOT,
    ATTR_START_DAY,
    ATTR_START_HOUR,
    ATTR_START_MINUTE,
    _as_local_datetime,
    _async_reload_if_options_changed,
    _find_entry_id_by_serial,
    _resolve_entry_id,
    async_unload_entry,
    async_setup_entry,
    JudoLeakguardCoordinator,
)
from custom_components.judo_leakguard.const import DOMAIN
from custom_components.judo_leakguard.api import JudoApiError


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


def test_as_local_datetime_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyTimezone:
        def localize(self, dt_value: datetime) -> datetime:
            return dt_value.replace(tzinfo=timezone.utc)

    naive = datetime(2024, 1, 2, 3, 4, 5)
    monkeypatch.setattr("custom_components.judo_leakguard.dt_util.DEFAULT_TIME_ZONE", DummyTimezone())
    localized = _as_local_datetime(naive)
    assert localized.tzinfo is timezone.utc

    monkeypatch.setattr(
        "custom_components.judo_leakguard.dt_util.DEFAULT_TIME_ZONE", timezone.utc
    )
    aware = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert _as_local_datetime(aware) == aware


def test_find_entry_id_by_serial_updates_cache() -> None:
    coordinator = SimpleNamespace(data={"device": {"serial": "abc"}})
    hass_data = {"entry-one": {"coordinator": coordinator}}
    assert _find_entry_id_by_serial(hass_data, "abc") == "entry-one"
    assert hass_data["entry-one"]["serial"] == "ABC"
    assert _find_entry_id_by_serial(hass_data, "missing") is None


@pytest.mark.asyncio
async def test_resolve_entry_id_validates_inputs(hass: HomeAssistant) -> None:
    hass.data.pop(DOMAIN, None)
    with pytest.raises(HomeAssistantError):
        _resolve_entry_id(hass, {})

    hass.data[DOMAIN] = {"known": {}}
    with pytest.raises(HomeAssistantError, match="Unknown config_entry_id"):
        _resolve_entry_id(hass, {ATTR_CONFIG_ENTRY_ID: "missing"})

    with pytest.raises(HomeAssistantError, match="Device nonexistent not found"):
        _resolve_entry_id(hass, {ATTR_DEVICE_ID: "nonexistent"})


@pytest.mark.asyncio
async def test_resolve_entry_id_device_lookup(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {"serial": "SN123"}}
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "SN123")},
    )
    assert _resolve_entry_id(hass, {ATTR_DEVICE_ID: device.id}) == mock_config_entry.entry_id

    other = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("other", "id")},
    )
    with pytest.raises(HomeAssistantError, match="Device is not managed"):
        _resolve_entry_id(hass, {ATTR_DEVICE_ID: other.id})

    unmatched = device_registry.async_get_or_create(
        config_entry_id="other",
        identifiers={(DOMAIN, "UNKNOWN")},
    )
    with pytest.raises(HomeAssistantError, match="No config entry matches"):
        _resolve_entry_id(hass, {ATTR_DEVICE_ID: unmatched.id})


def test_resolve_entry_id_defaults_to_single_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {"serial": "SN321"}}
    assert _resolve_entry_id(hass, {}) == mock_config_entry.entry_id

    hass.data[DOMAIN]["second"] = {}
    with pytest.raises(HomeAssistantError, match="Multiple JUDO Leakguard devices"):
        _resolve_entry_id(hass, {})


@pytest.mark.usefixtures("mock_judo_api")
@pytest.mark.asyncio
async def test_services_raise_homeassistant_error_on_api_failure(
    hass: HomeAssistant, setup_integration: dict[str, object]
) -> None:
    entry = setup_integration["entry"]
    api = setup_integration["api"]

    api.write_device_time = AsyncMock(side_effect=JudoApiError("dt fail"))  # type: ignore[assignment]
    with pytest.raises(HomeAssistantError, match="Failed to set device time"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_DATETIME,
            {ATTR_DATETIME: datetime.now(timezone.utc), ATTR_CONFIG_ENTRY_ID: entry.entry_id},
            blocking=True,
        )

    api.write_absence_time = AsyncMock(side_effect=JudoApiError("abs fail"))  # type: ignore[assignment]
    with pytest.raises(HomeAssistantError, match="Failed to set absence"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_ABSENCE,
            {
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
                ATTR_SLOT: 0,
                ATTR_START_DAY: 1,
                ATTR_START_HOUR: 2,
                ATTR_START_MINUTE: 3,
                ATTR_END_DAY: 4,
                ATTR_END_HOUR: 5,
                ATTR_END_MINUTE: 6,
            },
            blocking=True,
        )

    api.delete_absence_time = AsyncMock(side_effect=JudoApiError("clr fail"))  # type: ignore[assignment]
    with pytest.raises(HomeAssistantError, match="Failed to clear absence"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEAR_ABSENCE,
            {ATTR_CONFIG_ENTRY_ID: entry.entry_id, ATTR_SLOT: 1},
            blocking=True,
        )


@pytest.mark.usefixtures("mock_judo_api")
@pytest.mark.asyncio
async def test_coordinator_update_errors(
    hass: HomeAssistant, setup_integration: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator: JudoLeakguardCoordinator = setup_integration["coordinator"]  # type: ignore[assignment]
    api = setup_integration["api"]

    api.fetch_all = AsyncMock(return_value={})  # type: ignore[assignment]
    with pytest.raises(UpdateFailed, match="Empty or invalid"):
        await coordinator._async_update_data()

    api.fetch_all = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[assignment]
    with pytest.raises(UpdateFailed, match="API error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_setup_entry_requires_host(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "user", CONF_PASSWORD: "pass"},
    )
    entry.add_to_hass(hass)
    assert not await async_setup_entry(hass, entry)
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_async_setup_entry_requires_credentials(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "host"})
    entry.add_to_hass(hass)
    assert not await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_async_reload_if_options_changed(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    mock_config_entry.add_to_hass(hass)
    reload_mock = AsyncMock()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_mock)
    await _async_reload_if_options_changed(hass, mock_config_entry)
    reload_mock.assert_awaited_once_with(mock_config_entry.entry_id)
    monkeypatch.undo()
