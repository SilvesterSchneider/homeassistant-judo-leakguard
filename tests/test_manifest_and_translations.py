from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT_ROOT = Path("custom_components/judo_leakguard")


def _flatten(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _flatten(value, path)
        else:
            keys.add(path)
    return keys


def test_manifest_fields() -> None:
    manifest = json.loads((COMPONENT_ROOT / "manifest.json").read_text())
    assert manifest["domain"] == "judo_leakguard"
    assert manifest["name"]
    assert manifest["version"]
    assert manifest["config_flow"] is True
    assert isinstance(manifest.get("requirements"), list)


@pytest.mark.parametrize("filename", ["en.json", "de.json"])
def test_translations_are_valid_json(filename: str) -> None:
    data = json.loads((COMPONENT_ROOT / "translations" / filename).read_text())
    assert "entity" in data
    assert "config" in data


def test_translations_have_matching_keys() -> None:
    en = json.loads((COMPONENT_ROOT / "translations" / "en.json").read_text())
    de = json.loads((COMPONENT_ROOT / "translations" / "de.json").read_text())
    assert _flatten(en) == _flatten(de)
