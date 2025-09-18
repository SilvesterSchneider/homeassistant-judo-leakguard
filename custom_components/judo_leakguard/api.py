from __future__ import annotations
import asyncio
import base64
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

class JudoClient:
    """Minimal async client for JUDO Connectivity REST API (ZEWA i‑SAFE)."""

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
        url = f"{self.base}/api/rest/{func_hex}{'' if payload_hex is None else payload_hex}"
        close_session = False
        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        try:
            auth = aiohttp.BasicAuth(self._username, self._password)
            headers = {"Accept": "application/json"}
            if self._send_data_as_query or payload_hex is None:
                # GET variant: payload embedded in URL (already concatenated above)
                async with session.get(url, auth=auth, ssl=self._verify_ssl, headers=headers) as resp:
                    text = await resp.text()
                    _LOGGER.debug("GET %s -> %s %s", url, resp.status, text)
                    resp.raise_for_status()
                    return _parse_json(text)
            else:
                # POST variant: send form field 'data'
                data = {"data": payload_hex or ""}
                async with session.post(f"{self.base}/api/rest/{func_hex}", data=data, auth=auth, ssl=self._verify_ssl, headers=headers) as resp:
                    text = await resp.text()
                    _LOGGER.debug("POST %s data=%s -> %s %s", func_hex, payload_hex, resp.status, text)
                    resp.raise_for_status()
                    return _parse_json(text)
        finally:
            if close_session:
                await session.close()

    # -------------------------- High-level helpers -------------------------
    async def get_device_type(self) -> int:
        data = await self._request("FF00")
        return int(data["data"], 16)

    async def get_serial(self) -> str:
        data = await self._request("0600")
        return data["data"].lower()

    async def get_fw(self) -> str:
        data = await self._request("0100")
        hexbytes = data["data"]
        # 3 bytes, e.g. 661301 -> 0x66 0x13 0x01; map to dotted-ish version
        major = int(hexbytes[0:2], 16)
        minor = int(hexbytes[2:4], 16)
        patch = int(hexbytes[4:6], 16)
        return f"{major}.{minor}.{patch}"

    async def get_install_ts(self) -> Optional[int]:
        try:
            data = await self._request("0E00")
            return int(data["data"], 16)
        except Exception:
            return None

    async def get_total_liters(self) -> Optional[int]:
        try:
            data = await self._request("2800")
            return _u32_le(data["data"])  # liters
        except Exception:
            return None

    # ZEWA specific reads
    async def read_absence_limits(self) -> tuple[int, int, int]:
        d = await self._request("5E00")
        s = d["data"].lstrip("\"").rstrip("\"") if isinstance(d["data"], str) else d["data"]
        flow = int(s[0:4], 16)
        volume = int(s[4:8], 16)
        minutes = int(s[8:12], 16)
        return flow, volume, minutes

    async def read_sleep_duration(self) -> Optional[int]:
        try:
            d = await self._request("6600")
            return int(d["data"], 16)
        except Exception:
            return None

    async def read_learn_status(self) -> tuple[bool, Optional[int]]:
        d = await self._request("6400")
        s = d["data"]
        active = int(s[0:2], 16) == 1
        remaining = int(s[2:6], 16)
        return active, remaining

    async def read_microleak_mode(self) -> Optional[int]:
        try:
            d = await self._request("6500")
            return int(d["data"], 16)
        except Exception:
            return None

    async def read_datetime(self) -> Optional[str]:
        try:
            d = await self._request("5900")
            s = d["data"]
            dd, mm, yy, hh, mi, ss = [int(s[i:i+2], 16) for i in range(0, 12, 2)]
            return f"20{yy:02d}-{mm:02d}-{dd:02d}T{hh:02d}:{mi:02d}:{ss:02d}"
        except Exception:
            return None

    # Writes / actions
    async def action_no_payload(self, func: str) -> None:
        await self._request(func)

    async def write_leak_settings(self, vac_mode: int, flow_lph: int, volume_l: int, minutes: int) -> None:
        # 7 bytes payload
        payload = (
            f"{vac_mode:02x}"
            f"{flow_lph & 0xFFFF:04x}"
            f"{volume_l & 0xFFFF:04x}"
            f"{minutes & 0xFFFF:04x}"
        ).upper()
        await self._request("50", payload)

    async def write_sleep_duration(self, hours: int) -> None:
        await self._request("53", f"{hours & 0xFF:02x}".upper())

    async def write_vacation_type(self, vac_mode: int) -> None:
        await self._request("56", f"{vac_mode & 0xFF:02x}".upper())

    async def write_datetime(self, dt_tuple: tuple[int,int,int,int,int,int]) -> None:
        dd, mm, yy, hh, mi, ss = dt_tuple
        payload = f"{dd:02x}{mm:02x}{yy:02x}{hh:02x}{mi:02x}{ss:02x}".upper()
        await self._request("5A", payload)


def _parse_json(text: str) -> Dict[str, Any]:
    # Some firmwares wrap as {"data":"..."} or ["data":"..."] or raw; normalize
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return obj[0]
    except Exception:
        pass
    # fallback: extract after data:
    if "data" in text:
        start = text.find("data")
        colon = text.find(":", start)
        quote = text.find("\"", colon)
        endq = text.find("\"", quote + 1)
        if start != -1 and colon != -1 and quote != -1 and endq != -1:
            return {"data": text[quote + 1 : endq]}
    raise ValueError(f"Unexpected API response: {text!r}")


def _u32_le(hexstr: str) -> int:
    # expects 8 hex chars LSB first => reverse byte order
    hexstr = hexstr.strip().strip('"')
    if len(hexstr) < 8:
        hexstr = hexstr.zfill(8)
    b0, b1, b2, b3 = hexstr[0:2], hexstr[2:4], hexstr[4:6], hexstr[6:8]
    le = b3 + b2 + b1 + b0
    return int(le, 16)