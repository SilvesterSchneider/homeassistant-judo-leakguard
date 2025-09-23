from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from copy import deepcopy
import importlib
from typing import Any

import pytest

try:  # pragma: no cover - fallback for limited test env
    from pytest_asyncio import fixture as async_fixture
except ModuleNotFoundError:  # pragma: no cover - fallback for limited test env
    async_fixture = pytest.fixture

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from custom_components.judo_leakguard.const import (
    CONF_SEND_AS_QUERY,
    CONF_VERIFY_SSL,
    DOMAIN,
)

from .helpers import MockJudoApi, SERIAL, fresh_payload

try:
    importlib.import_module("pytest_homeassistant_custom_component.plugin")
except ModuleNotFoundError:
    pytest_plugins = ("pytest_homeassistant_custom_component",)
else:
    pytest_plugins = ("pytest_homeassistant_custom_component.plugin",)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Judo Leakguard",
        data={
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 8443,
            CONF_PROTOCOL: "https",
            CONF_USERNAME: "apiuser",
            CONF_PASSWORD: "apipass",
            CONF_VERIFY_SSL: False,
            CONF_SEND_AS_QUERY: False,
        },
        unique_id=f"judo_{SERIAL}",
    )
    return entry


@pytest.fixture
def mock_judo_api(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[type[MockJudoApi], list[MockJudoApi]], None, None]:
    instances: list[MockJudoApi] = []

    class _PatchedMockApi(MockJudoApi):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            instances.append(self)

        async def fetch_all(self) -> dict[str, Any]:
            if _PatchedMockApi.fetch_exception is not None:
                exc = _PatchedMockApi.fetch_exception
                _PatchedMockApi.fetch_exception = None
                raise exc
            self.fetch_all_calls += 1
            return deepcopy(self.data)

    _PatchedMockApi.fetch_exception = None  # type: ignore[attr-defined]
    _PatchedMockApi.default_payload = fresh_payload()  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "custom_components.judo_leakguard.api.JudoLeakguardApi",
        _PatchedMockApi,
    )
    monkeypatch.setattr(
        "custom_components.judo_leakguard.JudoLeakguardApi",
        _PatchedMockApi,
        raising=False,
    )
    monkeypatch.setattr(
        "custom_components.judo_leakguard.config_flow.JudoLeakguardApi",
        _PatchedMockApi,
        raising=False,
    )

    yield _PatchedMockApi, instances

    instances.clear()
    _PatchedMockApi.fetch_exception = None  # type: ignore[attr-defined]
    _PatchedMockApi.default_payload = fresh_payload()  # type: ignore[attr-defined]


if async_fixture is pytest.fixture:

    @pytest.fixture
    def setup_integration(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_judo_api: tuple[type[MockJudoApi], list[MockJudoApi]],
    ) -> Generator[dict[str, Any], None, None]:
        api_class, instances = mock_judo_api
        api_class.default_payload = fresh_payload()
        mock_config_entry.add_to_hass(hass)
        loop = hass.loop
        assert loop.run_until_complete(
            hass.config_entries.async_setup(mock_config_entry.entry_id)
        )
        loop.run_until_complete(hass.async_block_till_done())

        api_instance = instances[0]
        data = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator = data["coordinator"]

        yield {
            "entry": mock_config_entry,
            "api": api_instance,
            "coordinator": coordinator,
            "data": data,
        }

        assert loop.run_until_complete(
            hass.config_entries.async_unload(mock_config_entry.entry_id)
        )
        loop.run_until_complete(hass.async_block_till_done())

else:

    @async_fixture
    async def setup_integration(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_judo_api: tuple[type[MockJudoApi], list[MockJudoApi]],
    ) -> AsyncGenerator[dict[str, Any], None]:
        api_class, instances = mock_judo_api
        api_class.default_payload = fresh_payload()
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        api_instance = instances[0]
        data = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator = data["coordinator"]

        yield {
            "entry": mock_config_entry,
            "api": api_instance,
            "coordinator": coordinator,
            "data": data,
        }

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()


@pytest.fixture
def bypass_throttle(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:  # pragma: no cover - trivial
        sleep_calls.append(delay)

    monkeypatch.setattr("custom_components.judo_leakguard.api.asyncio.sleep", _fake_sleep)
    return sleep_calls
