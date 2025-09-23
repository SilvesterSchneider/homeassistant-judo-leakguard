from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
import asyncio
from copy import deepcopy
import importlib
import inspect
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
    plugin_module = importlib.import_module("pytest_homeassistant_custom_component.plugin")
except ModuleNotFoundError:
    pytest_plugins = ("pytest_homeassistant_custom_component",)
    plugin_module = None
else:
    pytest_plugins = ("pytest_homeassistant_custom_component.plugin",)

if plugin_module is not None:
    plugin_hass = getattr(plugin_module, "hass", None)
    if plugin_hass is not None and hasattr(plugin_hass, "_get_wrapped_function"):
        hass_func = plugin_hass._get_wrapped_function()
        hass_params = tuple(inspect.signature(hass_func).parameters)

        if inspect.isasyncgenfunction(hass_func):

            if async_fixture is pytest.fixture:

                @pytest.fixture(name="hass")
                def hass_override(request: pytest.FixtureRequest) -> Generator[HomeAssistant, None, None]:
                    kwargs = {name: request.getfixturevalue(name) for name in hass_params}
                    loop = kwargs.get("event_loop") or request.getfixturevalue("event_loop")
                    hass_gen = hass_func(**kwargs)
                    hass_obj = loop.run_until_complete(hass_gen.__anext__())  # type: ignore[arg-type]
                    try:
                        yield hass_obj
                    finally:
                        try:
                            loop.run_until_complete(hass_gen.aclose())  # type: ignore[arg-type]
                        except (RuntimeError, AttributeError, StopAsyncIteration):  # pragma: no cover - defensive
                            pass

            else:

                @async_fixture(name="hass")
                async def hass_override(request: pytest.FixtureRequest) -> AsyncGenerator[HomeAssistant, None]:
                    kwargs = {name: request.getfixturevalue(name) for name in hass_params}
                    hass_gen = hass_func(**kwargs)
                    try:
                        hass_obj = await hass_gen.__anext__()
                        yield hass_obj
                    finally:
                        try:
                            await hass_gen.aclose()
                        except (RuntimeError, AttributeError, StopAsyncIteration):  # pragma: no cover - defensive
                            pass

        elif inspect.iscoroutinefunction(hass_func):

            if async_fixture is pytest.fixture:

                @pytest.fixture(name="hass")
                def hass_override(request: pytest.FixtureRequest) -> HomeAssistant:
                    kwargs = {name: request.getfixturevalue(name) for name in hass_params}
                    loop = kwargs.get("event_loop")
                    if loop is None:  # pragma: no cover - defensive fallback
                        loop = request.getfixturevalue("event_loop")
                    return loop.run_until_complete(hass_func(**kwargs))  # type: ignore[arg-type]

            else:

                @async_fixture(name="hass")
                async def hass_override(request: pytest.FixtureRequest) -> HomeAssistant:
                    kwargs = {name: request.getfixturevalue(name) for name in hass_params}
                    return await hass_func(**kwargs)

        elif inspect.isgeneratorfunction(hass_func):

            @pytest.fixture(name="hass")
            def hass_override(request: pytest.FixtureRequest) -> Generator[HomeAssistant, None, None]:
                kwargs = {name: request.getfixturevalue(name) for name in hass_params}
                hass_gen = hass_func(**kwargs)
                try:
                    hass_obj = next(hass_gen)
                    yield hass_obj
                finally:
                    try:
                        next(hass_gen)
                    except StopIteration:
                        pass

        else:

            @pytest.fixture(name="hass")
            def hass_override(request: pytest.FixtureRequest) -> HomeAssistant:
                kwargs = {name: request.getfixturevalue(name) for name in hass_params}
                return hass_func(**kwargs)


def _sync_noop() -> None:
    return None


async def _async_noop() -> None:  # pragma: no cover - trivial
    return None


def _ensure_hass_sync(
    hass_obj: Any, request: pytest.FixtureRequest
) -> tuple[HomeAssistant, Callable[[], None]]:
    if isinstance(hass_obj, HomeAssistant):
        return hass_obj, _sync_noop

    loop = getattr(hass_obj, "loop", None)
    if loop is None:
        try:
            loop = request.getfixturevalue("event_loop")
        except pytest.FixtureLookupError:
            loop = asyncio.get_event_loop()

    if inspect.isasyncgen(hass_obj):
        hass_gen = hass_obj
        hass_instance = loop.run_until_complete(hass_gen.__anext__())

        def _finalize() -> None:
            try:
                loop.run_until_complete(hass_gen.aclose())
            except (RuntimeError, AttributeError, StopAsyncIteration):
                pass

        return hass_instance, _finalize

    if inspect.isawaitable(hass_obj):
        return loop.run_until_complete(hass_obj), _sync_noop

    if inspect.isgenerator(hass_obj):
        hass_gen = hass_obj
        hass_instance = next(hass_gen)

        def _finalize() -> None:
            try:
                next(hass_gen)
            except StopIteration:
                pass

        return hass_instance, _finalize

    raise TypeError("Unexpected hass fixture type")


async def _ensure_hass_async(
    hass_obj: Any, request: pytest.FixtureRequest
) -> tuple[HomeAssistant, Callable[[], Awaitable[None]]]:
    if isinstance(hass_obj, HomeAssistant):
        return hass_obj, _async_noop

    if inspect.isasyncgen(hass_obj):
        hass_gen = hass_obj
        hass_instance = await hass_gen.__anext__()

        async def _finalize() -> None:
            try:
                await hass_gen.aclose()
            except (RuntimeError, AttributeError, StopAsyncIteration):
                pass

        return hass_instance, _finalize

    if inspect.isawaitable(hass_obj):
        return await hass_obj, _async_noop

    if inspect.isgenerator(hass_obj):
        hass_gen = hass_obj
        hass_instance = next(hass_gen)

        async def _finalize() -> None:
            try:
                next(hass_gen)
            except StopIteration:
                pass

        return hass_instance, _finalize

    return hass_obj, _async_noop


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
        request: pytest.FixtureRequest,
    ) -> Generator[dict[str, Any], None, None]:
        api_class, instances = mock_judo_api
        api_class.default_payload = fresh_payload()
        hass, finalize_hass = _ensure_hass_sync(hass, request)
        mock_config_entry.add_to_hass(hass)
        loop = hass.loop
        assert loop.run_until_complete(
            hass.config_entries.async_setup(mock_config_entry.entry_id)
        )
        loop.run_until_complete(hass.async_block_till_done())

        api_instance = instances[0]
        data = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator = data["coordinator"]

        try:
            yield {
                "entry": mock_config_entry,
                "api": api_instance,
                "coordinator": coordinator,
                "data": data,
            }
        finally:
            assert loop.run_until_complete(
                hass.config_entries.async_unload(mock_config_entry.entry_id)
            )
            loop.run_until_complete(hass.async_block_till_done())
            finalize_hass()

else:

    @async_fixture
    async def setup_integration(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_judo_api: tuple[type[MockJudoApi], list[MockJudoApi]],
        request: pytest.FixtureRequest,
    ) -> AsyncGenerator[dict[str, Any], None]:
        api_class, instances = mock_judo_api
        api_class.default_payload = fresh_payload()
        hass, finalize_hass = await _ensure_hass_async(hass, request)
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        api_instance = instances[0]
        data = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator = data["coordinator"]

        try:
            yield {
                "entry": mock_config_entry,
                "api": api_instance,
                "coordinator": coordinator,
                "data": data,
            }
        finally:
            assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
            await hass.async_block_till_done()
            await finalize_hass()


@pytest.fixture
def bypass_throttle(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:  # pragma: no cover - trivial
        sleep_calls.append(delay)

    monkeypatch.setattr("custom_components.judo_leakguard.api.asyncio.sleep", _fake_sleep)
    return sleep_calls
