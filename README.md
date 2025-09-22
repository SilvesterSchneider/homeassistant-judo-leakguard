# Judo Leakguard (Zewa i-safe) — Home Assistant Integration

Custom integration to connect **Judo Leakguard / Zewa i-safe** devices to Home Assistant.

## Installation (HACS)

1. HACS → (bis Aufnahme in Default) **Custom repositories** → URL: `https://github.com/SilvesterSchneider/homeassistant-judo-leakguard` → Type: **Integration**
2. Install the integration
3. Restart Home Assistant
4. Add the integration via UI: **My Link** → [Add Judo Leakguard](https://my.home-assistant.io/redirect/config_flow_start/?domain=judo_leakguard)

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
