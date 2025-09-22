from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JudoLeakguardApi, JudoAuthenticationError, JudoConnectionError
from .const import (
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_SEND_AS_QUERY,
    CONF_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_DEFAULT_USERNAME = "admin"
_DEFAULT_PASSWORD = "Connectivity"
_PORT_SENTINEL = 0


def _schema(defaults: Optional[Dict[str, Any]] = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Optional(CONF_PROTOCOL, default=defaults.get(CONF_PROTOCOL, "http")): vol.In(["http", "https"]),
            vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, _PORT_SENTINEL)): vol.All(int, vol.Range(min=0, max=65535)),
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, _DEFAULT_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, _DEFAULT_PASSWORD)): str,
            vol.Optional(CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, True)): bool,
            vol.Optional(CONF_SEND_AS_QUERY, default=defaults.get(CONF_SEND_AS_QUERY, False)): bool,
        }
    )


class JudoLeakguardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Judo Leakguard."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_schema())

        protocol = user_input.get(CONF_PROTOCOL, "http")
        host = user_input.get(CONF_HOST, "").strip()
        port_raw = user_input.get(CONF_PORT, _PORT_SENTINEL)
        port = port_raw if isinstance(port_raw, int) and port_raw > 0 else None
        verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
        username = user_input.get(CONF_USERNAME, "").strip()
        password = user_input.get(CONF_PASSWORD, "")
        send_as_query = user_input.get(CONF_SEND_AS_QUERY, False)
        data: Dict[str, Any] = {}

        form_defaults = {
            CONF_HOST: host,
            CONF_PROTOCOL: protocol,
            CONF_PORT: port_raw if isinstance(port_raw, int) else _PORT_SENTINEL,
            CONF_USERNAME: username if username else user_input.get(CONF_USERNAME, ""),
            CONF_PASSWORD: password,
            CONF_VERIFY_SSL: verify_ssl,
            CONF_SEND_AS_QUERY: send_as_query,
        }

        if not host:
            errors["base"] = "invalid_host"
        elif not username or not password:
            errors["base"] = "invalid_auth"

        base_url = f"{protocol}://{host}"
        if port:
            base_url = f"{protocol}://{host}:{port}"

        if not errors:
            session = async_get_clientsession(self.hass)
            api = JudoLeakguardApi(
                session=session,
                base_url=base_url,
                verify_ssl=verify_ssl,
                username=username,
                password=password,
                send_as_query=send_as_query,
            )

            try:
                data = await api.fetch_all()
            except JudoAuthenticationError:
                errors["base"] = "invalid_auth"
            except JudoConnectionError as exc:
                _LOGGER.debug("Connection test failed: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.debug("Connection test failed: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                if not isinstance(data, dict) or not data:
                    errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(step_id="user", data_schema=_schema(form_defaults), errors=errors)

        serial = data.get("serial") or host
        unique_id = f"judo_{serial}"

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        entry_data: Dict[str, Any] = {
            CONF_HOST: host,
            CONF_PROTOCOL: protocol,
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
            CONF_VERIFY_SSL: verify_ssl,
            CONF_SEND_AS_QUERY: send_as_query,
        }
        if port is not None:
            entry_data[CONF_PORT] = port

        title = f"Judo Leakguard ({serial})"
        return self.async_create_entry(title=title, data=entry_data)

    async def async_step_import(self, import_config: Dict[str, Any]):
        """Support YAML import if needed later."""
        return await self.async_step_user(import_config)


class JudoLeakguardOptionsFlow(config_entries.OptionsFlow):
    """Options flow to adjust settings after setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = dict(self.config_entry.options)
        schema = vol.Schema(
            {
                # Placeholder for future options, e.g. scan interval.
                # vol.Optional("scan_interval_seconds", default=defaults.get("scan_interval_seconds", 30)): vol.All(int, vol.Range(min=5, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
