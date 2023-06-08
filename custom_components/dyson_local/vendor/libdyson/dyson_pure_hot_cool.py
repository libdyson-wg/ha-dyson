"""Dyson Pure Hot+Cool device."""

from .dyson_device import DysonHeatingDevice
from .dyson_pure_cool import DysonPureCool


class DysonPureHotCool(DysonPureCool, DysonHeatingDevice):
    """Dyson Pure Hot+Cool device."""
