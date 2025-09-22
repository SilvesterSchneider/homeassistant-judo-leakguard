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

- **Switches**: Ventil öffnen/schließen (5100/5200), Sleep-Modus (5400/5500), Urlaubsmodus (5700/5800)
- **Buttons**: Meldungen zurücksetzen (6300), Mikroleckageprüfung starten (5C00), Lernmodus starten (5D00)
- **Numbers**: Sleep-Dauer (53/66), Abwesenheits-Grenzwerte für Durchfluss/Volumen/Zeit (5F/5E)
- **Selects**: Urlaubsmodus-Typ (56), Mikro-Leckage-Betrieb (5B/65)
- **Sensoren**: Leitungsdruck, Durchfluss, Geräte-Temperatur, Batteriestand, Gesamtverbrauch (2800), Gerätezeit (5900), Lernmodus-Status & Restwassermenge (6400), Abwesenheitslimits (5E00), Installationsdatum (0E00) uvm.

> Achtung: Ventil-Steuerung kann die Wasserzufuhr schließen. Automationen mit Bedacht.

## Beispiele

### Ventil schließen/öffnen
1. Öffne in Home Assistant **Entwicklerwerkzeuge → Dienste**.
2. Wähle den Dienst `switch.turn_off` (zum Schließen) bzw. `switch.turn_on` (zum Öffnen).
3. Trage als Entität `switch.judo_leakguard_valve` ein.
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
