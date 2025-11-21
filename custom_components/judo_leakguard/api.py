"""Client helper for die lokale Judo-Leakguard-REST-API."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

from aiohttp import BasicAuth, ClientError, ClientSession

# Die PDF beschreibt nur den Pfad `/api/rest/<kommando>` und nennt keinen TLS-Endpunkt.
# Deshalb verwenden wir HTTP als Standard und akzeptieren optional eine manuell
# angegebene HTTPS-URL.
DEFAULT_SCHEME: Final = "http"
DEFAULT_USERNAME: Final = "standard"
DEVICE_TYPE_COMMAND: Final = "FF00"
EXPECTED_DEVICE_TYPE: Final = "44"
MAX_ATTEMPTS: Final = 3
BACKOFF_SECONDS: Final = 2


@dataclass
class DeviceInfo:
    """Geräteinformationen, die beim Einrichtungs-Check zurückgegeben werden.

    Dieses Modell stellt sicher, dass die Antwort des Endpunkts klar typisiert
    ist und der Config-Flow präzise prüfen kann, ob wirklich ein ZEWA i-SAFE
    angesprochen wird.
    """

    device_type: str


class JudoLeakguardApiError(Exception):
    """Basisfehler für alle Kommunikationsprobleme mit der REST-API.

    Die Ausnahme kapselt Netzwerk- oder Antwortfehler, damit der Config-Flow
    sie eindeutig behandeln und dem Nutzer ein konsistentes Fehlerbild liefern
    kann.
    """


class UnsupportedDeviceError(JudoLeakguardApiError):
    """Spezifischer Fehler, wenn der Typ nicht dem erwarteten ZEWA i-SAFE entspricht.

    Damit verhindern wir, dass andere Judo-Geräte fälschlich eingebunden werden
    und spätere Befehle fehlschlagen würden.
    """


class JudoLeakguardApi:
    """Schlanker REST-Client für die lokale ZEWA-i-SAFE-API.

    Die Klasse bündelt Authentifizierung, URL-Aufbau und Wiederhol-Logik, damit
    alle Aufrufe identisch und fehlertolerant ablaufen.
    """

    def __init__(self, host: str, username: str, password: str) -> None:
        """Bereitet den Client mit Basis-URL und Basic-Auth vor.

        Falls der Nutzer nur einen Host ohne Protokoll angibt, wird automatisch
        HTTP ergänzt. TLS kann genutzt werden, indem die URL mit `https://`
        übergeben wird.
        """
        parsed = urlparse(host)
        if not parsed.scheme:
            host = f"{DEFAULT_SCHEME}://{host}"
        self._base_url = host.rstrip("/")
        self._auth = BasicAuth(username, password)

    async def async_get_device_info(self, session: ClientSession) -> DeviceInfo:
        """Liest den Gerätetyp aus und validiert, ob es ein ZEWA i-SAFE ist.

        Nur wenn die Antwort exakt dem erwarteten Hex-Wert entspricht, lassen wir
        die Einrichtung zu. Dadurch schützt der Flow vor Fehleinbindungen und
        falschen Erwartungen an die API.
        """

        text = await self._async_request(session, DEVICE_TYPE_COMMAND)
        device_type = text.strip().strip("\"").upper()
        if device_type != EXPECTED_DEVICE_TYPE:
            raise UnsupportedDeviceError(
                f"Unexpected device type '{device_type}', expected '{EXPECTED_DEVICE_TYPE}'"
            )
        return DeviceInfo(device_type=device_type)

    async def _async_request(self, session: ClientSession, command: str) -> str:
        """Sendet einen einzelnen API-Aufruf mit Backoff und Fehlerbehandlung.

        Die Methode kapselt das Exponential-Backoff bei 429-Antworten und
        bricht nach einer festen Anzahl Versuche ab, damit der Config-Flow klar
        zwischen Verbindungsproblemen und Gerätetyp-Fehlern unterscheiden kann.
        """
        url = f"{self._base_url}/api/rest/{command}"
        delay = BACKOFF_SECONDS
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with session.get(url, auth=self._auth) as response:
                    if response.status == 429 and attempt < MAX_ATTEMPTS:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    response.raise_for_status()
                    return await response.text()
            except ClientError as err:
                if attempt == MAX_ATTEMPTS:
                    raise JudoLeakguardApiError("Request failed") from err
                await asyncio.sleep(delay)
                delay *= 2
        raise JudoLeakguardApiError("Request failed")
