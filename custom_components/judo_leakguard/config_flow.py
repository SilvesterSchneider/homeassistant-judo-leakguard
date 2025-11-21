"""Config-Flow für die Judo-Leakguard-Integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from aiohttp import ClientError, ClientSession
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN
from .api import (
    DEFAULT_USERNAME,
    JudoLeakguardApi,
    JudoLeakguardApiError,
    UnsupportedDeviceError,
)

_LOGGER = logging.getLogger(__name__)


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class JudoLeakguardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Steuert den Einrichtungsdialog im Home Assistant Frontend.

    Der Flow zeigt das Pop-up mit Host, Benutzername und Passwort, hinterlegt
    standardmäßig den Judo-Standardnutzer und prüft anschließend per API-Call,
    ob ein unterstützter ZEWA i-SAFE erreichbar ist.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Zeigt das Eingabeformular und verarbeitet die Nutzereingaben.

        Bei vorhandenen Daten wird sofort ein Validierungsaufruf ausgeführt und
        anhand der Antwort entweder ein Fehler im Formular angezeigt oder ein
        neuer Config-Eintrag angelegt.
        """

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._async_validate_input(self.hass, user_input)
            except UnsupportedDeviceError:
                errors["base"] = "unsupported_device"
            except ClientError:
                errors["base"] = "cannot_connect"
            except JudoLeakguardApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def _async_validate_input(self, hass: HomeAssistant, data: dict) -> None:
        """Validiert die Verbindung gegen das Gerät.

        Baut einen API-Client mit den eingegebenen Zugangsdaten und dem
        angegebenen Host auf und prüft ausschließlich den Gerätetyp-Endpunkt.
        Dadurch stellen wir sicher, dass die Verbindung grundsätzlich funktioniert
        und wirklich ein ZEWA i-SAFE erreichbar ist.
        """

        api = JudoLeakguardApi(data[CONF_HOST], data[CONF_USERNAME], data[CONF_PASSWORD])

        async with ClientSession() as session:
            await api.async_get_device_info(session)
