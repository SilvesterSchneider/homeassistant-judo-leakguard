"""Lightweight subset of the :mod:`voluptuous` API used in tests."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable


class Invalid(Exception):
    """Exception raised when validation fails."""


class Required(str):
    def __new__(cls, key: str, default: Any | None = None):
        obj = str.__new__(cls, key)
        obj.default = default
        obj.required = True
        return obj


class Optional(str):
    def __new__(cls, key: str, default: Any | None = None):
        obj = str.__new__(cls, key)
        obj.default = default
        obj.required = False
        return obj


def All(*validators: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def _validator(value: Any) -> Any:
        for validator in validators:
            value = validator(value)
        return value

    return _validator


def Range(*, min: float | None = None, max: float | None = None) -> Callable[[Any], Any]:
    def _validator(value: Any) -> Any:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise Invalid(f"Expected numeric value, got {value!r}") from exc
        if min is not None and number < min:
            raise Invalid(f"Value {number} is smaller than minimum {min}")
        if max is not None and number > max:
            raise Invalid(f"Value {number} is greater than maximum {max}")
        return value

    return _validator


def In(container: Iterable[Any]) -> Callable[[Any], Any]:
    allowed = set(container)

    def _validator(value: Any) -> Any:
        if value not in allowed:
            raise Invalid(f"Value {value!r} not in {allowed!r}")
        return value

    return _validator


class Schema:
    """Very small schema wrapper.

    The implementation accepts dictionaries that map :class:`Required` or
    :class:`Optional` keys to validators.  Only the functionality exercised by
    the tests is implemented; other behaviour is intentionally omitted.
    """

    def __init__(self, schema: Dict[Any, Any]) -> None:
        self.schema = schema

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, validator in self.schema.items():
            if isinstance(key, (Required, Optional)):
                name = str(key)
                present = name in data
                if not present:
                    if getattr(key, "required", False):
                        raise Invalid(f"Missing required key: {name}")
                    if hasattr(key, "default") and key.default is not None:
                        result[name] = key.default
                    continue
                value = data[name]
            else:
                name = key
                if name not in data:
                    raise Invalid(f"Missing required key: {name}")
                value = data[name]

            if callable(validator):
                value = validator(value)
            result[name] = value
        for name, value in data.items():
            result.setdefault(name, value)
        return result


__all__ = [
    "All",
    "In",
    "Invalid",
    "Optional",
    "Range",
    "Required",
    "Schema",
]
