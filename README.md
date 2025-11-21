# Judo Leakguard for Home Assistant

This repository contains a Home Assistant custom integration for the **Judo ZEWA i-SAFE Leakguard**. It guides you through installation, explains how the setup pop-up works, and documents every file and function that currently ships with the integration.

## Installation

1. Copy the `custom_components/judo_leakguard` folder into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant so the integration is discovered.
3. Navigate to **Settings → Devices & Services → Add Integration**, search for **Judo Leakguard**, and start the flow.
4. In the setup pop-up, the username field is pre-filled with the Judo standard account (`standard`). Enter your device host and password, submit, and the flow will validate that your unit reports the required ZEWA i-SAFE device type before creating the config entry.

## File overview

- `custom_components/judo_leakguard/__init__.py`: Registers the integration domain and wires Home Assistant setup/unload hooks. Each config entry is stored under `hass.data[DOMAIN]` so other platform files can later read connection details.
- `custom_components/judo_leakguard/api.py`: Minimal REST helper for the device. It normalizes the host to HTTPS, attaches HTTP basic auth, applies exponential backoff on HTTP 429 responses, and validates the device type using command `FF00` (expecting response `"44"`).
- `custom_components/judo_leakguard/config_flow.py`: Implements the config flow UI. Presents host/username/password fields with the username defaulting to the Judo standard user, tests connectivity via the API helper, handles common errors, and enforces one entry per host.
- `custom_components/judo_leakguard/manifest.json`: Home Assistant manifest declaring the domain, version, config flow availability, and translation files.
- `custom_components/judo_leakguard/strings.json` and `custom_components/judo_leakguard/translations/en.json`: User-facing strings for the setup form, including error messages for unsupported devices and failed connections.
- `requirements/`: Vendor documentation and mappings that describe the REST endpoints and expected payloads for future feature development.

## Function breakdown

### `custom_components/judo_leakguard/__init__.py`

- `async_setup_entry(hass, entry)`: Stores the created config entry’s data in `hass.data` so platform code can reuse the host and credentials. Returns `True` to signal successful setup.
- `async_unload_entry(hass, entry)`: Removes the stored config entry data when a user deletes or disables the integration, then returns `True` to confirm cleanup.

### `custom_components/judo_leakguard/api.py`

- `DeviceInfo`: Dataclass carrying parsed device information returned by validation requests.
- `JudoLeakguardApi`: REST client wrapper for the Judo endpoint.
  - `__init__(host, username, password)`: Normalizes the host (adds `https://` if missing) and stores Basic Auth credentials for all requests.
  - `async_get_device_info(session)`: Executes the `FF00` command, cleans the response string, and raises `UnsupportedDeviceError` unless the device type is the expected ZEWA i-SAFE identifier (`44`). Returns a `DeviceInfo` instance on success.
  - `_async_request(session, command)`: Internal helper that performs the GET request with exponential backoff (`2s`, `4s`, `8s`) on HTTP 429. Raises `JudoLeakguardApiError` when the request ultimately fails.
- `JudoLeakguardApiError`: Base exception for request failures.
- `UnsupportedDeviceError`: Raised when the device does not report the ZEWA i-SAFE type.

### `custom_components/judo_leakguard/config_flow.py`

- `JudoLeakguardConfigFlow`: Home Assistant config flow implementation.
  - `async_step_user(user_input=None)`: Renders the setup pop-up schema (host, username with default `standard`, password). On submit, it calls `_async_validate_input`; if validation passes, it creates a config entry keyed by host and prevents duplicates. Maps connection or device-type errors to localized form errors.
  - `_async_validate_input(hass, data)`: Builds a `JudoLeakguardApi` client and calls `async_get_device_info` within an `aiohttp` `ClientSession` to verify both connectivity and that the target device is ZEWA i-SAFE.

### Translations and strings

- The strings in `strings.json` and `translations/en.json` provide the labels and error messages shown in the config flow pop-up. They align with the error codes raised in `config_flow.py` (`cannot_connect`, `unsupported_device`, and `unknown`).

This documentation reflects the current scope of the integration. Future features (entities, services, schedules, statistics) can build on the REST commands listed in the `requirements` folder.
