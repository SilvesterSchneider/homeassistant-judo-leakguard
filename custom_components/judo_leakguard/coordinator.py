"""DataUpdateCoordinator für JUDO ZEWA i-SAFE."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DeviceInfo, DeviceStatus, JudoApiClient, JudoApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class JudoData:
    info: DeviceInfo
    status: DeviceStatus


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
            info, status = await _gather_data(self.client)
        except JudoApiError as exc:
            raise UpdateFailed(f"Fehler beim Datenabruf: {exc}") from exc
        return JudoData(info=info, status=status)


async def _gather_data(client: JudoApiClient) -> tuple[DeviceInfo, DeviceStatus]:
    """Holt Geräteinfos und Betriebsstatus parallel."""
    import asyncio

    return await asyncio.gather(
        client.get_device_info(),
        client.get_status(),
    )
