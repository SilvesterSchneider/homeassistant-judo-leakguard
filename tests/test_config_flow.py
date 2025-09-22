from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.judo_leakguard import config_flow
from custom_components.judo_leakguard.const import DOMAIN
from custom_components.judo_leakguard.api import (
    JudoAuthenticationError,
    JudoConnectionError,
)


@pytest.mark.asyncio
async def test_config_flow_success(hass, config_entry_data, monkeypatch):
    mock_api = MagicMock()
    mock_api.fetch_all = AsyncMock(return_value={"serial": "XYZ123"})
    monkeypatch.setattr(
        config_flow,
        "JudoLeakguardApi",
        MagicMock(return_value=mock_api),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=None,
    )
    assert result["type"] == FlowResultType.FORM

    user_input = dict(config_entry_data)
    user_input["port"] = 0
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["host"] == config_entry_data["host"]
    assert "port" not in result2["data"]
    assert result2["title"] == "Judo Leakguard (XYZ123)"


@pytest.mark.asyncio
async def test_config_flow_invalid_auth(hass, config_entry_data, monkeypatch):
    mock_api = MagicMock()
    mock_api.fetch_all = AsyncMock(side_effect=JudoAuthenticationError("boom"))
    monkeypatch.setattr(
        config_flow,
        "JudoLeakguardApi",
        MagicMock(return_value=mock_api),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=None,
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=config_entry_data,
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_config_flow_cannot_connect(hass, config_entry_data, monkeypatch):
    mock_api = MagicMock()
    mock_api.fetch_all = AsyncMock(side_effect=JudoConnectionError("offline"))
    monkeypatch.setattr(
        config_flow,
        "JudoLeakguardApi",
        MagicMock(return_value=mock_api),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=None,
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=config_entry_data,
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
