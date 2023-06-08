"""Dyson Pure Humidify+Cool device."""

from typing import Optional

from .const import HumidifyOscillationMode, WaterHardness
from .dyson_pure_cool import DysonPureCoolBase

WATER_HARDNESS_ENUM_TO_STR = {
    WaterHardness.SOFT: "2025",
    WaterHardness.MEDIUM: "1350",
    WaterHardness.HARD: "0675",
}
WATER_HARDNESS_STR_TO_ENUM = {
    str_: enum for enum, str_ in WATER_HARDNESS_ENUM_TO_STR.items()
}


class DysonPurifierHumidifyCool(DysonPureCoolBase):
    """Dyson Pure Humidify+Cool device."""

    @property
    def oscillation(self) -> bool:
        """Return oscillation status."""
        return self._get_field_value(self._status, "oson") == "ON"

    @property
    def oscillation_mode(self) -> HumidifyOscillationMode:
        """Return oscillation mode."""
        return HumidifyOscillationMode(self._get_field_value(self._status, "ancp"))

    @property
    def humidification(self) -> bool:
        """Return if humidification is on."""
        return self._get_field_value(self._status, "hume") == "HUMD"

    @property
    def humidification_auto_mode(self) -> bool:
        """Return if humidification auto mode is on."""
        return self._get_field_value(self._status, "haut") == "ON"

    @property
    def target_humidity(self) -> int:
        """Return target humidity in percentage."""
        return int(self._get_field_value(self._status, "humt"))

    @property
    def auto_target_humidity(self) -> int:
        """Return humidification auto mode target humidity."""
        return int(self._get_field_value(self._status, "rect"))

    @property
    def water_hardness(self) -> WaterHardness:
        """Return the water hardness setting."""
        return WATER_HARDNESS_STR_TO_ENUM[self._get_field_value(self._status, "wath")]

    @property
    def time_until_next_clean(self) -> int:
        """Return the time remaining in hours before the next deep cleaning."""
        return int(self._get_field_value(self._status, "cltr"))

    @property
    def clean_time_remaining(self) -> int:
        """Return the time remaining in minutes before the cleaning finishes."""
        return int(self._get_field_value(self._status, "cdrr"))

    def enable_oscillation(
        self, oscillation_mode: Optional[HumidifyOscillationMode] = None
    ) -> None:
        """Turn on oscillation."""
        if oscillation_mode is None:
            oscillation_mode = self.oscillation_mode

        self._set_configuration(oson="ON", fpwr="ON", ancp=oscillation_mode.value)

    def disable_oscillation(self) -> None:
        """Turn off oscillation."""
        self._set_configuration(oson="OFF")

    def enable_humidification(self) -> None:
        """Enable humidification."""
        self._set_configuration(hume="HUMD")

    def disable_humidification(self) -> None:
        """Disable humidification."""
        self._set_configuration(hume="OFF")

    def enable_humidification_auto_mode(self) -> None:
        """Enable humidification auto mode."""
        self._set_configuration(haut="ON")

    def disable_humidification_auto_mode(self) -> None:
        """Disable humidification auto mode."""
        self._set_configuration(haut="OFF")

    def set_target_humidity(self, target_humidity: int) -> None:
        """Set target humidity."""
        self._set_configuration(humt=f"{target_humidity:04d}", haut="OFF")

    def set_water_hardness(self, water_hardness: WaterHardness) -> None:
        """Set water hardness."""
        self._set_configuration(wath=WATER_HARDNESS_ENUM_TO_STR[water_hardness])

