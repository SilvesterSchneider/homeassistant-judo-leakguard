# JUDO ZEWA i-SAFE – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Eine Home Assistant Custom Component für den **JUDO ZEWA i-SAFE** Leckageschutz mit JUDO Connectivity-Modul.

> [!WARNING]
> **Nutzung auf eigene Gefahr.** Dies ist ein privates Hobbyprojekt, weder von
> JUDO entwickelt noch unterstützt oder geprüft. Die Integration kann das
> Absperrventil schließen und öffnen sowie Leckageschutz-Einstellungen ändern.
> Fehlerhafte Befehle oder Einstellungen können dazu führen, dass der
> Leckageschutz nicht wie erwartet greift oder die Wasserversorgung
> unterbrochen wird. Es wird keinerlei Gewähr oder Haftung für Schäden
> übernommen, insbesondere nicht für Wasserschäden, Folgeschäden oder
> Datenverlust. Prüfe nach jeder Änderung am Gerät selbst, ob es sich wie
> erwartet verhält.

## Voraussetzungen

- JUDO ZEWA i-SAFE (Gerätetyp `0x44`) mit eingebautem JUDO Connectivity-Modul
- Gerät ist per LAN oder WLAN im Heimnetzwerk erreichbar
- Home Assistant mit installiertem [HACS](https://hacs.xyz)

## Installation via HACS

1. HACS öffnen → **Integrationen** → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. URL `https://github.com/SilvesterSchneider/homeassistant-judo-leakguard` eintragen, Kategorie **Integration** wählen → **Hinzufügen**
3. Integration in der HACS-Liste suchen und **Herunterladen**
4. Home Assistant neu starten
5. **Einstellungen → Geräte & Dienste → Integration hinzufügen** → „JUDO ZEWA i-SAFE" suchen

## Konfiguration

| Feld | Beschreibung | Standard |
|---|---|---|
| IP-Adresse / Hostname | IP oder `connectivity-XXXXX` des Geräts | – |
| Benutzername | Web-Interface-Benutzername | `admin` |
| Passwort | Web-Interface-Passwort (siehe Geräteanleitung; bitte ändern) | – |

## Entitäten

### Sensoren
| Entität | Beschreibung |
|---|---|
| `sensor.total_water_liters` | Gesamtwasserverbrauch in Litern |
| `sensor.device_serial` | Seriennummer |
| `sensor.device_firmware` | Firmware-Version |
| `sensor.installation_date` | Inbetriebnahmedatum |
| `sensor.device_datetime` | Geräteuhrzeit (Diagnose, standardmäßig deaktiviert) |
| `sensor.clock_offset` | Abweichung der Geräteuhr gegenüber HA in Sekunden |
| `sensor.sleep_duration` | Eingestellte Schlafdauer |
| `sensor.learning_remaining_water` | Lernmodus Restwasser |
| `sensor.absence_flow_limit` | Abwesenheit – Durchfluss-Limit |
| `sensor.absence_volume_limit` | Abwesenheit – Volumen-Limit |
| `sensor.absence_duration_limit` | Abwesenheit – Dauer-Limit |
| `sensor.yesterday_usage` | Verbrauch gestern (das Gerät liefert Tageswerte erst nach Tagesende; für „heute“ einen Verbrauchszähler-Helfer auf `sensor.total_water_liters` anlegen) |
| `sensor.weekly_usage` | Verbrauch diese Woche |
| `sensor.monthly_usage` | Verbrauch dieser Monat |
| `sensor.yearly_usage` | Verbrauch dieses Jahr |

### Binärsensoren
| Entität | Beschreibung |
|---|---|
| `binary_sensor.learn_active` | Lernmodus aktiv |

### Schalter (optimistisch)
| Entität | Beschreibung |
|---|---|
| `switch.valve_open` | Absperrventil (ON = offen) |
| `switch.sleep_mode` | Sleep-Modus |
| `switch.vacation_mode` | Urlaubsmodus |

### Buttons
| Entität | Beschreibung |
|---|---|
| `button.reset_alarms` | Meldungen zurücksetzen |
| `button.start_microleak_test` | Mikroleck-Test starten |
| `button.start_learning` | Lernmodus starten |

### Zahlen (konfigurierbar)
| Entität | Beschreibung |
|---|---|
| `number.absence_flow_limit` | Abwesenheit – Durchfluss-Limit (L/h) |
| `number.absence_volume_limit` | Abwesenheit – Volumen-Limit (L) |
| `number.absence_duration_limit` | Abwesenheit – Dauer-Limit (min) |

### Auswahl
| Entität | Beschreibung |
|---|---|
| `select.vacation_type` | Urlaubstyp (off / u1 / u2 / u3), optimistisch – das Gerät meldet ihn nicht zurück |
| `select.microleak_mode` | Mikroleck-Modus (off / notify / notify_and_close) |

## Services

### `judo_leakguard.set_absence_schedule`
Schreibt einen Abwesenheitszeitraum (Index 0–6).

```yaml
service: judo_leakguard.set_absence_schedule
data:
  index: 0
  start_day: 1   # 0=So, 1=Mo, …, 6=Sa
  start_hour: 8
  start_minute: 0
  stop_day: 5    # Freitag
  stop_hour: 18
  stop_minute: 0
```

### `judo_leakguard.clear_absence_schedule`
Löscht einen Abwesenheitszeitraum.

```yaml
service: judo_leakguard.clear_absence_schedule
data:
  index: 0
```

### `judo_leakguard.set_datetime`
Schreibt Datum und Uhrzeit auf das Gerät.

```yaml
service: judo_leakguard.set_datetime
data:
  datetime: "2024-06-15 14:30:00"
```

## Technische Details

- Kommunikation: HTTP REST API mit Basic Authentication
- Rate-Limiting: Automatisches Retry mit Exponential Backoff bei HTTP 429
- Poll-Intervall: 30 Sekunden
- Ventil/Sleep/Urlaubsmodus: Optimistische Zustandsverwaltung (kein Status-Readback möglich)

## Sicherheit

- Ändere das Standardpasswort des Connectivity-Moduls. Das Werkspasswort steht
  in der öffentlichen JUDO-Anleitung und ist damit kein Schutz.
- Die REST API spricht nur unverschlüsseltes HTTP. Das Gerät gehört in ein
  abgeschottetes Netz, nicht ins Internet.
- Zugangsdaten gehören nur in die Home-Assistant-Konfiguration, nie in dieses
  Repository.

## Lizenz

MIT – ohne Gewährleistung, siehe Hinweis „Nutzung auf eigene Gefahr" oben.
