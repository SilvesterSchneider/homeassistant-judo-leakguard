from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .client import JudoClient

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Optional("use_https", default=False): bool,
        vol.Optional("verify_ssl", default=True): bool,
        vol.Optional("username"): str,
        vol.Optional("password"): str,
        vol.Optional("send_data_as_query", default=False): bool,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        # Probe device type to validate settings
        client = JudoClient(
            user_input["host"],
            use_https=user_input.get("use_https", False),
            verify_ssl=user_input.get("verify_ssl", True),
            username=user_input.get("username"),
            password=user_input.get("password"),
            send_data_as_query=user_input.get("send_data_as_query", False),
        )
        try:
            dtype = await client.get_device_type()
            if dtype < 0:
                return self.async_abort(reason="cannot_connect")
        except Exception:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(f"judo_{user_input['host']}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=f"Judo @ {user_input['host']}", data=user_input)