# ZEWA i-SAFE API → Home Assistant Platform Mapping

Dieses Dokument beschreibt die exakte Zuordnung der ZEWA i-SAFE API-Kommandos zu den Home Assistant Plattformen und Entitäten.  
Es basiert auf der offiziellen API-Spezifikation (PDF) und ist so formuliert, dass keine Mehrdeutigkeit bleibt.

---

## 1. Aktoren (Switch / Button)

| API Command      | Hex  | Beschreibung           | Daten (Request) | Rückgabe | HA Plattform → Entity         | Bemerkungen       |
| ---------------- | ---- | ---------------------- | --------------- | -------- | ----------------------------- | ----------------- |
| `/api/rest/5100` | 0x51 | Ventil schließen       | –               | –        | `switch.valve_open` (OFF)     | OFF = geschlossen |
| `/api/rest/5200` | 0x52 | Ventil öffnen          | –               | –        | `switch.valve_open` (ON)      | ON = geöffnet     |
| `/api/rest/5400` | 0x54 | Sleepmodus starten     | –               | –        | `switch.sleep_mode` (ON)      | Start             |
| `/api/rest/5500` | 0x55 | Sleepmodus beenden     | –               | –        | `switch.sleep_mode` (OFF)     | Stop              |
| `/api/rest/5700` | 0x57 | Urlaubsmodus starten   | –               | –        | `switch.vacation_mode` (ON)   | Start             |
| `/api/rest/5800` | 0x58 | Urlaubsmodus beenden   | –               | –        | `switch.vacation_mode` (OFF)  | Stop              |
| `/api/rest/5C00` | 0x5C | Mikrolecktest starten  | –               | –        | `button.start_microleak_test` | Einmalige Aktion  |
| `/api/rest/5D00` | 0x5D | Lernmodus starten      | –               | –        | `button.start_learning`       | Einmalige Aktion  |
| `/api/rest/6300` | 0x63 | Meldungen zurücksetzen | –               | –        | `button.reset_alarms`         | Einmalige Aktion  |

---

## 2. Konfiguration (Number / Select)

| API Command      | Hex  | Beschreibung              | Datenlayout                              | Rückgabe                                                   | HA Plattform → Entity                                                                           | Details                         |
| ---------------- | ---- | ------------------------- | ---------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------- |
| `/api/rest/5300` | 0x53 | Sleepdauer setzen         | 1 B (1–10 h)                             | –                                                          | `number.sleep_hours`                                                                            | Bsp.: `5300 08` → 8 h           |
| `/api/rest/6600` | 0x66 | Sleepdauer lesen          | –                                        | 1 B (1–10 h)                                               | `sensor.sleep_duration`                                                                         | Bsp.: `"06"` → 6 h              |
| `/api/rest/5E00` | 0x5E | Abwesenheitslimits lesen  | –                                        | 6 B (3×2B LSB-first): Flow (l/h), Volumen (L), Dauer (min) | `sensor.absence_flow_limit`<br>`sensor.absence_volume_limit`<br>`sensor.absence_duration_limit` | Reihenfolge: Flow, Volume, Time |
| `/api/rest/5F00` | 0x5F | Abwesenheitslimits setzen | 6 B (3×2B LSB-first)                     | –                                                          | `number.absence_flow_limit`<br>`number.absence_volume_limit`<br>`number.absence_duration_limit` | Bsp.: `C4 09` → 2500 l/h        |
| `/api/rest/5600` | 0x56 | Urlaubstyp setzen         | 1 B: `00`=off, `01`=U1, `02`=U2, `03`=U3 | –                                                          | `select.vacation_type`                                                                          | States: `off/u1/u2/u3`          |
| `/api/rest/6500` | 0x65 | Mikroleckmodus lesen      | –                                        | 1 B: `00`=off, `01`=notify, `02`=notify+close              | `select.microleak_mode_set`                                                                     | –                               |
| `/api/rest/5B00` | 0x5B | Mikroleckmodus setzen     | 1 B: `00/01/02`                          | –                                                          | `select.microleak_mode_set`                                                                     | –                               |

---

## 3. Zeitplan Abwesenheit (Services)

| API Command      | Hex  | Beschreibung       | Datenlayout          | Rückgabe                                                       | HA Service / Entity                     | Beispiel                                |
| ---------------- | ---- | ------------------ | -------------------- | -------------------------------------------------------------- | --------------------------------------- | --------------------------------------- |
| `/api/rest/6000` | 0x60 | Zeitplan lesen     | Index 0–6            | 6 B: Start-Tag, Start-h, Start-min, Stop-Tag, Stop-h, Stop-min | `sensor.absence_schedule` (optional)    | `02 04 00 03 07 00` → Di 04:00–Mi 07:00 |
| `/api/rest/6100` | 0x61 | Zeitplan schreiben | Index + 6 B wie oben | –                                                              | `judo_leakguard.set_absence_schedule`   | `61 00 03 04 02 00 06 08 00`            |
| `/api/rest/6200` | 0x62 | Zeitplan löschen   | Index 0–6            | –                                                              | `judo_leakguard.clear_absence_schedule` | –                                       |

---

## 4. Geräte-Infos (Sensor / Service)

| API Command      | Hex  | Beschreibung        | Rückgabe               | HA Entity / Service        | Details                       |
| ---------------- | ---- | ------------------- | ---------------------- | -------------------------- | ----------------------------- | --- |
| `/api/rest/5900` | 0x59 | Datum/Zeit lesen    | 6 B: DD MM YY HH mm ss | `sensor.device_datetime`   | –                             |
| `/api/rest/5A00` | 0x5A | Datum/Zeit setzen   | 6 B wie oben           | –                          | `judo_leakguard.set_datetime` | –   |
| `/api/rest/FF00` | 0xFF | Gerätetyp           | 1 B Typ-ID             | `sensor.device_type`       | z. B. `0x44`                  |
| `/api/rest/0600` | 0x06 | Seriennummer        | 4 B                    | `sensor.device_serial`     | LSB-first                     |
| `/api/rest/0100` | 0x01 | Firmware-Version    | 3 B                    | `sensor.device_firmware`   | –                             |
| `/api/rest/0E00` | 0x0E | Inbetriebnahmedatum | 4 B Unix-Timestamp     | `sensor.installation_date` | –                             |

---

## 5. Verbrauch & Statistiken (Sensoren)

| API Command      | Hex  | Beschreibung    | Rückgabe              | HA Entity                   | Details               |
| ---------------- | ---- | --------------- | --------------------- | --------------------------- | --------------------- |
| `/api/rest/2800` | 0x28 | Gesamtwasser    | 4 B Liter (LSB-first) | `sensor.total_water_liters` | m³ = Liter/1000       |
| `/api/rest/FB00` | 0xFB | Tagesstatistik  | 32 B (8×3h-Blöcke)    | `sensor.daily_usage`        | Parameter: DD MM YYYY |
| `/api/rest/FC00` | 0xFC | Wochenstatistik | 28 B (7 Tage)         | `sensor.weekly_usage`       | Parameter: KW YYYY    |
| `/api/rest/FD00` | 0xFD | Monatsstatistik | 124 B (31 Tage)       | `sensor.monthly_usage`      | Parameter: MM YYYY    |
| `/api/rest/FE00` | 0xFE | Jahresstatistik | 48 B (12 Monate)      | `sensor.yearly_usage`       | Parameter: YYYY       |

---

## 6. Lernmodus (Binary Sensor + Sensor)

| API Command      | Hex  | Beschreibung            | Rückgabe                                     | HA Entity                                                         | Details |
| ---------------- | ---- | ----------------------- | -------------------------------------------- | ----------------------------------------------------------------- | ------- |
| `/api/rest/6400` | 0x64 | Lernstatus & Restwasser | 1 B aktiv (0/1) + 2 B Rest-Liter (LSB-first) | `binary_sensor.learn_active`<br>`sensor.learning_remaining_water` | –       |

---

## Hinweise

- Alle **2-Byte-Werte** sind LSB-first kodiert (z. B. `C4 09` → 0x09C4 = 2500).
- **Statistik-Parameter**: Jahr = 2 B Big-Endian (z. B. `07 E7` = 2023).
- **Switches** sind „optimistic“, da nur Start/Stop-Befehle existieren, kein Status-Read.
- **Abwesenheitszeitpläne** können bis zu 7 Einträge haben (Index 0–6).
