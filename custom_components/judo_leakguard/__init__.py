"""Grundlegende Einrichtung der Judo-Leakguard-Integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import JudoLeakguardCoordinator
from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Registriert die Integration nach erfolgreichem Config-Flow."""

    coordinator = JudoLeakguardCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def async_set_absence_schedule(call) -> None:
        """Service to set absence schedule."""
        index = call.data["index"]
        start_day = call.data["start_day"]
        start_hour = call.data["start_hour"]
        start_minute = call.data["start_minute"]
        stop_day = call.data["stop_day"]
        stop_hour = call.data["stop_hour"]
        stop_minute = call.data["stop_minute"]
        
        from .api import AbsenceWindow
        window = AbsenceWindow(
            index=index,
            start_day=start_day,
            start_hour=start_hour,
            start_minute=start_minute,
            stop_day=stop_day,
            stop_hour=stop_hour,
            stop_minute=stop_minute,
        )
        await coordinator.api.async_write_absence_window(coordinator.session, window)

    async def async_clear_absence_schedule(call) -> None:
        """Service to clear absence schedule."""
        index = call.data["index"]
        await coordinator.api.async_delete_absence_window(coordinator.session, index)

    async def async_set_datetime(call) -> None:
        """Service to set device datetime."""
        # This service might take a datetime object or use current time?
        # Mapping says: `judo_leakguard.set_datetime`
        # It doesn't specify arguments in the mapping table for the service call itself, 
        # but the API command takes 6 bytes.
        # Let's assume it takes a datetime or uses "now" if not provided?
        # Or maybe it takes explicit arguments.
        # Given the complexity, let's assume it takes a datetime string or timestamp.
        # But for simplicity and common use case, maybe it just syncs with HA time?
        # The mapping says: `judo_leakguard.set_datetime` -> `/api/rest/5A00` (Datum/Zeit setzen)
        # Let's allow passing a datetime, default to now.
        import datetime
        dt_val = call.data.get("datetime")
        if dt_val:
            dt = datetime.datetime.fromisoformat(dt_val)
        else:
            dt = datetime.datetime.now()
        
        await coordinator.api.async_set_clock(coordinator.session, dt)

    hass.services.async_register(DOMAIN, "set_absence_schedule", async_set_absence_schedule)
    hass.services.async_register(DOMAIN, "clear_absence_schedule", async_clear_absence_schedule)
    hass.services.async_register(DOMAIN, "set_datetime", async_set_datetime)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Bereinigt die gespeicherten Daten beim Entfernen der Integration."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
