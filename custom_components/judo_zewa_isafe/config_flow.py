"""Config flow for Judo ZEWA i-SAFE."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from zewa_client.client import ZewaAuthenticationError, ZewaConnectionError

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import async_create_client


def _normalise_base_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return f"http://{url}"
    return url


async def _async_validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    base_url = _normalise_base_url(data[CONF_BASE_URL])
    session = async_get_clientsession(hass)
    client = await async_create_client(base_url, data[CONF_USERNAME], data[CONF_PASSWORD], session=session)

    try:
        device_type, serial = await asyncio.gather(client.get_device_type(), client.get_serial())
    except ZewaAuthenticationError as exc:
        raise InvalidAuth from exc
    except (ZewaConnectionError, ClientError) as exc:
        raise CannotConnect from exc
    finally:
        await client.close()

    return {
        "title": f"{device_type} ({serial})",
        "serial": serial,
        "base_url": base_url,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Judo ZEWA i-SAFE."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _async_validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base_url"] = "cannot_connect"
            except InvalidAuth:
                errors["base_url"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base_url"] = "unknown"
            else:
                await self.async_set_unique_id(str(info["serial"]))
                self._abort_if_unique_id_configured()
                data = {
                    CONF_BASE_URL: info["base_url"],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
                return self.async_create_entry(title=info["title"], data=data)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(data_schema, user_input),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
