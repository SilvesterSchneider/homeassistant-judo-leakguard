"""Home Assistant integration for the Judo ZEWA i-SAFE leak guard."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_BASE_URL, CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS
from .coordinator import JudoDataUpdateCoordinator, JudoRuntimeState, async_create_client


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration via YAML (not supported)."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    hass.data.setdefault(DOMAIN, {})
    session = async_get_clientsession(hass)

    try:
        client = await async_create_client(
            entry.data[CONF_BASE_URL], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], session=session
        )
    except Exception as exc:  # noqa: BLE001
        raise ConfigEntryNotReady("Failed to create client") from exc

    coordinator = JudoDataUpdateCoordinator(hass, client, runtime=JudoRuntimeState())

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        await client.close()
        raise
    except Exception as exc:  # noqa: BLE001
        await client.close()
        raise ConfigEntryNotReady("Unable to communicate with device") from exc

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].close()
    return unload_ok
