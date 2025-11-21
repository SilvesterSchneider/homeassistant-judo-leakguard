"""Grundlegende Einrichtung der Judo-Leakguard-Integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "judo_leakguard"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Registriert die Integration nach erfolgreichem Config-Flow.

    Die Methode legt die vom Benutzer eingegebenen Verbindungsdaten im
    Home-Assistant-Datenbereich ab, sodass Plattformen und Dienste darauf
    zugreifen können. Weitere Initialisierung ist aktuell nicht nötig, weil die
    Integration ausschließlich einen Verbindungscheck bereitstellt.
    """

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Bereinigt die gespeicherten Daten beim Entfernen der Integration.

    Die Funktion entfernt den zuvor abgelegten Config-Flow-Eintrag aus dem
    zentralen Datencontainer, sodass bei einer erneuten Einrichtung ein sauberer
    Zustand vorliegt.
    """

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
