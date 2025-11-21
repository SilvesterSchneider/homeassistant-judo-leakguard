# Judo ZEWA i-SAFE Leak Guard – Home Assistant Integration

Custom integration that connects the local Judo ZEWA i-SAFE leak guard to Home Assistant. It uses the bundled `zewa_client` to talk to the device's REST API and exposes sensors, binary sensors, switches, selects, numbers, and utility buttons.

## Setup

1. Copy the `custom_components/judo_zewa_isafe` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via Settings → Devices & Services → **Add Integration** → search for "Judo ZEWA i-SAFE".
4. Enter the device URL (include scheme or plain host), username, and password.

## Exposed entities

- **Sensors**: total water usage (litres and cubic meters), sleep duration, absence limits, learning water remaining, device clock, firmware, serial number.
- **Binary sensor**: learning mode active.
- **Switches**: valve open/close, sleep mode, vacation mode (optimistic).
- **Selects**: vacation program, micro-leak handling.
- **Numbers**: sleep hours, absence thresholds.
- **Buttons**: reset alarms, start micro-leak test, start learning.

## Development

Install dependencies and run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

The test suite targets **100%** coverage for all Python modules.
