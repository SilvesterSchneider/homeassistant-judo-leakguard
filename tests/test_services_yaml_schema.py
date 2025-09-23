from __future__ import annotations

from pathlib import Path

import yaml

SERVICES_FILE = Path("custom_components/judo_leakguard/services.yaml")


def test_services_yaml_structure() -> None:
    data = yaml.safe_load(SERVICES_FILE.read_text())
    assert set(data) == {"set_datetime", "set_absence_schedule", "clear_absence_schedule"}

    datetime_field = data["set_datetime"]["fields"]["datetime"]
    assert datetime_field["required"] is True
    assert "selector" in datetime_field
    assert "datetime" in datetime_field["selector"]

    absence_fields = data["set_absence_schedule"]["fields"]
    for field in ("slot", "start_day", "start_hour", "start_minute", "end_day", "end_hour", "end_minute"):
        assert field in absence_fields
        selector = absence_fields[field]["selector"]["number"]
        assert selector["min"] >= 0
        assert selector["max"] >= selector["min"]

    clear_fields = data["clear_absence_schedule"]["fields"]
    assert clear_fields["slot"]["selector"]["number"]["max"] == 6
