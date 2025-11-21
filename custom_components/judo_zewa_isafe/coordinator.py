"""Data update coordinator for the Judo ZEWA i-SAFE integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from aiohttp import BasicAuth, ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from zewa_client import ZewaClient
from zewa_client.client import (
    ZewaAuthenticationError,
    ZewaConnectionError,
    ZewaError,
)
from zewa_client import models

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__package__)


@dataclass
class JudoRuntimeState:
    """Optimistic runtime state for commands without direct read-back."""

    valve_open: bool = False
    sleep_mode: bool = False
    vacation_mode: bool = False


@dataclass
class JudoCoordinatorData:
    """Container for all data exposed to Home Assistant entities."""

    device_type: str
    serial: int
    firmware: str
    commission_date: datetime
    total_water_l: int
    sleep_hours: int
    absence_limits: models.AbsenceLimits
    vacation_type: int
    micro_leak_mode: int
    learn_active: bool
    learning_remaining_l: int
    clock: models.DeviceClock
    runtime: JudoRuntimeState


class JudoDataUpdateCoordinator(DataUpdateCoordinator[JudoCoordinatorData]):
    """Coordinator responsible for polling the ZEWA device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ZewaClient,
        *,
        runtime: Optional[JudoRuntimeState] = None,
    ) -> None:
        self.client = client
        self.runtime = runtime or JudoRuntimeState()
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> JudoCoordinatorData:
        try:
            (
                device_type,
                serial,
                firmware,
                commission_date,
                total_water,
                sleep_hours,
                absence_limits,
                vacation_type,
                micro_leak_mode,
                clock,
                learn_status,
            ) = await asyncio.gather(
                self.client.get_device_type(),
                self.client.get_serial(),
                self.client.get_fw_version(),
                self.client.get_commission_date(),
                self.client.get_total_water_l(),
                self.client.get_sleep_hours(),
                self.client.read_absence_limits(),
                self.client.get_vacation_type(),
                self.client.get_micro_leak_mode(),
                self.client.get_clock(),
                self.client.get_learn_status(),
            )
        except ZewaAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except ZewaConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except ZewaError as err:
            raise UpdateFailed(str(err)) from err

        learn_active, remaining_l = learn_status
        return JudoCoordinatorData(
            device_type=device_type,
            serial=serial,
            firmware=firmware,
            commission_date=commission_date,
            total_water_l=total_water,
            sleep_hours=sleep_hours,
            absence_limits=absence_limits,
            vacation_type=vacation_type,
            micro_leak_mode=micro_leak_mode,
            learn_active=learn_active,
            learning_remaining_l=remaining_l,
            clock=clock,
            runtime=self.runtime,
        )


async def async_create_client(
    base_url: str, username: str, password: str, session: ClientSession | None = None
) -> ZewaClient:
    """Create a configured :class:`ZewaClient` instance."""

    return ZewaClient(base_url, BasicAuth(username, password), session=session)
