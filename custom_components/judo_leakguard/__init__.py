from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JudoLeakguardApi
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_PORT, CONF_PROTOCOL, CONF_SEND_AS_QUERY, CONF_VERIFY_SSL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


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

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "base_url": base_url,
        "send_as_query": send_as_query,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_if_options_changed))
    _LOGGER.debug("Setup complete for %s at %s (interval=%ss)", DOMAIN, base_url, scan_seconds)
    return True


async def _async_reload_if_options_changed(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
