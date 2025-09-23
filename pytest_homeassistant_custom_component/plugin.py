"""Pytest plugin providing Home Assistant style fixtures."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest

from homeassistant import HomeAssistant
from homeassistant.config_entries import ConfigEntries


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture
def hass(event_loop: asyncio.AbstractEventLoop) -> HomeAssistant:
    hass = HomeAssistant(event_loop)
    ConfigEntries(hass)  # attaches itself to hass
    try:
        yield hass
    finally:
        event_loop.run_until_complete(hass.async_stop())


def pytest_pyfunc_call(pyfuncitem: Any) -> bool:
    test_function = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_function):
        loop: asyncio.AbstractEventLoop = pyfuncitem.funcargs.get("event_loop")
        created_loop = False
        if loop is None:
            loop = asyncio.get_event_loop_policy().new_event_loop()
            asyncio.set_event_loop(loop)
            created_loop = True
        try:
            argnames = getattr(pyfuncitem._fixtureinfo, "argnames", ())
            kwargs = {name: pyfuncitem.funcargs[name] for name in argnames if name in pyfuncitem.funcargs}
            loop.run_until_complete(test_function(**kwargs))
        finally:
            if created_loop:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                asyncio.set_event_loop(None)
        return True
    return False


@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    func = fixturedef.func
    if inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func):
        loop = request.getfixturevalue("event_loop")
        kwargs = {name: request.getfixturevalue(name) for name in fixturedef.argnames}
        if inspect.isasyncgenfunction(func):
            async_gen = func(**kwargs)
            value = loop.run_until_complete(async_gen.__anext__())

            def _finalizer() -> None:
                try:
                    loop.run_until_complete(async_gen.__anext__())
                except StopAsyncIteration:
                    pass

            request.addfinalizer(_finalizer)
            return value
        return loop.run_until_complete(func(**kwargs))
