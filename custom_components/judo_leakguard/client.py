from __future__ import annotations
import asyncio
import logging
from typing import Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

class JudoClient:
    def __init__(
        self,
        host: str,
        *,
        use_https: bool = False,
        verify_ssl: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        send_data_as_query: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._base = f"{'https' if use_https else 'http'}://{host}"
        self._verify_ssl = verify_ssl
        self._auth = aiohttp.BasicAuth(username, password) if username and password else None
        self._send_data_as_query = send_data_as_query
        self._session = session

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def rest(self, cmd_hex: str, data: Optional[str] = None) -> dict:
        """Call `/api/rest/<cmd>`.
        Automatically tries POST form (`data=...`) first, then GET with `?data=...` if needed.
        Returns JSON dict. Raises for HTTP >=400.
        """
        url = f"{self._base}/api/rest/{cmd_hex}"
        headers = {"Accept": "application/json, text/plain, */*"}

        # Primary: POST form data (observed on some firmwares)
        try:
            if data is None or not self._send_data_as_query:
                payload = None if data is None else {"data": data}
                async with self.session.post(
                    url,
                    data=payload,
                    auth=self._auth,
                    ssl=self._verify_ssl,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
        except Exception as e:
            _LOGGER.debug("POST form failed for %s (%s), will try GET fallback", cmd_hex, e)

        # Fallback: GET with query param
        params = {"data": data} if data is not None else None
        async with self.session.get(
            url,
            params=params if self._send_data_as_query or data is not None else None,
            auth=self._auth,
            ssl=self._verify_ssl,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    # Convenience wrappers
    async def get_device_type(self) -> int:
        js = await self.rest("FF00")
        # responses look like {"data": "33"} or hex bytes; normalize to int
        raw = js.get("data", "")
        return int(raw, 16) if raw else -1

    async def get_total_liters(self) -> Optional[int]:
        js = await self.rest("2800")
        raw = js.get("data")
        if not raw:
            return None
        # 4 bytes LSB first -> liters total, many firmwares encode m³ * 1000 as liters
        b = bytes.fromhex(raw)
        return int.from_bytes(b[:4], "little")

    async def get_soft_liters(self) -> Optional[int]:
        js = await self.rest("2900")
        raw = js.get("data")
        if not raw:
            return None
        b = bytes.fromhex(raw)
        return int.from_bytes(b[:4], "little")

    async def valve_open(self, device_type: int) -> None:
        # i-soft SAFE/PRO: 3D00; ZEWA i-SAFE: 5200
        cmd = "3D00" if device_type not in (0x44,) else "5200"
        await self.rest(cmd)

    async def valve_close(self, device_type: int) -> None:
        # i-soft SAFE/PRO: 3C00; ZEWA i-SAFE: 5100
        cmd = "3C00" if device_type not in (0x44,) else "5100"
        await self.rest(cmd)

    async def get_service_phone(self) -> Optional[str]:
        # 16 ASCII bytes
        js = await self.rest("5800")
        raw = js.get("data")
        if not raw:
            return None
        try:
            return bytes.fromhex(raw).decode("ascii", errors="ignore").strip("\x00 ")
        except Exception:
            return None