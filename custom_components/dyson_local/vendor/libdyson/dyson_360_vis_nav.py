"""Dyson 360 Vis Nav vacuum robot."""

from .const import DEVICE_TYPE_360_VIS_NAV
from .dyson_360_heurist import Dyson360Heurist


class Dyson360VisNav(Dyson360Heurist):
    """Dyson 360 Vis Nav device."""

    @property
    def device_type(self) -> str:
        """Return the device type."""
        return DEVICE_TYPE_360_VIS_NAV
