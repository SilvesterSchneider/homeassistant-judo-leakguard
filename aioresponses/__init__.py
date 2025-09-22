"""Very small subset of the aioresponses API used for tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import aiohttp


@dataclass
class RequestCall:
    kwargs: Dict[str, Any]


@dataclass
class _ResponseSpec:
    status: int
    body: str
    headers: aiohttp.LooseHeaders


class AioResponses:
    def __init__(self) -> None:
        self._responses: Dict[Tuple[str, str], List[_ResponseSpec]] = {}
        self.requests: Dict[Tuple[str, str], List[RequestCall]] = {}

    def __enter__(self) -> "AioResponses":
        aiohttp.register_mocker(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        aiohttp.register_mocker(None)
        self._responses.clear()
        return False

    def get(
        self,
        url: str,
        *,
        status: int = 200,
        body: str = "",
        headers: Dict[str, str] | None = None,
    ) -> None:
        spec = _ResponseSpec(status=status, body=body, headers=headers or {})
        self._responses.setdefault(("GET", url), []).append(spec)

    # Internal API used by the aiohttp stub ---------------------------------

    def _pop(self, method: str, url: str) -> _ResponseSpec:
        queue = self._responses.get((method, url))
        if not queue:
            raise AssertionError(f"No mocked response for {method} {url}")
        return queue.pop(0)

    def _record(self, method: str, url: str, kwargs: Dict[str, Any]) -> None:
        self.requests.setdefault((method, url), []).append(RequestCall(kwargs))


# The real library exposes the class under this name

aioresponses = AioResponses

__all__ = ["aioresponses", "AioResponses", "RequestCall"]
