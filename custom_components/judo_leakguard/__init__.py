from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JudoLeakguardApi
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_PORT, CONF_PROTOCOL, CONF_VERIFY_SSL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]


class JudoLeakguardCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: JudoLeakguardApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
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

    protocol: str = entry.data.get(CONF_PROTOCOL, "http")
    port: int | None = entry.data.get(CONF_PORT)
    verify_ssl: bool = entry.data.get(CONF_VERIFY_SSL, True)

    if port:
        base_url = f"{protocol}://{host}:{port}"
    else:
        base_url = f"{protocol}://{host}"

    session = async_get_clientsession(hass)
    api = JudoLeakguardApi(session=session, base_url=base_url, verify_ssl=verify_ssl)

    coordinator = JudoLeakguardCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "client": api,
        "base_url": base_url,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_if_options_changed))
    _LOGGER.debug("Setup complete for %s at %s", DOMAIN, base_url)
    return True


async def _async_reload_if_options_changed(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
