"""Minimal pytest-asyncio compatibility shim for offline test environments."""

from __future__ import annotations

import pytest

fixture = pytest.fixture


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ini options expected by ``pytest-asyncio``."""

    parser.addini(
        "asyncio_mode",
        "Default execution mode for asyncio tests.",
        default="auto",
    )
    parser.addini(
        "asyncio_default_fixture_loop_scope",
        "Default scope for the pytest-asyncio event loop fixture.",
        default="function",
    )

