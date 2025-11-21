from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant import data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.judo_zewa_isafe.const import CONF_BASE_URL, DOMAIN
from zewa_client.client import ZewaAuthenticationError, ZewaConnectionError


@pytest.fixture
async def mock_flow_client(monkeypatch):
    client = AsyncMock()
    client.get_device_type.return_value = "ZEWA_I_SAFE"
    client.get_serial.return_value = 999
    client.close = AsyncMock()
    monkeypatch.setattr(
        "custom_components.judo_zewa_isafe.config_flow.async_create_client",
        AsyncMock(return_value=client),
    )
    return client


async def test_successful_config_flow(hass, mock_flow_client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={CONF_BASE_URL: "example.com", CONF_USERNAME: "u", CONF_PASSWORD: "p"},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BASE_URL] == "http://example.com"
    assert result["title"] == "ZEWA_I_SAFE (999)"
    mock_flow_client.close.assert_awaited()


async def test_invalid_auth(hass, monkeypatch):
    client = AsyncMock()
    client.get_device_type.side_effect = ZewaAuthenticationError()
    client.get_serial.return_value = 1
    client.close = AsyncMock()
    monkeypatch.setattr(
        "custom_components.judo_zewa_isafe.config_flow.async_create_client",
        AsyncMock(return_value=client),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={CONF_BASE_URL: "http://host", CONF_USERNAME: "u", CONF_PASSWORD: "p"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base_url"] == "invalid_auth"


async def test_cannot_connect(hass, monkeypatch):
    client = AsyncMock()
    client.get_device_type.side_effect = ZewaConnectionError()
    client.get_serial.return_value = 1
    client.close = AsyncMock()
    monkeypatch.setattr(
        "custom_components.judo_zewa_isafe.config_flow.async_create_client",
        AsyncMock(return_value=client),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={CONF_BASE_URL: "http://host", CONF_USERNAME: "u", CONF_PASSWORD: "p"},
    )
    assert result["errors"]["base_url"] == "cannot_connect"
