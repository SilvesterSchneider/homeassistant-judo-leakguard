"""Select platform for Judo Leakguard."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import VacationType, MicroLeakMode
from .const import DOMAIN
from .coordinator import JudoLeakguardCoordinator
from .entity import JudoLeakguardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator: JudoLeakguardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JudoLeakguardVacationTypeSelect(coordinator),
            JudoLeakguardMicroLeakModeSelect(coordinator),
        ]
    )


class JudoLeakguardVacationTypeSelect(JudoLeakguardEntity, SelectEntity):
    """Select to set vacation type."""

    _attr_translation_key = "vacation_type"
    _attr_unique_id = "vacation_type"
    _attr_options = ["off", "u1", "u2", "u3"]

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        # We don't have a read command for vacation type in the coordinator data?
        # The requirements say:
        # - Set vacation type: /api/rest/56<1B 0..3>
        # - Write leak preset (incl. vacation type & maxima): /api/rest/50<7B>
        # But there is NO command to READ the current vacation type explicitly mentioned in mapping.md as a simple GET.
        # Wait, mapping.md says:
        # | `/api/rest/5600` | 0x56 | Urlaubstyp setzen | ... | select.vacation_type |
        # It doesn't list a read command for it.
        # However, `api.py` has `CMD_SET_VACATION_TYPE`.
        # If there is no read command, we can't know the current state unless we store it or if it's part of another command.
        # Checking `api.py` again.
        # `CMD_WRITE_LEAK_PRESET` (50) sets it.
        # Is there a read for leak preset? No.
        # So this might be optimistic or I missed something.
        # Mapping.md: "Switches sind „optimistic“, da nur Start/Stop-Befehle existieren, kein Status-Read."
        # Maybe Selects are also optimistic?
        # But `select` entity usually requires a current option.
        # If I can't read it, I might have to default to something or use `None`.
        return None 

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        val_map = {
            "off": VacationType.OFF,
            "u1": VacationType.U1,
            "u2": VacationType.U2,
            "u3": VacationType.U3,
        }
        await self.coordinator.api.async_set_vacation_type(self.coordinator.session, val_map[option])
        # Optimistic update?
        # self._attr_current_option = option
        # self.async_write_ha_state()


class JudoLeakguardMicroLeakModeSelect(JudoLeakguardEntity, SelectEntity):
    """Select to set micro leak mode."""

    _attr_translation_key = "microleak_mode_set"
    _attr_unique_id = "microleak_mode_set"
    _attr_options = ["off", "notify", "notify_close"]

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        mode = self.coordinator.data.micro_leak_mode
        if mode == MicroLeakMode.OFF:
            return "off"
        if mode == MicroLeakMode.NOTIFY:
            return "notify"
        if mode == MicroLeakMode.NOTIFY_AND_CLOSE:
            return "notify_close"
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        val_map = {
            "off": MicroLeakMode.OFF,
            "notify": MicroLeakMode.NOTIFY,
            "notify_close": MicroLeakMode.NOTIFY_AND_CLOSE,
        }
        await self.coordinator.api.async_set_micro_leak_mode(self.coordinator.session, val_map[option])
        await self.coordinator.async_request_refresh()
