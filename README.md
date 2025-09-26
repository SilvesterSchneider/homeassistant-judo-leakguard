# Judo Leakguard (Zewa i-safe) — Home Assistant Integration

Custom integration to connect **Judo Leakguard / Zewa i-safe** devices to Home Assistant.

## Installation (HACS)

1. HACS → (bis Aufnahme in Default) **Custom repositories** → URL: `https://github.com/SilvesterSchneider/homeassistant-judo-leakguard` → Type: **Integration**
2. Install the integration
3. Restart Home Assistant
4. Add the integration via UI: **My Link** → [Add Judo Leakguard](https://my.home-assistant.io/redirect/config_flow_start/?domain=judo_leakguard)

## Available Entities

| Platform          | Entity ID suffix           | English name             | German name                      | Description                                       | Unit / Values               |
| ----------------- | -------------------------- | ------------------------ | -------------------------------- | ------------------------------------------------- | --------------------------- |
| **Sensor**        | `pressure`                 | Pressure                 | Druck                            | Current water pressure                            | bar                         |
|                   | `water_flow`               | Water flow               | Wasserdurchfluss                 | Current flow rate                                 | l/min                       |
|                   | `total_water`              | Total water              | Gesamtwasser                     | Total consumption (m³) since installation         | m³                          |
|                   | `total_water_liters`       | Total water (L)          | Gesamtwasser (L)                 | Total consumption in liters                       | L                           |
|                   | `device_temperature`       | Device temperature       | Gerätetemperatur                 | Internal device temperature                       | °C                          |
|                   | `battery`                  | Battery                  | Batterie                         | Backup battery charge                             | %                           |
|                   | `last_update_age`          | Last update age          | Alter der letzten Aktualisierung | Time since last successful update                 | seconds/minutes             |
|                   | `sleep_duration`           | Sleep duration           | Ruhedauer                        | Duration of current sleep mode                    | hours                       |
|                   | `absence_flow_limit`       | Absence flow limit       | Abwesenheits-Durchflussgrenze    | Max flow limit during absence                     | l/min                       |
|                   | `absence_volume_limit`     | Absence volume limit     | Abwesenheits-Volumengrenze       | Max volume limit during absence                   | L                           |
|                   | `absence_duration_limit`   | Absence duration limit   | Abwesenheits-Dauergrenze         | Max duration of water use during absence          | min/h                       |
|                   | `learning_remaining_water` | Remaining learning water | Verbleibende Lernwassermenge     | Remaining water until learning completes          | L                           |
|                   | `installation_date`        | Installation date        | Installationsdatum               | Date of installation                              | date                        |
| **Binary Sensor** | `learn_active`             | Learning active          | Lernmodus aktiv                  | Indicates if device is currently in learning mode | on/off                      |
| **Button**        | `reset_alarms`             | Reset alarms             | Alarme zurücksetzen              | Clears all active alarms                          | –                           |
|                   | `start_microleak_test`     | Start micro-leak test    | Mikrolecktest starten            | Starts a micro-leak test                          | –                           |
|                   | `start_learning`           | Start learning           | Lernmodus starten                | Starts learning process                           | –                           |
| **Number**        | `sleep_hours`              | Sleep hours              | Ruhedauer (Stunden)              | Configure sleep duration                          | hours                       |
|                   | `absence_flow_limit`       | Absence flow limit       | Abwesenheits-Durchflussgrenze    | Configure flow limit during absence               | l/min                       |
|                   | `absence_volume_limit`     | Absence volume limit     | Abwesenheits-Volumengrenze       | Configure volume limit during absence             | L                           |
|                   | `absence_duration_limit`   | Absence duration limit   | Abwesenheits-Dauergrenze         | Configure max duration during absence             | min/h                       |
| **Select**        | `vacation_type`            | Vacation type            | Urlaubstyp                       | Select vacation program (U1, U2, U3)              | off / u1 / u2 / u3          |
|                   | `microleak_mode_set`       | Micro-leak mode          | Mikroleck-Modus                  | Behavior when micro-leak detected                 | off / notify / notify_close |
| **Switch**        | `valve_open`               | Valve open               | Ventil geöffnet                  | Open/close main valve                             | on/off                      |
|                   | `sleep_mode`               | Sleep mode               | Ruhemodus                        | Enable/disable sleep mode                         | on/off                      |
|                   | `vacation_mode`            | Vacation mode            | Urlaubsmodus                     | Enable/disable vacation mode                      | on/off                      |

## Features

- Sensors for water status, alerts, battery/connection (model-dependent)
- Basic diagnostics & logging
- Localized strings (DE/EN)

## Configuration

Use the UI flow: [Start config flow](https://my.home-assistant.io/redirect/config_flow_start/?domain=judo_leakguard)

## Support / Issues

- Documentation: this README
- Issues: https://github.com/SilvesterSchneider/homeassistant-judo-leakguard/issues

## Developer

Install development dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

### Client usage examples

```python
import asyncio
from aiohttp import BasicAuth, ClientSession

from zewa_client import ZewaClient


async def main() -> None:
    async with ClientSession() as session:
        client = ZewaClient("http://device", BasicAuth("user", "pass"), session=session)

        # Control the valve
        await client.open_valve()
        await client.close_valve()

        # Configure sleep mode for six hours and start it immediately
        await client.set_sleep_hours(6)
        await client.sleep_start()

        # Update absence monitoring limits and leak preset
        await client.write_absence_limits(flow_l_h=30, volume_l=2, duration_min=15)
        await client.write_leak_preset(vacation_type=1, max_flow_l_h=150, max_volume_l=500, max_duration_min=90)


if __name__ == "__main__":
    asyncio.run(main())
```
