"""Coordinator for Judo Leakguard."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    JudoLeakguardApi,
    JudoLeakguardApiError,
    DeviceInfo,
    FirmwareInfo,
    CommissionInfo,
    TotalWaterUsage,
    AbsenceLimits,
    MicroLeakMode,
    ClockState,
    LearnStatus,
    DayStatistics,
    WeekStatistics,
    MonthStatistics,
    YearStatistics,
)
from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)


@dataclass
class JudoLeakguardData:
    """Data class for the coordinator."""

    device_info: DeviceInfo
    serial_number: str
    firmware_info: FirmwareInfo
    commission_info: CommissionInfo
    total_water: TotalWaterUsage
    absence_limits: AbsenceLimits
    micro_leak_mode: MicroLeakMode
    clock: ClockState
    learn_status: LearnStatus
    sleep_hours: int
    
    # Statistics (fetched less frequently or just 'current' ones)
    day_stats: DayStatistics
    week_stats: WeekStatistics
    month_stats: MonthStatistics
    year_stats: YearStatistics


class JudoLeakguardCoordinator(DataUpdateCoordinator[JudoLeakguardData]):
    """Class to manage fetching Judo Leakguard data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.config_entry = config_entry
        self.api = JudoLeakguardApi(
            config_entry.data[CONF_HOST],
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> JudoLeakguardData:
        """Fetch data from API endpoint."""
        try:
            # Fetch all data
            # Note: Some of these could be cached or fetched less frequently if performance is an issue.
            # For now, we fetch everything on update.
            
            # Device Info & Firmware & Commission could be fetched once, but for simplicity we fetch them.
            # Optimally we would store them in `self` after first fetch.
            
            device_info = await self.api.async_get_device_info(self.session)
            serial_number = await self.api.async_read_serial_number(self.session)
            firmware_info = await self.api.async_read_firmware(self.session)
            commission_info = await self.api.async_read_commission_info(self.session)
            
            total_water = await self.api.async_read_total_water(self.session)
            absence_limits = await self.api.async_read_absence_limits(self.session)
            micro_leak_mode = await self.api.async_read_micro_leak_mode(self.session)
            clock = await self.api.async_read_clock(self.session)
            learn_status = await self.api.async_read_learn_status(self.session)
            sleep_hours = await self.api.async_read_sleep_hours(self.session)

            # Statistics - Fetching for "today" based on device clock or system clock?
            # Using system clock for simplicity of request, but maybe device clock is better?
            # Let's use system date.
            today = date.today()
            day_stats = await self._safe_fetch(
                self.api.async_read_day_statistics(self.session, today),
                DayStatistics([])
            )
            week_stats = await self._safe_fetch(
                self.api.async_read_week_statistics(self.session, today),
                WeekStatistics([])
            )
            month_stats = await self._safe_fetch(
                self.api.async_read_month_statistics(self.session, today),
                MonthStatistics([])
            )
            year_stats = await self._safe_fetch(
                self.api.async_read_year_statistics(self.session, today.year),
                YearStatistics([])
            )

            return JudoLeakguardData(
                device_info=device_info,
                serial_number=serial_number,
                firmware_info=firmware_info,
                commission_info=commission_info,
                total_water=total_water,
                absence_limits=absence_limits,
                micro_leak_mode=micro_leak_mode,
                clock=clock,
                learn_status=learn_status,
                sleep_hours=sleep_hours,
                day_stats=day_stats,
                week_stats=week_stats,
                month_stats=month_stats,
                year_stats=year_stats,
            )

        except JudoLeakguardApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _safe_fetch(self, coro, default):
        """Safely fetch data, returning default on error."""
        try:
            return await coro
        except JudoLeakguardApiError as err:
            _LOGGER.warning("Failed to fetch optional data: %s", err)
            return default


