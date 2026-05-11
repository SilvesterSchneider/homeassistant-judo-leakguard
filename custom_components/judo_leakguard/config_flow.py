"""Config Flow für JUDO ZEWA i-SAFE."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.aiohttp_client as hass_aiohttp

from .api import JudoApiClient, JudoAuthError, JudoApiError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    DEVICE_TYPE_ZEWA_ISAFE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


async def _validate_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    """Verbindung testen und Gerätetyp prüfen."""
    session = hass_aiohttp.async_get_clientsession(hass)
    client = JudoApiClient(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        session=session,
    )
    device_type = await client.get_device_type()
    if device_type != DEVICE_TYPE_ZEWA_ISAFE:
        raise ValueError(
            f"Unbekannter Gerätetyp 0x{device_type:02X} – "
            f"erwartet ZEWA i-SAFE (0x44)"
        )
    serial = await client.get_serial_number()
    return {"title": f"JUDO ZEWA i-SAFE ({serial})"}


class JudoLeakguardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow für JUDO ZEWA i-SAFE."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_connection(self.hass, user_input)
            except JudoAuthError:
                errors["base"] = "invalid_auth"
            except JudoApiError:
                errors["base"] = "cannot_connect"
            except ValueError as exc:
                _LOGGER.warning("Gerätetyp-Fehler: %s", exc)
                errors["base"] = "wrong_device_type"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unerwarteter Fehler beim Verbindungstest")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
