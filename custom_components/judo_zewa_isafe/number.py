"""Number platform for configuration values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import JudoBaseEntity


@dataclass
class JudoNumberDescription(NumberEntityDescription):
    """Describe a configurable number value."""

    set_value_fn: Callable[[object, float, "JudoNumberEntity"], Awaitable[None]]


async def _set_sleep_hours(client, value: float, entity: "JudoNumberEntity") -> None:
    await client.set_sleep_hours(int(value))
    await entity.coordinator.async_request_refresh()


async def _set_absence_limit(client, value: float, entity: "JudoNumberEntity", field: str) -> None:
    limits = entity.coordinator.data.absence_limits
    kwargs = {
        "flow_l_h": limits.max_flow_l_h,
        "volume_l": limits.max_volume_l,
        "duration_min": limits.max_duration_min,
    }
    kwargs[field] = int(value)
    await client.write_absence_limits(**kwargs)
    await entity.coordinator.async_request_refresh()


NUMBERS: tuple[JudoNumberDescription, ...] = (
    JudoNumberDescription(
        key="sleep_hours",
        translation_key="sleep_hours",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=1,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement="h",
        set_value_fn=_set_sleep_hours,
    ),
    JudoNumberDescription(
        key="absence_flow_limit",
        translation_key="absence_flow_limit",
        native_min_value=0,
        native_max_value=10000,
        native_step=10,
        native_unit_of_measurement="L/h",
        set_value_fn=lambda client, value, entity: _set_absence_limit(client, value, entity, "flow_l_h"),
    ),
    JudoNumberDescription(
        key="absence_volume_limit",
        translation_key="absence_volume_limit",
        native_min_value=0,
        native_max_value=10000,
        native_step=10,
        native_unit_of_measurement="L",
        set_value_fn=lambda client, value, entity: _set_absence_limit(client, value, entity, "volume_l"),
    ),
    JudoNumberDescription(
        key="absence_duration_limit",
        translation_key="absence_duration_limit",
        native_min_value=0,
        native_max_value=1000,
        native_step=5,
        native_unit_of_measurement="min",
        set_value_fn=lambda client, value, entity: _set_absence_limit(client, value, entity, "duration_min"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client = data["client"]
    entities = [JudoNumberEntity(coordinator, client, description) for description in NUMBERS]
    async_add_entities(entities)


class JudoNumberEntity(JudoBaseEntity, NumberEntity):
    """Representation of a configurable numeric value."""

    entity_description: JudoNumberDescription

    def __init__(self, coordinator, client, description: JudoNumberDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._client = client
        self._attr_unique_id = f"{coordinator.data.serial}_{description.key}"

    @property
    def native_value(self):
        if self.entity_description.key == "sleep_hours":
            return self.coordinator.data.sleep_hours
        limits = self.coordinator.data.absence_limits
        if self.entity_description.key == "absence_flow_limit":
            return limits.max_flow_l_h
        if self.entity_description.key == "absence_volume_limit":
            return limits.max_volume_l
        return limits.max_duration_min

    async def async_set_native_value(self, value: float) -> None:
        await self.entity_description.set_value_fn(self._client, value, self)
