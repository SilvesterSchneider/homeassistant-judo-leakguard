from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import JudoClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.BUTTON, Platform.NUMBER, Platform.SELECT]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    client = JudoClient(
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
        use_https=entry.data.get("https", False),
        verify_ssl=entry.data.get("verify_ssl", True),
        send_data_as_query=entry.data.get("send_data_as_query", False),
    )

    async def _update():
        total = await client.get_total_liters()
        fw = await client.get_fw()
        dt = await client.read_datetime()
        sleep_h = await client.read_sleep_duration()
        learn_active, learn_rem = await client.read_learn_status()
        micro = await client.read_microleak_mode()
        limits = await client.read_absence_limits()
        return {
            "total_l": total,
            "fw": fw,
            "datetime": dt,
            "sleep_h": sleep_h,
            "learn_active": learn_active,
            "learn_remaining": learn_rem,
            "micro": micro,
            "limits": limits,
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="judo_leakguard",
        update_method=_update,
        update_interval=timedelta(seconds=60),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
