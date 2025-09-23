# JUDO ZEWA i-SAFE – Home Assistant (local API)

**Nur ZEWA i-SAFE (Gerätetyp 0x44)**. Zugriff über lokales Connectivity-Modul mit Basic-Auth (`admin:Connectivity`, sofern nicht geändert).

## Installation

- Ordner `custom_components/judo_leakguard/` in den HA-Config-Ordner kopieren.
- HA neu starten → Einstellungen → Geräte & Dienste → Integration hinzufügen → **JUDO ZEWA i-SAFE (local)**.

## Konfiguration

- Host/IP, Username/Passwort
- HTTPS optional (bei Self-Signed „Verify SSL“ deaktivieren)
- „Send data as query“ umschalten, falls deine Firmware GET (mit `?data=`) statt POST erwartet.

## Entitäten

### Switches

| Entity-ID | Beschreibung | API |
| --- | --- | --- |
| `switch.<gerät>_valve_open` | Ventil öffnen/schließen | `5200` (auf) / `5100` (zu) |
| `switch.<gerät>_sleep_mode` | Sleep-Modus aktivieren/deaktivieren | `5400` / `5500` |
| `switch.<gerät>_vacation_mode` | Urlaubsmodus aktivieren/deaktivieren | `5700` / `5800` |

### Buttons

| Entity-ID | Beschreibung | API |
| --- | --- | --- |
| `button.<gerät>_reset_alarms` | Meldungen/Alarme zurücksetzen | `6300` |
| `button.<gerät>_start_microleak_test` | Mikrolecktest starten | `5C00` |
| `button.<gerät>_start_learning` | Lernmodus starten | `5D00` |

### Numbers (Schreiben)

| Entity-ID | Beschreibung | API (Schreiben) |
| --- | --- | --- |
| `number.<gerät>_sleep_hours` | Sleepdauer 1–10 h (liest `6600`) | `5300` |
| `number.<gerät>_absence_flow_limit` | Grenzwert Durchfluss (l/h) | `5F00` |
| `number.<gerät>_absence_volume_limit` | Grenzwert Volumen (l) | `5F00` |
| `number.<gerät>_absence_duration_limit` | Grenzwert Dauer (min) | `5F00` |

### Selects

| Entity-ID | Beschreibung | API |
| --- | --- | --- |
| `select.<gerät>_vacation_type` | Urlaubstyp `off/u1/u2/u3` | Lesen/Schreiben `5600` |
| `select.<gerät>_microleak_mode_set` | Mikro-Leck-Betrieb `off/notify/notify_close` | Lesen `6500`, Schreiben `5B00` |

### Binary Sensor

| Entity-ID | Beschreibung | API |
| --- | --- | --- |
| `binary_sensor.<gerät>_learn_active` | Lernmodus aktiv | `6400` |

### Sensoren (REST API)

| Entity-ID | Beschreibung | API |
| --- | --- | --- |
| `sensor.<gerät>_sleep_duration` | Aktuelle Sleepdauer (h) | `6600` |
| `sensor.<gerät>_absence_flow_limit` | Grenzwert Durchfluss (l/h) | `5E00` |
| `sensor.<gerät>_absence_volume_limit` | Grenzwert Volumen (l) | `5E00` |
| `sensor.<gerät>_absence_duration_limit` | Grenzwert Dauer (min) | `5E00` |
| `sensor.<gerät>_total_water_liters` / `_total_water` | Gesamtverbrauch (l / m³) | `2800` |
| `sensor.<gerät>_daily_usage` | Tagesverbrauch gesamt (l) | `FB00` |
| `sensor.<gerät>_weekly_usage` | Wochenverbrauch gesamt (l) | `FC00` |
| `sensor.<gerät>_monthly_usage` | Monatsverbrauch gesamt (l) | `FD00` |
| `sensor.<gerät>_yearly_usage` | Jahresverbrauch gesamt (l) | `FE00` |
| `sensor.<gerät>_learning_remaining_water` | Restwassermenge im Lernmodus | `6400` |
| `sensor.<gerät>_device_time` | Gerätesystemzeit | `5900` |
| `sensor.<gerät>_device_type` | Gerätemodell-Code | `FF00` |
| `sensor.<gerät>_device_serial` | Seriennummer | `0600` |
| `sensor.<gerät>_device_firmware` | Firmware-Version | `0100` |
| `sensor.<gerät>_installation_date` | Inbetriebnahmedatum | `0E00` |

Zusätzlich stellt die Integration Live-Werte wie Druck, Durchfluss, Temperatur, Batterie und letzter Kontakt über die JSON-Statusendpunkte bereit.

> Achtung: Ventil-Steuerung kann die Wasserzufuhr schließen. Automationen mit Bedacht.

## Services

| Service | Beschreibung | API |
| --- | --- | --- |
| `judo_leakguard.set_datetime` | Gerätedatum/-zeit setzen | `5A00` |
| `judo_leakguard.set_absence_schedule` | Abwesenheits-Zeitfenster schreiben (Slot 0–6) | `6100` |
| `judo_leakguard.clear_absence_schedule` | Abwesenheits-Zeitfenster löschen | `6200` |

Alle Dienste akzeptieren optional `config_entry_id` oder `device_id`, falls mehrere Geräte eingebunden sind. Beim Setzen eines Zeitfensters müssen Start-/Endtag (0 = Montag … 6 = Sonntag) sowie Stunde und Minute angegeben werden.

## Beispiele

### Ventil schließen/öffnen
1. Öffne in Home Assistant **Entwicklerwerkzeuge → Dienste**.
2. Wähle den Dienst `switch.turn_off` (zum Schließen) bzw. `switch.turn_on` (zum Öffnen).
3. Trage als Entität `switch.<gerät>_valve_open` ein.
4. Ausführen – das Gerät ruft intern `GET /api/rest/5100` (zu) bzw. `GET /api/rest/5200` (auf).

### Sleep-Modus konfigurieren
1. Setze die gewünschte Schlafdauer (1–10 h) über den Dienst `number.set_value` für `number.judo_leakguard_sleep_hours`.
2. Aktiviere den Modus mit `switch.turn_on` auf `switch.judo_leakguard_sleep_mode` (ruft `5300` + `5400`).
3. Zum Beenden `switch.turn_off` auf derselben Entität ausführen (`5500`).

### Abwesenheitsgrenzen schreiben
1. Öffne **Einstellungen → Geräte & Dienste → JUDO ZEWA i-SAFE** und wähle das Gerät.
2. Passe die drei Number-Entitäten an:
   - `number.judo_leakguard_absence_flow` (l/h)
   - `number.judo_leakguard_absence_volume` (l)
   - `number.judo_leakguard_absence_duration` (min)
3. Jeder Wert löst `GET /api/rest/5F00<data>` mit Big-Endian U16-Werten aus.
