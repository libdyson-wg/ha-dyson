"""Dyson 360 Heurist vacuum robot."""

from typing import Optional

from .const import DEVICE_TYPE_360_HEURIST, CleaningMode, VacuumHeuristPowerMode
from .dyson_vacuum_device import DysonVacuumDevice


class Dyson360Heurist(DysonVacuumDevice):
    """Dyson 360 Heurist device."""

    @property
    def device_type(self) -> str:
        """Return the device type."""
        return DEVICE_TYPE_360_HEURIST

    @property
    def current_power_mode(self) -> VacuumHeuristPowerMode:
        """Return current power mode."""
        return VacuumHeuristPowerMode(self._status["currentVacuumPowerMode"])

    @property
    def default_power_mode(self) -> VacuumHeuristPowerMode:
        """Return default power mode."""
        return VacuumHeuristPowerMode(self._status["defaultVacuumPowerMode"])

    @property
    def current_cleaning_mode(self) -> CleaningMode:
        """Return current cleaning mode."""
        return CleaningMode(self._status["currentCleaningMode"])

    @property
    def default_cleaning_mode(self) -> CleaningMode:
        """Return default cleaning mode."""
        return CleaningMode(self._status["defaultCleaningMode"])

    @property
    def is_bin_full(self) -> bool:
        """Return if the bin is full."""
        airways = self._status.get("faults", {}).get("AIRWAYS")
        if airways is None:
            return False
        return (
            airways.get("active") is True and airways.get("description") == "1.0.-1"
        )  # Not sure what this means

    def _send_command(self, command: str, data: Optional[dict] = None):
        if data is None:
            data = {}
        data["mode-reason"] = "LAPP"
        super()._send_command(command, data)

    def start_all_zones(self) -> None:
        """Start cleaning of all zones."""
        self._send_command(
            "START", {"cleaningMode": "global", "fullCleanType": "immediate"}
        )

    def set_default_power_mode(self, power_mode: VacuumHeuristPowerMode) -> None:
        """Set default power mode."""
        self._send_command(
            "STATE-SET",
            {"defaults": {"defaultVacuumPowerMode": power_mode.value}},
        )
