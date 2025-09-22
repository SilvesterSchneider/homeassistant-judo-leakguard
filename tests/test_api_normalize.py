from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.judo_leakguard.api import (
    JudoAuthenticationError,
    JudoLeakguardApi,
)


def make_api(**kwargs: Any) -> JudoLeakguardApi:
    session = MagicMock()
    return JudoLeakguardApi(session=session, base_url="http://device", **kwargs)


def test_deep_merge_merges_nested():
    left = {"meta": {"serial": "1"}, "value": 1}
    right = {"meta": {"model": "X"}, "value": 2}
    merged = JudoLeakguardApi._deep_merge(left, right)
    assert merged["meta"] == {"serial": "1", "model": "X"}
    assert merged["value"] == 2


@pytest.mark.parametrize(
    "raw,total_expected",
    [
        ({"total_water_m3": 1.5}, 1.5),
        ({"counters": {"total_water_l": 1200}}, 1.2),
    ],
)
def test_normalize_converts_totals(raw, total_expected, monkeypatch):
    api = make_api()
    base: Dict[str, Any] = {
        "pressure": "3.5",
        "sensors": {"flow": "2.0"},
        "temperature": "19.5",
        "battery": "80",
        "meta": {
            "manufacturer": "Brand",
            "model": "ModelX",
            "serial": "XYZ",
            "firmware": "1.0",
            "last_update": 1700000000,
        },
    }
    base.update(raw)
    monkeypatch.setattr(
        "custom_components.judo_leakguard.api.utcnow",
        lambda: datetime.fromtimestamp(1700000010, tz=timezone.utc),
    )
    normalized = api._normalize(base)
    assert normalized["pressure_bar"] == pytest.approx(3.5)
    assert normalized["water_flow_l_min"] == pytest.approx(2.0)
    assert normalized["temperature_c"] == pytest.approx(19.5)
    assert normalized["battery_percent"] == pytest.approx(80)
    assert normalized["total_water_m3"] == pytest.approx(total_expected)
    assert normalized["last_update_seconds"] == 10
    assert normalized["manufacturer"] == "Brand"
    assert normalized["model"] == "ModelX"
    assert normalized["serial"] == "XYZ"
    assert normalized["firmware"] == "1.0"


@pytest.mark.asyncio
async def test_collect_rest_data_gathers(monkeypatch):
    api = make_api()
    monkeypatch.setattr(api, "read_sleep_duration", AsyncMock(return_value=6))
    monkeypatch.setattr(api, "read_absence_limits", AsyncMock(return_value=(10, 20, 30)))
    monkeypatch.setattr(api, "read_microleak_mode", AsyncMock(return_value=2))
    monkeypatch.setattr(api, "read_vacation_type", AsyncMock(return_value=1))
    monkeypatch.setattr(api, "read_learn_status", AsyncMock(return_value={"learn_active": 1}))
    monkeypatch.setattr(api, "read_device_time", AsyncMock(return_value={"device_time": "2023-01-01T00:00:00Z"}))
    monkeypatch.setattr(api, "read_device_type", AsyncMock(return_value="Leakguard"))
    monkeypatch.setattr(api, "read_serial_number", AsyncMock(return_value="123"))
    monkeypatch.setattr(api, "read_firmware_version", AsyncMock(return_value="1.2.3"))
    monkeypatch.setattr(api, "read_installation_timestamp", AsyncMock(return_value={"installation_datetime": "2020-01-01T00:00:00Z"}))
    monkeypatch.setattr(api, "read_total_water", AsyncMock(return_value={"total_water_l": 1200}))

    result = await api._collect_rest_data()
    assert result["sleep_hours"] == 6
    assert result["absence_flow_l_h"] == 10
    assert result["absence_volume_l"] == 20
    assert result["absence_duration_min"] == 30
    assert result["microleak_mode"] == 2
    assert result["vacation_type"] == 1
    assert result["learn_active"] == 1
    assert result["device_time"] == "2023-01-01T00:00:00Z"
    assert result["installation_datetime"] == "2020-01-01T00:00:00Z"
    assert result["total_water_l"] == 1200


@pytest.mark.asyncio
async def test_collect_rest_data_propagates_auth(monkeypatch):
    api = make_api()
    monkeypatch.setattr(api, "read_sleep_duration", AsyncMock(side_effect=JudoAuthenticationError("fail")))
    with pytest.raises(JudoAuthenticationError):
        await api._collect_rest_data()


@pytest.mark.asyncio
async def test_fetch_all_merges_sources(monkeypatch):
    api = make_api()
    payloads = {
        "/api/device": {"serial": "XYZ", "manufacturer": "Brand"},
        "/api/status": {"pressure": "3.2", "sensors": {"flow": "1.5"}},
        "/api/counters": {"total_water_l": 1500},
    }

    async def fake_fetch(endpoint: str) -> Dict[str, Any] | None:
        return payloads.get(endpoint)

    monkeypatch.setattr(api, "_fetch_json", AsyncMock(side_effect=fake_fetch))
    monkeypatch.setattr(api, "_collect_rest_data", AsyncMock(return_value={"sleep_hours": 8}))
    monkeypatch.setattr(
        "custom_components.judo_leakguard.api.utcnow",
        lambda: datetime.fromtimestamp(1700000010, tz=timezone.utc),
    )

    result = await api.fetch_all()
    assert result["serial"] == "XYZ"
    assert result["pressure_bar"] == pytest.approx(3.2)
    assert result["water_flow_l_min"] == pytest.approx(1.5)
    assert result["total_water_m3"] == pytest.approx(1.5)
    assert result["sleep_hours"] == 8
    assert "meta" in result
