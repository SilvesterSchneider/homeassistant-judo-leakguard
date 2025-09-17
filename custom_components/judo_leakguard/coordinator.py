from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class JudoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client, device_type: int):
        super().__init__(
            hass,
            _LOGGER,
            name="Judo Leakguard",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.device_type = device_type

    async def _async_update_data(self):
        total = await self.client.get_total_liters()
        soft = await self.client.get_soft_liters()
        phone = await self.client.get_service_phone()
        return {
            "total_liters": total,
            "soft_liters": soft,
            "service_phone": phone,
        }