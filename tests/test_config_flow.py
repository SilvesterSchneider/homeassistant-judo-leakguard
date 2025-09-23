from __future__ import annotations

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.judo_leakguard import config_flow
from custom_components.judo_leakguard.api import JudoAuthenticationError, JudoConnectionError
from custom_components.judo_leakguard.const import DOMAIN

from .helpers import MockJudoApi


@pytest.mark.usefixtures("mock_judo_api")
async def test_config_flow_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"

    user_input = {
        config_flow.CONF_HOST: "leakguard.local",
        config_flow.CONF_PROTOCOL: "http",
        config_flow.CONF_PORT: 8443,
        config_flow.CONF_USERNAME: "test",
        config_flow.CONF_PASSWORD: "secret",
        config_flow.CONF_VERIFY_SSL: True,
        config_flow.CONF_SEND_AS_QUERY: True,
    }

    create = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    assert create["type"] == "create_entry"
    assert create["title"].startswith("Judo Leakguard")
    assert create["data"] == {
        config_flow.CONF_HOST: "leakguard.local",
        config_flow.CONF_PROTOCOL: "http",
        config_flow.CONF_USERNAME: "test",
        config_flow.CONF_PASSWORD: "secret",
        config_flow.CONF_VERIFY_SSL: True,
        config_flow.CONF_SEND_AS_QUERY: True,
        config_flow.CONF_PORT: 8443,
    }


async def test_config_flow_handles_errors(
    hass: HomeAssistant,
    mock_judo_api: tuple[type[MockJudoApi], list[MockJudoApi]],
) -> None:
    api_class, _instances = mock_judo_api

    api_class.fetch_exception = JudoConnectionError("boom")  # type: ignore[attr-defined]
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    form = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            config_flow.CONF_HOST: "test.local",
            config_flow.CONF_PROTOCOL: "https",
            config_flow.CONF_USERNAME: "user",
            config_flow.CONF_PASSWORD: "pw",
            config_flow.CONF_VERIFY_SSL: True,
            config_flow.CONF_SEND_AS_QUERY: False,
            config_flow.CONF_PORT: 0,
        },
    )
    assert form["type"] == "form"
    assert form["errors"]["base"] == "cannot_connect"

    api_class.fetch_exception = JudoAuthenticationError("auth")  # type: ignore[attr-defined]
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    form = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            config_flow.CONF_HOST: "test.local",
            config_flow.CONF_PROTOCOL: "https",
            config_flow.CONF_USERNAME: "user",
            config_flow.CONF_PASSWORD: "pw",
            config_flow.CONF_VERIFY_SSL: True,
            config_flow.CONF_SEND_AS_QUERY: False,
            config_flow.CONF_PORT: 0,
        },
    )
    assert form["type"] == "form"
    assert form["errors"]["base"] == "invalid_auth"

    # Invalid host should be caught before API call
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    form = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            config_flow.CONF_HOST: "",
            config_flow.CONF_PROTOCOL: "https",
            config_flow.CONF_USERNAME: "user",
            config_flow.CONF_PASSWORD: "pw",
            config_flow.CONF_VERIFY_SSL: True,
            config_flow.CONF_SEND_AS_QUERY: False,
            config_flow.CONF_PORT: 0,
        },
    )
    assert form["type"] == "form"
    assert form["errors"]["base"] == "invalid_host"


async def test_options_flow(mock_config_entry: config_entries.ConfigEntry) -> None:
    flow = config_flow.JudoLeakguardOptionsFlow(mock_config_entry)
    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    complete = await flow.async_step_init({})
    assert complete["type"] == "create_entry"
    assert complete["data"] == {}
