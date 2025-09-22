import asyncio
from typing import List

import aiohttp
from aioresponses import aioresponses

from zewa_client.client import ZewaClient


def test_backoff_on_429(http_session: aiohttp.ClientSession, run_async) -> None:
    sleep_calls: List[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = ZewaClient(
        "http://device",
        aiohttp.BasicAuth("user", "pass"),
        session=http_session,
        sleep=fake_sleep,
        max_attempts=4,
    )
    url = "http://device/api/rest/FF00"
    with aioresponses() as mocked:
        mocked.get(url, status=429)
        mocked.get(url, status=429)
        mocked.get(url, status=200, body="44")
        device_type = run_async(client.get_device_type())

    assert device_type == "ZEWA_I_SAFE"
    assert sleep_calls == [2.0, 4.0]
    assert len(mocked.requests[("GET", url)]) == 3


class _ControlledResponse:
    def __init__(self, body: str) -> None:
        self.status = 200
        self.headers: dict[str, str] = {}
        self._body = body

    async def __aenter__(self) -> "_ControlledResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        return None

    async def text(self) -> str:
        return self._body


class _ControlledSession:
    def __init__(self, bodies: list[str], gates: list[asyncio.Event]) -> None:
        self._bodies = bodies
        self._gates = gates
        self.calls: list[str] = []
        self.active = 0
        self.enter_events = [asyncio.Event() for _ in bodies]

    def get(self, url: str, **kwargs):  # type: ignore[override]
        index = len(self.calls)
        self.calls.append(url)
        enter_event = self.enter_events[index]
        gate = self._gates[index]
        body = self._bodies[index]
        session = self

        class _ContextManager:
            async def __aenter__(self_inner) -> _ControlledResponse:
                session.active += 1
                enter_event.set()
                await gate.wait()
                return _ControlledResponse(body)

            async def __aexit__(self_inner, exc_type, exc, tb) -> None:
                session.active -= 1
                return None

        return _ContextManager()

def test_single_flight_requests(run_async) -> None:
    async def scenario() -> None:
        gate_first = asyncio.Event()
        gate_second = asyncio.Event()
        session = _ControlledSession(["00000000", "00000000"], [gate_first, gate_second])
        client = ZewaClient("http://device", aiohttp.BasicAuth("user", "pass"), session=session)

        first_task = asyncio.create_task(client.get_serial())
        await session.enter_events[0].wait()
        assert session.active == 1

        second_task = asyncio.create_task(client.get_serial())
        await asyncio.sleep(0)
        assert not session.enter_events[1].is_set()
        assert session.active == 1

        gate_first.set()
        await session.enter_events[1].wait()
        assert session.active == 1

        gate_second.set()
        serial1, serial2 = await asyncio.gather(first_task, second_task)
        assert serial1 == 0
        assert serial2 == 0

    run_async(scenario())
