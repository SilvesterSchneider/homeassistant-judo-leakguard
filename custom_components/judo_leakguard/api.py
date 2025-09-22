from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)


class JudoApiError(Exception):
    """Base exception for Judo API errors."""


class JudoAuthenticationError(JudoApiError):
    """Raised when authentication fails."""


class JudoConnectionError(JudoApiError):
    """Raised when the device cannot be reached."""


class JudoLeakguardApi:
    """Sehr einfacher API-Client für die ZEWA i-SAFE / JUDO Leakguard Box."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        verify_ssl: bool = True,
        request_timeout: float = 5.0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        send_as_query: bool = False,
    ) -> None:
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self._session = session
        self._base_url = base_url
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)
        self._auth = aiohttp.BasicAuth(username or "", password or "") if username or password else None
        self._send_as_query = send_as_query

        # Kandidaten-Endpunkte; wir probieren mehrere und mergen die Ergebnisse
        self._status_candidates = [
            "/api/status",
            "/api/live",
            "/api/values",
            "/status",
            "/live",
            "/values",
            "/zewa/status",
            "/zewa/live",
            "/judo/leakguard/status",
        ]
        self._meta_candidates = [
            "/api/device",
            "/device",
            "/api/info",
            "/info",
        ]
        self._counter_candidates = [
            "/api/counters",
            "/counters",
        ]

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base_url}{path}"

    async def _fetch_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON from the device. Returns None for 404 responses."""
        url = self._url(path)
        try:
            async with self._session.get(
                url,
                timeout=self._timeout,
                ssl=self._verify_ssl,
                auth=self._auth,
            ) as resp:
                if resp.status == 404:
                    return None
                if resp.status in (401, 403):
                    raise JudoAuthenticationError(f"Authentication failed for {url} (status={resp.status})")
                resp.raise_for_status()
                text = await resp.text()
                if not text:
                    return None
                return json.loads(text)
        except JudoAuthenticationError:
            raise
        except asyncio.TimeoutError as exc:
            raise JudoConnectionError(f"Timeout while requesting {url}") from exc
        except aiohttp.ClientConnectorError as exc:
            raise JudoConnectionError(f"Cannot connect to {url}: {exc}") from exc
        except aiohttp.ClientResponseError as exc:
            if exc.status == 404:
                return None
            if exc.status in (401, 403):
                raise JudoAuthenticationError(f"Authentication failed for {url} (status={exc.status})") from exc
            _LOGGER.debug("Unexpected response from %s: %s", url, exc)
            return None
        except aiohttp.ClientError as exc:
            raise JudoConnectionError(f"Client error while requesting {url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            _LOGGER.debug("Invalid JSON from %s: %s", url, exc)
            return None
        except Exception as exc:
            _LOGGER.debug("Fetch failed for %s: %s", url, exc)
            return None

    @staticmethod
    def _deep_merge(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
        """Shallow-merge reicht hier; bei dict/dict könnten wir rekursiv mergen."""
        merged = dict(left)
        for k, v in (right or {}).items():
            # Wenn beide dicts sind, leichtes rekursives Merge
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = JudoLeakguardApi._deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristische Normalisierung, damit die Sensoren etwas finden."""
        if not data:
            return data

        norm = dict(data)

        # Druck (bar)
        pressure = (
            norm.get("pressure_bar")
            or norm.get("pressure")
            or norm.get("sensors", {}).get("pressure_bar")
            or norm.get("live", {}).get("pressure_bar")
        )
        if pressure is not None:
            # Wenn plausibel (< 20 bar), direkt als bar
            try:
                pressure_f = float(pressure)
                if 0 <= pressure_f < 20:
                    norm["pressure_bar"] = pressure_f
            except Exception:
                pass

        # Durchfluss (L/min)
        flow = (
            norm.get("water_flow_l_min")
            or norm.get("flow_l_min")
            or norm.get("flow")
            or norm.get("sensors", {}).get("flow")
            or norm.get("live", {}).get("flow")
        )
        if flow is not None:
            try:
                flow_f = float(flow)
                if flow_f >= 0:
                    norm["water_flow_l_min"] = flow_f
            except Exception:
                pass

        # Temperatur (°C)
        temp = (
            norm.get("temperature_c")
            or norm.get("temp_c")
            or norm.get("temperature")
            or norm.get("sensors", {}).get("temperature_c")
        )
        if temp is not None:
            try:
                norm["temperature_c"] = float(temp)
            except Exception:
                pass

        # Total Water m3 (falls in Litern vorhanden)
        total_m3 = norm.get("total_water_m3") or norm.get("counters", {}).get("total_water_m3")
        if total_m3 is None:
            total_l = norm.get("total_water_l") or norm.get("counters", {}).get("total_water_l")
            try:
                if total_l is not None:
                    norm["total_water_m3"] = float(total_l) / 1000.0
            except Exception:
                pass

        # Akku %
        bat = norm.get("battery_percent") or norm.get("battery") or norm.get("status", {}).get("battery_percent")
        if bat is not None:
            try:
                bat_f = float(bat)
                if 0 <= bat_f <= 100:
                    norm["battery_percent"] = bat_f
            except Exception:
                pass

        # Meta
        manufacturer = norm.get("manufacturer") or norm.get("brand") or norm.get("meta", {}).get("manufacturer")
        if manufacturer:
            norm["manufacturer"] = manufacturer

        model = norm.get("model") or norm.get("device", {}).get("model") or norm.get("meta", {}).get("model")
        if model:
            norm["model"] = model

        serial = norm.get("serial") or norm.get("device", {}).get("serial") or norm.get("meta", {}).get("serial")
        if serial:
            norm["serial"] = serial

        fw = norm.get("firmware") or norm.get("sw_version") or norm.get("meta", {}).get("firmware")
        if fw:
            norm["firmware"] = fw

        # Letztes Update (Sekunden seit)
        # Manche APIs geben timestamps (epoch ms/sec) oder ISO-Strings; wir rechnen age_seconds
        ts = norm.get("last_update") or norm.get("meta", {}).get("last_update") or norm.get("timestamp")
        age = None
        try:
            now = utcnow().timestamp()
            if isinstance(ts, (int, float)) and ts > 1e12:
                age = now - (ts / 1000.0)  # epoch ms
            elif isinstance(ts, (int, float)) and ts > 0:
                age = now - ts  # epoch sec
            elif isinstance(ts, str):
                # Try ISO 8601
                from datetime import datetime
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age = now - dt.timestamp()
        except Exception:
            age = None

        if age is not None and age >= 0:
            norm["last_update_seconds"] = round(age)

        return norm

    async def fetch_all(self) -> Dict[str, Any]:
        """Holt Daten von mehreren Kandidaten-Endpunkten und merged sie."""
        merged: Dict[str, Any] = {}

        # Meta zuerst (falls vorhanden)
        for ep in self._meta_candidates:
            js = await self._fetch_json(ep)
            if js:
                merged = self._deep_merge(merged, {"meta": js})

        # Status / Live
        for ep in self._status_candidates:
            js = await self._fetch_json(ep)
            if js:
                merged = self._deep_merge(merged, js)

        # Counter
        for ep in self._counter_candidates:
            js = await self._fetch_json(ep)
            if js:
                merged = self._deep_merge(merged, {"counters": js})

        if not merged:
            _LOGGER.debug("No payload collected from any endpoint at %s", self._base_url)
            return {}

        normalized = self._normalize(merged)
        _LOGGER.debug("Fetched+normalized payload keys: %s", list(normalized.keys()))
        return normalized
