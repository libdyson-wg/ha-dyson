"""Dyson Pure Cool Link fan."""

from .const import AirQualityTarget
from .dyson_device import DysonFanDevice


class DysonPureCoolLink(DysonFanDevice):
    """Dyson Pure Cool Link device."""

    @property
    def fan_mode(self) -> str:
        """Return the fan mode of the fan."""
        return self._get_field_value(self._status, "fmod")

    @property
    def is_on(self) -> bool:
        """Return if the device is on."""
        return self.fan_mode in ["FAN", "AUTO"]

    @property
    def auto_mode(self) -> bool:
        """Return auto mode status."""
        return self.fan_mode == "AUTO"

    @property
    def oscillation(self) -> bool:
        """Return oscillation status."""
        return self._get_field_value(self._status, "oson") == "ON"

    @property
    def air_quality_target(self) -> AirQualityTarget:
        """Return air quality target."""
        return AirQualityTarget(self._get_field_value(self._status, "qtar"))

    @property
    def filter_life(self) -> int:
        """Return filter life in hours."""
        return int(self._get_field_value(self._status, "filf"))

    @property
    def particulates(self) -> int:
        """Return particulate matter in unknown unit."""
        return self._get_environmental_field_value("pact")

    @property
    def volatile_organic_compounds(self) -> int:
        """Return VOCs in unknown unit."""
        return self._get_environmental_field_value("vact")

    def turn_on(self) -> None:
        """Turn on the device."""
        self._set_configuration(fmod="FAN")

    def turn_off(self) -> None:
        """Turn off the device."""
        self._set_configuration(fmod="OFF")

    def _set_speed(self, speed: int) -> None:
        self._set_configuration(fmod="FAN", fnsp=f"{speed:04d}")

    def enable_auto_mode(self) -> None:
        """Turn on auto mode."""
        self._set_configuration(fmod="AUTO")

    def disable_auto_mode(self) -> None:
        """Turn off auto mode."""
        self._set_configuration(fmod="FAN")

    def enable_oscillation(self) -> None:
        """Turn on oscillation."""
        self._set_configuration(oson="ON")

    def disable_oscillation(self) -> None:
        """Turn off oscillation."""
        self._set_configuration(oson="OFF")

    def enable_continuous_monitoring(self) -> None:
        """Turn on continuous monitoring."""
        self._set_configuration(
            fmod=self.fan_mode,  # Seems fmod is required to make this work
            rhtm="ON",
        )

    def disable_continuous_monitoring(self) -> None:
        """Turn off continuous monitoring."""
        self._set_configuration(
            fmod=self.fan_mode,
            rhtm="OFF",
        )

    def set_air_quality_target(self, air_quality_target: AirQualityTarget) -> None:
        """Set air quality target."""
        self._set_configuration(qtar=air_quality_target.value)
