"""JUDO ZEWA i-SAFE Home Assistant Integration."""
from __future__ import annotations

import logging
from datetime import datetime

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
import homeassistant.helpers.aiohttp_client as hass_aiohttp

from .api import AbsenceWindow, JudoApiClient
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import JudoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service-Schema: Abwesenheitszeitraum setzen
SERVICE_SET_ABSENCE_SCHEDULE = "set_absence_schedule"
SERVICE_CLEAR_ABSENCE_SCHEDULE = "clear_absence_schedule"
SERVICE_SET_DATETIME = "set_datetime"

SET_ABSENCE_SCHEMA = vol.Schema(
    {
        vol.Required("index"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("start_day"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("start_hour"): vol.All(int, vol.Range(min=0, max=23)),
        vol.Required("start_minute"): vol.All(int, vol.Range(min=0, max=59)),
        vol.Required("stop_day"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("stop_hour"): vol.All(int, vol.Range(min=0, max=23)),
        vol.Required("stop_minute"): vol.All(int, vol.Range(min=0, max=59)),
    }
)

CLEAR_ABSENCE_SCHEMA = vol.Schema(
    {vol.Required("index"): vol.All(int, vol.Range(min=0, max=6))}
)

SET_DATETIME_SCHEMA = vol.Schema(
    {vol.Required("datetime"): cv.datetime}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setzt einen ConfigEntry auf."""
    session = hass_aiohttp.async_get_clientsession(hass)
    client = JudoApiClient(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
    )

    coordinator = JudoDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Services registrieren ──────────────────────────────────────────────

    async def handle_set_absence_schedule(call: ServiceCall) -> None:
        window = AbsenceWindow(
            index=call.data["index"],
            start_day=call.data["start_day"],
            start_hour=call.data["start_hour"],
            start_minute=call.data["start_minute"],
            stop_day=call.data["stop_day"],
            stop_hour=call.data["stop_hour"],
            stop_minute=call.data["stop_minute"],
        )
        try:
            await client.write_absence_schedule(window)
        except Exception as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def handle_clear_absence_schedule(call: ServiceCall) -> None:
        try:
            await client.delete_absence_schedule(call.data["index"])
        except Exception as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def handle_set_datetime(call: ServiceCall) -> None:
        dt: datetime = call.data["datetime"]
        try:
            await client.set_datetime(dt)
        except Exception as exc:
            raise HomeAssistantError(str(exc)) from exc

    if not hass.services.has_service(DOMAIN, SERVICE_SET_ABSENCE_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ABSENCE_SCHEDULE,
            handle_set_absence_schedule,
            schema=SET_ABSENCE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_ABSENCE_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_ABSENCE_SCHEDULE,
            handle_clear_absence_schedule,
            schema=CLEAR_ABSENCE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DATETIME):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_DATETIME,
            handle_set_datetime,
            schema=SET_DATETIME_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlädt einen ConfigEntry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
