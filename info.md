# Judo Leakguard (HACS)

Dieses Repository stellt die Home Assistant-Integration für den **Judo ZEWA i-SAFE Leakguard** bereit. Die Integration bietet einen Konfigurations-Flow (Host, Benutzername, Passwort) und überprüft beim Verbindungsaufbau automatisch, ob es sich um ein unterstütztes ZEWA i-SAFE-Gerät handelt.

## Installation über HACS
1. Füge dieses Repository in HACS als benutzerdefinierte Integration hinzu.
2. Wähle die neueste verfügbare Version aus (diese richtet sich nach den GitHub Releases/Tags).
3. Nach der Installation Home Assistant neu starten und über **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Judo Leakguard** suchen.
4. Host, Passwort und optional den Benutzernamen (Standard: `standard`) eingeben. Bei einem nicht unterstützten Gerät oder Verbindungsfehlern zeigt der Dialog die passenden Fehlermeldungen an.

## Hinweis zu neuen Releases
- Die in HACS sichtbare Version entspricht dem zuletzt veröffentlichten GitHub-Release. Stelle sicher, dass ein neuer Tag/Release erstellt wird, wenn sich die Versionsnummer in der `manifest.json` ändert (aktuell `0.6.1`).
- Prüfe in der `manifest.json`, ob die Versionsnummer mit dem Release übereinstimmt, damit HACS den Update-Hinweis korrekt anzeigen kann.
