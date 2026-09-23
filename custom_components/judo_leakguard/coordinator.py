"""DataUpdateCoordinator für JUDO ZEWA i-SAFE."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    JudoApiClient,
    JudoApiError,
    JudoConsumptionStats,
    JudoDeviceInfo,
    JudoDeviceStatus,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class JudoData:
    info: JudoDeviceInfo
    status: JudoDeviceStatus
    stats: JudoConsumptionStats | None  # None, wenn das Gerät keine Statistik liefert


class JudoDataUpdateCoordinator(DataUpdateCoordinator[JudoData]):
    """Koordiniert den periodischen Datenabruf vom Gerät."""

    def __init__(self, hass: HomeAssistant, client: JudoApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> JudoData:
        try:
            info, status, stats = await _gather_data(self.client)
        except JudoApiError as exc:
            raise UpdateFailed(f"Fehler beim Datenabruf: {exc}") from exc
        return JudoData(info=info, status=status, stats=stats)


async def _gather_data(
    client: JudoApiClient,
) -> tuple[JudoDeviceInfo, JudoDeviceStatus, JudoConsumptionStats | None]:
    """Holt Geräteinfos, Betriebsstatus und Statistiken parallel."""
    import asyncio

    info, status = await asyncio.gather(
        client.get_device_info(),
        client.get_status(),
    )
    return info, status, await _gather_stats(client)


async def _gather_stats(client: JudoApiClient) -> JudoConsumptionStats | None:
    """Liest die Verbrauchsstatistik. Ein Fehler hier legt nicht alles lahm."""
    import asyncio

    # Lokales Datum von HA, nicht die Systemzeit des Containers
    now = dt_util.now()
    yesterday = now - timedelta(days=1)
    week_year, week, _ = now.isocalendar()

    try:
        # Für heute liefert das Gerät nur Nullen, deshalb der Vortag
        daily, weekly, monthly, yearly = await asyncio.gather(
            client.get_daily_usage(yesterday.day, yesterday.month, yesterday.year),
            client.get_weekly_usage(week, week_year),
            client.get_monthly_usage(now.month, now.year),
            client.get_yearly_usage(now.year),
        )
    except (JudoApiError, ValueError, IndexError) as exc:
        _LOGGER.debug("Statistik nicht verfügbar: %s", exc)
        return None
    return JudoConsumptionStats(
        yesterday=daily, weekly=weekly, monthly=monthly, yearly=yearly
    )
