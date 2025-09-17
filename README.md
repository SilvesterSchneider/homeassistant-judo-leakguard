# Home Assistant – Judo Leakguard Custom Integration

> **Supports**: Judo i-soft SAFE/PRO (+ Leakageschutz), ZEWA i‑SAFE, i-fill 60 (limited) — via the local REST-like `/api/rest/<cmd>` interface.
>
> **Entities (initial)**: Valve switch (open/close), total water meter (liters), soft water meter, device type sensor, service phone text, update coordinator health. Easily extendable to thresholds, scenes & stats.

# Judo Leakguard / i-soft for Home Assistant

A minimal, extendable custom integration for JUDO devices exposing the `/api/rest/<cmd>` local API.

## Install via HACS (Custom Repository)
1. Ensure you have **HACS** installed in Home Assistant.
2. Go to **HACS → Integrations → ⋮ → Custom repositories**.
3. Add repo URL `https://github.com/silvester-schneider/homeassistant-judo-leakguard` as type **Integration**.
4. Search in HACS for **Judo Leakguard / i-soft** and install.
5. Restart Home Assistant.
6. Add via **Settings → Devices & Services → Add Integration → Judo Leakguard**.

> When you later publish a release on GitHub (see below), HACS will surface updates automatically.

## Manual install (without HACS)
1. Create folder: `config/custom_components/judo_leakguard/`
2. Copy all files from this repo into that folder.
3. Restart Home Assistant.
4. Add via **Settings → Devices & Services → Add Integration → Judo Leakguard**.

## Options
- **Send 'data' as query**: Some firmwares expect `/api/rest/<cmd>?data=...` while others expect a POST with form body `data=...`. This switch lets you pick; the client also attempts a fallback automatically.

## Entities (initial)
- **Switch – Leakguard Valve**: turns the valve *on* (open) or *off* (closed). Uses 3D00/3C00 (i‑soft SAFE/PRO) or 5200/5100 (ZEWA).
- **Sensor – Total water (L)**: `/api/rest/2800` (LSB first).
- **Sensor – Soft water (L)**: `/api/rest/2900` (LSB first).
- **Sensor – Service phone**: `/api/rest/5800` (ASCII, 16 bytes).

## Release to HACS
This repo ships a GitHub Action that automatically builds a zip from `custom_components/judo_leakguard` when you create a GitHub Release.

**Steps:**
1. Commit & push to `main`.
2. Create a tag like `v0.1.0`.
3. Create a GitHub Release for that tag and publish.
4. HACS will detect the new version and offer an update.

## Dev Notes
- Device type is read via `FF00` (single byte hex). Mapping is in `const.py`.
- All hex payloads are **little‑endian** unless noted.
- The client returns verbatim `{"data": "..."}` hex; parsers convert to meaningful ints/strings.
- Many commands accept *no* data (e.g., open/close), others accept 1–n bytes encoded as hex.

## Safety
Controlling a leak guard can stop household water. Use automations carefully.