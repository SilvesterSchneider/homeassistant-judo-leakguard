from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Mapping, Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    JudoApiError,
    JudoLeakguardApi,
)
from .const import (
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_SEND_AS_QUERY,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .helpers import extract_serial

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]

SERVICE_SET_DATETIME = "set_datetime"
SERVICE_SET_ABSENCE = "set_absence_schedule"
SERVICE_CLEAR_ABSENCE = "clear_absence_schedule"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DEVICE_ID = "device_id"
ATTR_DATETIME = "datetime"
ATTR_SLOT = "slot"
ATTR_START_DAY = "start_day"
ATTR_START_HOUR = "start_hour"
ATTR_START_MINUTE = "start_minute"
ATTR_END_DAY = "end_day"
ATTR_END_HOUR = "end_hour"
ATTR_END_MINUTE = "end_minute"

BASE_SERVICE_FIELDS: dict[Any, Any] = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Optional(ATTR_DEVICE_ID): cv.string,
}

SERVICE_SET_DATETIME_SCHEMA = vol.Schema(
    {**BASE_SERVICE_FIELDS, vol.Required(ATTR_DATETIME): cv.datetime}
)

SERVICE_SET_ABSENCE_SCHEMA = vol.Schema(
    {
        **BASE_SERVICE_FIELDS,
        vol.Required(ATTR_SLOT): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required(ATTR_START_DAY): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required(ATTR_START_HOUR): vol.All(int, vol.Range(min=0, max=23)),
        vol.Required(ATTR_START_MINUTE): vol.All(int, vol.Range(min=0, max=59)),
        vol.Required(ATTR_END_DAY): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required(ATTR_END_HOUR): vol.All(int, vol.Range(min=0, max=23)),
        vol.Required(ATTR_END_MINUTE): vol.All(int, vol.Range(min=0, max=59)),
    }
)

SERVICE_CLEAR_ABSENCE_SCHEMA = vol.Schema(
    {**BASE_SERVICE_FIELDS, vol.Required(ATTR_SLOT): vol.All(int, vol.Range(min=0, max=6))}
)


def _as_local_datetime(dt_value: datetime) -> datetime:
    """Return ``dt_value`` converted to Home Assistant's local timezone."""

    tz = dt_util.DEFAULT_TIME_ZONE
    if dt_value.tzinfo is None:
        if hasattr(tz, "localize"):
            return tz.localize(dt_value)  # type: ignore[attr-defined]
        return dt_value.replace(tzinfo=tz)
    return dt_value.astimezone(tz)


def _find_entry_id_by_serial(
    hass_data: Dict[str, Dict[str, Any]],
    serial: str,
) -> str | None:
    """Find the config entry that matches ``serial``."""

    serial_upper = serial.upper()
    for entry_id, entry_data in hass_data.items():
        stored_serial = entry_data.get("serial")
        if stored_serial is None:
            coordinator = entry_data.get("coordinator")
            if coordinator is not None:
                entry_data["serial"] = str(
                    extract_serial(getattr(coordinator, "data", None))
                ).upper()
                stored_serial = entry_data["serial"]
        if stored_serial and str(stored_serial).upper() == serial_upper:
            return entry_id
    return None


def _resolve_entry_id(hass: HomeAssistant, data: Mapping[str, Any]) -> str:
    """Determine which config entry should handle a service call."""

    domain_data: Dict[str, Dict[str, Any]] | None = hass.data.get(DOMAIN)
    if not domain_data:
        raise HomeAssistantError("JUDO Leakguard is not configured")

    entry_id = data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        if entry_id not in domain_data:
            raise HomeAssistantError(f"Unknown config_entry_id: {entry_id}")
        return entry_id

    device_id = data.get(ATTR_DEVICE_ID)
    if device_id:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device is None:
            raise HomeAssistantError(f"Device {device_id} not found")
        serial_identifier: str | None = None
        for domain, identifier in device.identifiers:
            if domain == DOMAIN:
                serial_identifier = str(identifier)
                break
        if serial_identifier is None:
            raise HomeAssistantError("Device is not managed by JUDO Leakguard")
        entry_id = _find_entry_id_by_serial(domain_data, serial_identifier)
        if entry_id is None:
            raise HomeAssistantError("No config entry matches the selected device")
        return entry_id

    if len(domain_data) == 1:
        return next(iter(domain_data))

    raise HomeAssistantError(
        "Multiple JUDO Leakguard devices configured. Specify config_entry_id or device_id."
    )


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register domain services once."""

    if hass.services.has_service(DOMAIN, SERVICE_SET_DATETIME):
        return

    async def _handle_set_datetime(call: ServiceCall) -> None:
        entry_id = _resolve_entry_id(hass, call.data)
        entry_data = hass.data[DOMAIN][entry_id]
        api: JudoLeakguardApi = entry_data["api"]
        coordinator: JudoLeakguardCoordinator = entry_data["coordinator"]
        dt_value: datetime = call.data[ATTR_DATETIME]
        dt_local = _as_local_datetime(dt_value)
        try:
            await api.write_device_time(dt_local)
        except JudoApiError as exc:
            raise HomeAssistantError(f"Failed to set device time: {exc}") from exc
        await coordinator.async_request_refresh()

    async def _handle_set_absence(call: ServiceCall) -> None:
        entry_id = _resolve_entry_id(hass, call.data)
        entry_data = hass.data[DOMAIN][entry_id]
        api: JudoLeakguardApi = entry_data["api"]
        coordinator: JudoLeakguardCoordinator = entry_data["coordinator"]
        try:
            await api.write_absence_time(
                call.data[ATTR_SLOT],
                call.data[ATTR_START_DAY],
                call.data[ATTR_START_HOUR],
                call.data[ATTR_START_MINUTE],
                call.data[ATTR_END_DAY],
                call.data[ATTR_END_HOUR],
                call.data[ATTR_END_MINUTE],
            )
        except JudoApiError as exc:
            raise HomeAssistantError(f"Failed to set absence schedule: {exc}") from exc
        await coordinator.async_request_refresh()

    async def _handle_clear_absence(call: ServiceCall) -> None:
        entry_id = _resolve_entry_id(hass, call.data)
        entry_data = hass.data[DOMAIN][entry_id]
        api: JudoLeakguardApi = entry_data["api"]
        coordinator: JudoLeakguardCoordinator = entry_data["coordinator"]
        try:
            await api.delete_absence_time(call.data[ATTR_SLOT])
        except JudoApiError as exc:
            raise HomeAssistantError(f"Failed to clear absence schedule: {exc}") from exc
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DATETIME,
        _handle_set_datetime,
        schema=SERVICE_SET_DATETIME_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ABSENCE,
        _handle_set_absence,
        schema=SERVICE_SET_ABSENCE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ABSENCE,
        _handle_clear_absence,
        schema=SERVICE_CLEAR_ABSENCE_SCHEMA,
    )


def _unregister_services(hass: HomeAssistant) -> None:
    """Remove domain services when the last entry is unloaded."""

    for service in (SERVICE_SET_DATETIME, SERVICE_SET_ABSENCE, SERVICE_CLEAR_ABSENCE):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


class JudoLeakguardCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: JudoLeakguardApi, update_interval: timedelta) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            data = await self.api.fetch_all()
            if not isinstance(data, dict) or not data:
                raise UpdateFailed("Empty or invalid payload from API")
            return data
        except Exception as err:
            raise UpdateFailed(f"API error: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    host: str = entry.data.get(CONF_HOST) or entry.options.get(CONF_HOST)
    if not host:
        _LOGGER.error("No host configured for %s", DOMAIN)
        return False

    protocol: str = entry.data.get(CONF_PROTOCOL, entry.options.get(CONF_PROTOCOL, "http"))
    port: int | None = entry.data.get(CONF_PORT)
    if port is None:
        port = entry.options.get(CONF_PORT)
    verify_ssl: Optional[bool] = entry.data.get(CONF_VERIFY_SSL)
    if verify_ssl is None:
        verify_ssl = entry.options.get(CONF_VERIFY_SSL, True)
    verify_ssl = bool(verify_ssl)

    username: Optional[str] = entry.data.get(CONF_USERNAME) or entry.options.get(CONF_USERNAME)
    password: Optional[str] = entry.data.get(CONF_PASSWORD) or entry.options.get(CONF_PASSWORD)
    if not username or not password:
        _LOGGER.error("Missing credentials for %s", DOMAIN)
        return False

    send_as_query = entry.data.get(CONF_SEND_AS_QUERY)
    if send_as_query is None:
        send_as_query = entry.options.get(CONF_SEND_AS_QUERY, False)
    send_as_query = bool(send_as_query)

    if port:
        base_url = f"{protocol}://{host}:{port}"
    else:
        base_url = f"{protocol}://{host}"

    session = async_get_clientsession(hass)
    api = JudoLeakguardApi(
        session=session,
        base_url=base_url,
        verify_ssl=verify_ssl,
        username=username,
        password=password,
        send_as_query=send_as_query,
    )

    # Optionales Scan-Intervall aus Optionen (Fallback auf DEFAULT_SCAN_INTERVAL)
    scan_seconds = entry.options.get("scan_interval_seconds", int(DEFAULT_SCAN_INTERVAL.total_seconds()))
    update_interval = timedelta(seconds=scan_seconds)

    coordinator = JudoLeakguardCoordinator(hass, api, update_interval)
    await coordinator.async_config_entry_first_refresh()

    entry_data: Dict[str, Any] = {
        "coordinator": coordinator,
        "api": api,
        "client": api,
        "base_url": base_url,
        "send_as_query": send_as_query,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data

    def _update_serial() -> None:
        entry_data["serial"] = str(extract_serial(coordinator.data)).upper()

    _update_serial()
    entry.async_on_unload(coordinator.async_add_listener(_update_serial))

    await _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_if_options_changed))
    _LOGGER.debug("Setup complete for %s at %s (interval=%ss)", DOMAIN, base_url, scan_seconds)
    return True


async def _async_reload_if_options_changed(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_entries = hass.data.get(DOMAIN, {})
        domain_entries.pop(entry.entry_id, None)
        if not domain_entries:
            _unregister_services(hass)
    return unload_ok
