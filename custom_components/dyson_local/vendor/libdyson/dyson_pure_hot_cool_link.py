"""Dyson Pure Hot+Cool Link device."""

from .dyson_device import DysonHeatingDevice
from .dyson_pure_cool_link import DysonPureCoolLink


class DysonPureHotCoolLink(DysonPureCoolLink, DysonHeatingDevice):
    """Dyson Pure Hot+Cool Link device."""

    @property
    def tilt(self) -> bool:
        """Return tilt status."""
        return self._get_field_value(self._status, "tilt") == "TILT"

    def enable_focus_mode(self) -> None:
        """Enable fan focus mode."""
        self._set_configuration(ffoc="ON")

    def disable_focus_mode(self) -> None:
        """Disable fan focus mode."""
        self._set_configuration(ffoc="OFF")
