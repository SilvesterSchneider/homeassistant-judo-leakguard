"""Helper definitions for entity platforms."""

from __future__ import annotations

from typing import Iterable, Protocol

from .entity import Entity


class AddEntitiesCallback(Protocol):
    def __call__(self, entities: Iterable[Entity], update_before_add: bool = False) -> None:
        ...


__all__ = ["AddEntitiesCallback", "Entity"]
