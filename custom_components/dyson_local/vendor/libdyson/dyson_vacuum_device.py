"""Dyson vacuum device."""

from typing import Optional, Tuple

from .const import CleaningType, VacuumState
from .dyson_device import DysonDevice


class DysonVacuumDevice(DysonDevice):
    """Dyson vacuum device."""

    @property
    def _status_topic(self) -> str:
        """MQTT status topic."""
        return f"{self.device_type}/{self._serial}/status"

    @property
    def state(self) -> VacuumState:
        """State of the device."""
        return VacuumState(
            self._status["state"]
            if "state" in self._status
            else self._status["newstate"]
        )

    @property
    def cleaning_type(self) -> Optional[CleaningType]:
        """Return the type of the current cleaning task."""
        cleaning_type = self._status["fullCleanType"]
        if cleaning_type == "":
            return None
        return CleaningType(cleaning_type)

    @property
    def cleaning_id(self) -> Optional[str]:
        """Return the id of the current cleaning task."""
        cleaning_id = self._status["cleanId"]
        if cleaning_id == "":
            return None
        return cleaning_id

    @property
    def battery_level(self) -> int:
        """Battery level of the device in percentage."""
        return self._status["batteryChargeLevel"]

    @property
    def position(self) -> Optional[Tuple[int, int]]:
        """Position (x, y) of the device."""
        if (
            "globalPosition" in self._status
            and len(self._status["globalPosition"]) == 2
        ):
            return tuple(self._status["globalPosition"])
        return None

    @property
    def is_charging(self) -> bool:
        """Whether the device is charging."""
        return self.state in [
            VacuumState.INACTIVE_CHARGING,
            VacuumState.INACTIVE_CHARGED,
            VacuumState.FULL_CLEAN_CHARGING,
            VacuumState.MAPPING_CHARGING,
        ]

    def _update_status(self, payload: dict) -> None:
        self._status = payload

    def pause(self) -> None:
        """Pause cleaning."""
        self._send_command("PAUSE")

    def resume(self) -> None:
        """Resume cleaning."""
        self._send_command("RESUME")

    def abort(self) -> None:
        """Abort cleaning."""
        self._send_command("ABORT")
