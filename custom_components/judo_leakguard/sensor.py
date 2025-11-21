"""Sensor platform for Judo Leakguard."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoLeakguardCoordinator
from .entity import JudoLeakguardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: JudoLeakguardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JudoLeakguardSleepDurationSensor(coordinator),
            JudoLeakguardAbsenceFlowLimitSensor(coordinator),
            JudoLeakguardAbsenceVolumeLimitSensor(coordinator),
            JudoLeakguardAbsenceDurationLimitSensor(coordinator),
            JudoLeakguardDeviceDatetimeSensor(coordinator),
            JudoLeakguardDeviceTypeSensor(coordinator),
            JudoLeakguardDeviceSerialSensor(coordinator),
            JudoLeakguardDeviceFirmwareSensor(coordinator),
            JudoLeakguardInstallationDateSensor(coordinator),
            JudoLeakguardTotalWaterSensor(coordinator),
            JudoLeakguardDailyUsageSensor(coordinator),
            JudoLeakguardWeeklyUsageSensor(coordinator),
            JudoLeakguardMonthlyUsageSensor(coordinator),
            JudoLeakguardYearlyUsageSensor(coordinator),
            JudoLeakguardLearningRemainingWaterSensor(coordinator),
        ]
    )


class JudoLeakguardSleepDurationSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for sleep duration."""

    _attr_translation_key = "sleep_duration"
    _attr_unique_id = "sleep_duration"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self.coordinator.data.sleep_hours


class JudoLeakguardAbsenceFlowLimitSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for absence flow limit."""

    _attr_translation_key = "absence_flow_limit"
    _attr_unique_id = "absence_flow_limit"
    # L/h is not a standard unit in UnitOfVolumeFlow (which has m3/h, L/min etc).
    # We can use "L/h" as string.
    _attr_native_unit_of_measurement = "L/h" 

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self.coordinator.data.absence_limits.max_flow_lph


class JudoLeakguardAbsenceVolumeLimitSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for absence volume limit."""

    _attr_translation_key = "absence_volume_limit"
    _attr_unique_id = "absence_volume_limit"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.VOLUME

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self.coordinator.data.absence_limits.max_volume_l


class JudoLeakguardAbsenceDurationLimitSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for absence duration limit."""

    _attr_translation_key = "absence_duration_limit"
    _attr_unique_id = "absence_duration_limit"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self.coordinator.data.absence_limits.max_duration_min


class JudoLeakguardDeviceDatetimeSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for device datetime."""

    _attr_translation_key = "device_datetime"
    _attr_unique_id = "device_datetime"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str:
        """Return the value."""
        return self.coordinator.data.clock.timestamp.isoformat()


class JudoLeakguardDeviceTypeSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for device type."""

    _attr_translation_key = "device_type"
    _attr_unique_id = "device_type"

    @property
    def native_value(self) -> str:
        """Return the value."""
        return self.coordinator.data.device_info.device_type


class JudoLeakguardDeviceSerialSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for device serial."""

    _attr_translation_key = "device_serial"
    _attr_unique_id = "device_serial"

    @property
    def native_value(self) -> str:
        """Return the value."""
        return self.coordinator.data.serial_number


class JudoLeakguardDeviceFirmwareSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for device firmware."""

    _attr_translation_key = "device_firmware"
    _attr_unique_id = "device_firmware"

    @property
    def native_value(self) -> str:
        """Return the value."""
        return self.coordinator.data.firmware_info.version


class JudoLeakguardInstallationDateSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for installation date."""

    _attr_translation_key = "installation_date"
    _attr_unique_id = "installation_date"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str:
        """Return the value."""
        return self.coordinator.data.commission_info.commissioned_at.isoformat()


class JudoLeakguardTotalWaterSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for total water."""

    _attr_translation_key = "total_water_liters"
    _attr_unique_id = "total_water_liters"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self.coordinator.data.total_water.liters


class JudoLeakguardDailyUsageSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for daily usage (sum of today)."""

    _attr_translation_key = "daily_usage"
    _attr_unique_id = "daily_usage"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the value."""
        return sum(self.coordinator.data.day_stats.liters_per_three_hours)


class JudoLeakguardWeeklyUsageSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for weekly usage (sum of current week)."""

    _attr_translation_key = "weekly_usage"
    _attr_unique_id = "weekly_usage"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the value."""
        return sum(self.coordinator.data.week_stats.liters_per_day)


class JudoLeakguardMonthlyUsageSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for monthly usage (sum of current month)."""

    _attr_translation_key = "monthly_usage"
    _attr_unique_id = "monthly_usage"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the value."""
        return sum(self.coordinator.data.month_stats.liters_per_day)


class JudoLeakguardYearlyUsageSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for yearly usage (sum of current year)."""

    _attr_translation_key = "yearly_usage"
    _attr_unique_id = "yearly_usage"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the value."""
        return sum(self.coordinator.data.year_stats.liters_per_month)


class JudoLeakguardLearningRemainingWaterSensor(JudoLeakguardEntity, SensorEntity):
    """Sensor for learning remaining water."""

    _attr_translation_key = "learning_remaining_water"
    _attr_unique_id = "learning_remaining_water"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.VOLUME

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self.coordinator.data.learn_status.remaining_liters
