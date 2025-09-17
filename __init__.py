from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .client import JudoClient
from .coordinator import JudoCoordinator

PLATFORMS = ["switch", "sensor"]
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    client = JudoClient(
        entry.data["host"],
        use_https=entry.data.get("use_https", False),
        verify_ssl=entry.data.get("verify_ssl", True),
        username=entry.data.get("username"),
        password=entry.data.get("password"),
        send_data_as_query=entry.data.get("send_data_as_query", False),
    )
    dtype = await client.get_device_type()
    coord = JudoCoordinator(hass, client, dtype)
    await coord.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coord,
        "device_type": dtype,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data and (client := data.get("client")):
            await client.close()
    return unload_ok