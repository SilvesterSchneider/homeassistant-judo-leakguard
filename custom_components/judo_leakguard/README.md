# JUDO ZEWA i-SAFE – Home Assistant (local API)

**Nur ZEWA i-SAFE (Gerätetyp 0x44)**. Zugriff über lokales Connectivity-Modul mit Basic-Auth (`admin:Connectivity`, sofern nicht geändert).

## Installation

- Ordner `custom_components/judo_leakguard/` in den HA-Config-Ordner kopieren.
- HA neu starten → Einstellungen → Geräte & Dienste → Integration hinzufügen → **JUDO ZEWA i-SAFE (local)**.

## Konfiguration

- Host/IP, Username/Passwort
- HTTPS optional (bei Self-Signed „Verify SSL“ deaktivieren)
- „Send data as query“ umschalten, falls deine Firmware GET (mit `?data=`) statt POST erwartet.

## Entities (Auszug)

- Switches: Valve (5100/5200), Sleep (5400/5500), Vacation (5700/5800)
- Buttons: Reset alarms (6300), Micro-leak test (5C00), Start learning (5D00)
- Numbers/Selects: Sleep hours (53/66), Absence flow/volume/duration (50/5E), Vacation type (56), Micro-leak mode (5B/65)
- Sensors: Total water (2800), Firmware (0100), Device time (5900), Sleep duration (6600), Learning remaining (6400), Micro-leak mode (6500), Absence limits (5E00)

> Achtung: Ventil-Steuerung kann die Wasserzufuhr schließen. Automationen mit Bedacht.
