from __future__ import annotations
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

class JudoClient:
    """Async client for JUDO Connectivity REST API (ZEWA i-SAFE only)."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_https: bool = False,
        verify_ssl: bool = True,
        send_data_as_query: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._https = use_https
        self._verify_ssl = verify_ssl
        self._send_data_as_query = send_data_as_query
        self._session = session

    @property
    def base(self) -> str:
        return f"{'https' if self._https else 'http'}://{self._host}"

    async def _request(self, func_hex: str, payload_hex: str | None = None) -> Dict[str, Any]:
        # Some firmware accepts GET with payload appended; otherwise POST with form field data=...
        url = f"{self.base}/api/rest/{func_hex}{'' if payload_hex is None else payload_hex}"
        close = False
        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            close = True
        try:
            auth = aiohttp.BasicAuth(self._username, self._password)
            headers = {"Accept": "application/json"}
            if self._send_data_as_query or payload_hex is None:
                async with session.get(url, auth=auth, ssl=self._verify_ssl, headers=headers) as resp:
                    text = await resp.text()
                    _LOGGER.debug("GET %s -> %s %s", url, resp.status, text)
                    resp.raise_for_status()
                    return _parse_json(text)
            else:
                data = {"data": payload_hex or ""}
                async with session.post(f"{self.base}/api/rest/{func_hex}", data=data, auth=auth, ssl=self._verify_ssl, headers=headers) as resp:
                    text = await resp.text()
                    _LOGGER.debug("POST %s data=%s -> %s %s", func_hex, payload_hex, resp.status, text)
                    resp.raise_for_status()
                    return _parse_json(text)
        finally:
            if close:
                await session.close()

    # ------------ High-level helpers ------------
    async def get_device_type(self) -> int:
        d = await self._request("FF00")
        return int(_extract(d), 16)

    async def get_serial(self) -> str:
        d = await self._request("0600")
        return _extract(d).lower()

    async def get_fw(self) -> str:
        d = await self._request("0100")
        s = _extract(d)
        major = int(s[0:2], 16)
        minor = int(s[2:4], 16)
        patch = int(s[4:6], 16)
        return f"{major}.{minor}.{patch}"

    async def get_total_liters(self) -> Optional[int]:
        try:
            d = await self._request("2800")
            return _u32_le(_extract(d))
        except Exception:
            return None

    async def read_absence_limits(self) -> tuple[int,int,int]:
        s = _extract(await self._request("5E00"))
        return int(s[0:4],16), int(s[4:8],16), int(s[8:12],16)

    async def read_sleep_duration(self) -> Optional[int]:
        try:
            s = _extract(await self._request("6600"))
            return int(s, 16)
        except Exception:
            return None

    async def read_learn_status(self) -> tuple[bool, Optional[int]]:
        s = _extract(await self._request("6400"))
        active = int(s[0:2], 16) == 1
        remaining = int(s[2:6], 16)
        return active, remaining

    async def read_microleak_mode(self) -> Optional[int]:
        try:
            s = _extract(await self._request("6500"))
            return int(s, 16)
        except Exception:
            return None

    async def read_datetime(self) -> Optional[str]:
        try:
            s = _extract(await self._request("5900"))
            dd, mm, yy, hh, mi, ss = [int(s[i:i+2], 16) for i in range(0, 12, 2)]
            return f"20{yy:02d}-{mm:02d}-{dd:02d}T{hh:02d}:{mi:02d}:{ss:02d}"
        except Exception:
            return None

    # Writes / actions
    async def action_no_payload(self, func: str) -> None:
        await self._request(func)

    async def write_leak_settings(self, vac_mode:int, flow_lph:int, volume_l:int, minutes:int) -> None:
        payload = (f"{vac_mode & 0xFF:02x}"
                   f"{flow_lph & 0xFFFF:04x}"
                   f"{volume_l & 0xFFFF:04x}"
                   f"{minutes & 0xFFFF:04x}").upper()
        await self._request("50", payload)

    async def write_sleep_duration(self, hours:int) -> None:
        await self._request("53", f"{hours & 0xFF:02x}".upper())

    async def write_vacation_type(self, vac_mode:int) -> None:
        await self._request("56", f"{vac_mode & 0xFF:02x}".upper())

    async def write_microleak_mode(self, mode:int) -> None:
        await self._request("5B", f"{mode & 0xFF:02x}".upper())

def _parse_json(text:str):
    try:
        obj = json.loads(text)
        if isinstance(obj, dict): return obj
        if isinstance(obj, list) and obj and isinstance(obj[0], dict): return obj[0]
    except Exception:
        pass
    key = '"data"'
    i = text.find(key)
    if i != -1:
        j = text.find('"', i + len(key))
        k = text.find('"', j + 1)
        if j != -1 and k != -1:
            return {"data": text[j+1:k]}
    raise ValueError(f"Unexpected API response: {text!r}")

def _extract(d):
    s = d.get("data", "")
    return s.strip().strip('"') if isinstance(s, str) else str(s)

def _u32_le(hexstr:str) -> int:
    hexstr = hexstr.strip().strip('"').zfill(8)
    b0,b1,b2,b3 = hexstr[0:2],hexstr[2:4],hexstr[4:6],hexstr[6:8]
    return int(b3+b2+b1+b0, 16)
