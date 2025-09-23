"""Minimal YAML parser used for tests.

This module implements a tiny subset of the :mod:`yaml` package that is
sufficient for the service description tests in this repository.  It only
understands mappings with scalar values and nested dictionaries.  Sequence
support, advanced tags or anchors are intentionally omitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class _StackFrame:
    indent: int
    container: Dict[str, Any]


def _parse_scalar(value: str) -> Any:
    """Return a Python value for the textual YAML representation ``value``."""

    if value.startswith("\"") and value.endswith("\"") and len(value) >= 2:
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered == "null" or value == "~":
        return None
    try:
        if value.startswith("0") and value != "0":
            # Treat values with leading zero as strings to avoid octal surprises
            raise ValueError
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def safe_load(text: str) -> Dict[str, Any]:
    """Parse *text* into a Python dictionary.

    The implementation is intentionally small and geared towards the YAML files
    contained in this repository.  It raises :class:`ValueError` for syntax it
    does not understand instead of trying to emulate the behaviour of the real
    PyYAML parser.
    """

    root: Dict[str, Any] = {}
    stack: List[_StackFrame] = [_StackFrame(indent=-1, container=root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if raw_line[indent:].startswith("- "):
            raise ValueError("Lists are not supported by the lightweight parser")

        if ":" not in raw_line:
            raise ValueError(f"Invalid YAML line: {raw_line!r}")
        key_part, value_part = raw_line[indent:].split(":", 1)
        key = key_part.strip()
        value_part = value_part.strip()

        while stack and indent <= stack[-1].indent:
            stack.pop()
        if not stack:
            raise ValueError(f"Indentation error in YAML near: {raw_line!r}")
        parent = stack[-1].container

        if value_part == "":
            next_container: Dict[str, Any] = {}
            parent[key] = next_container
            stack.append(_StackFrame(indent=indent, container=next_container))
        else:
            parent[key] = _parse_scalar(value_part)

    return root


__all__ = ["safe_load"]
