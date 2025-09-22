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
