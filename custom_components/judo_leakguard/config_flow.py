from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from .const import DOMAIN, DEFAULT_HTTPS, DEFAULT_VERIFY_SSL, DEFAULT_SEND_DATA_AS_QUERY
from .api import JudoClient

DATA_SCHEMA = vol.Schema({
    vol.Required("host"): str,
    vol.Required("username", default="admin"): str,
    vol.Required("password", default="Connectivity"): str,
    vol.Optional("https", default=DEFAULT_HTTPS): bool,
    vol.Optional("verify_ssl", default=DEFAULT_VERIFY_SSL): bool,
    vol.Optional("send_data_as_query", default=DEFAULT_SEND_DATA_AS_QUERY): bool,
})

class JudoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = JudoClient(
                user_input["host"],
                user_input["username"],
                user_input["password"],
                use_https=user_input["https"],
                verify_ssl=user_input["verify_ssl"],
                send_data_as_query=user_input["send_data_as_query"],
            )
            try:
                dtype = await client.get_device_type()
                if dtype != 0x44:
                    errors["base"] = "wrong_device_type"
                else:
                    serial = await client.get_serial()
                    await self.async_set_unique_id(f"zewa_{serial}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=f"ZEWA i‑SAFE ({serial[-5:]})", data=user_input)
            except aiohttp.ClientResponseError:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init")
