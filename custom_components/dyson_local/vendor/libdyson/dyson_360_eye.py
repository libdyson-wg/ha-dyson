"""Dyson 360 Eye vacuum robot."""

from .const import DEVICE_TYPE_360_EYE, VacuumEyePowerMode
from .dyson_vacuum_device import DysonVacuumDevice


class Dyson360Eye(DysonVacuumDevice):
    """Dyson 360 Eye device."""

    @property
    def device_type(self) -> str:
        """Return the device type."""
        return DEVICE_TYPE_360_EYE

    @property
    def power_mode(self) -> VacuumEyePowerMode:
        """Power mode of the device."""
        return VacuumEyePowerMode(self._status["currentVacuumPowerMode"])

    def start(self) -> None:
        """Start cleaning."""
        self._send_command("START", {"fullCleanType": "immediate"})

    def set_power_mode(self, power_mode: VacuumEyePowerMode) -> None:
        """Set power mode."""
        self._send_command(
            "STATE-SET",
            {"data": {"defaultVacuumPowerMode": power_mode.value}},
        )
