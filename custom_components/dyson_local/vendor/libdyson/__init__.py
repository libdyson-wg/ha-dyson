"""Dyson Python library."""

from typing import Optional
from .const import (
    DEVICE_TYPE_360_EYE,
    DEVICE_TYPE_360_HEURIST,
    DEVICE_TYPE_360_VIS_NAV,
    DEVICE_TYPE_PURE_COOL,
    DEVICE_TYPE_PURIFIER_COOL_E,
    DEVICE_TYPE_PURIFIER_COOL_K,
    DEVICE_TYPE_PURE_COOL_DESK,
    DEVICE_TYPE_PURE_COOL_LINK,
    DEVICE_TYPE_PURE_COOL_LINK_DESK,
    DEVICE_TYPE_PURE_HOT_COOL,
    DEVICE_TYPE_PURIFIER_HOT_COOL_E,
    DEVICE_TYPE_PURIFIER_HOT_COOL_K,
    DEVICE_TYPE_PURE_HOT_COOL_LINK,
    DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_E,
    DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,
    DEVICE_TYPE_PURIFIER_BIG_QUIET,
)

from .const import CleaningMode  # noqa: F401
from .const import CleaningType  # noqa: F401
from .const import DEVICE_TYPE_NAMES  # noqa: F401
from .const import HumidifyOscillationMode  # noqa: F401
from .const import MessageType  # noqa: F401
from .const import VacuumEyePowerMode  # noqa: F401
from .const import VacuumHeuristPowerMode  # noqa: F401
from .const import VacuumVisNavPowerMode  # noqa: F401
from .const import VacuumState  # noqa: F401
from .const import WaterHardness  # noqa: F401
from .discovery import DysonDiscovery  # noqa: F401
from .dyson_360_eye import Dyson360Eye
from .dyson_360_heurist import Dyson360Heurist
from .dyson_360_vis_nav import Dyson360VisNav
from .dyson_device import DysonDevice
from .dyson_pure_cool import DysonPureCool
from .dyson_pure_cool_link import DysonPureCoolLink
from .dyson_pure_hot_cool import DysonPureHotCool
from .dyson_pure_hot_cool_link import DysonPureHotCoolLink
from .dyson_pure_humidify_cool import DysonPurifierHumidifyCool
from .dyson_purifier_big_quiet import DysonBigQuiet
from .utils import get_mqtt_info_from_wifi_info  # noqa: F401


def get_device(serial: str, credential: str, device_type: str) -> Optional[DysonDevice]:
    """Get a new DysonDevice instance."""
    if device_type == DEVICE_TYPE_360_EYE:
        return Dyson360Eye(serial, credential)
    if device_type == DEVICE_TYPE_360_HEURIST:
        return Dyson360Heurist(serial, credential)
    if device_type == DEVICE_TYPE_360_VIS_NAV:
        return Dyson360VisNav(serial, credential)
    if device_type in [
        DEVICE_TYPE_PURE_COOL_LINK_DESK,
        DEVICE_TYPE_PURE_COOL_LINK,
    ]:
        return DysonPureCoolLink(serial, credential, device_type)
    if device_type in [
        DEVICE_TYPE_PURE_COOL,
        DEVICE_TYPE_PURIFIER_COOL_K,
        DEVICE_TYPE_PURIFIER_COOL_E,
        DEVICE_TYPE_PURE_COOL_DESK,
    ]:
        return DysonPureCool(serial, credential, device_type)
    if device_type == DEVICE_TYPE_PURE_HOT_COOL_LINK:
        return DysonPureHotCoolLink(serial, credential, device_type)
    if device_type in [
        DEVICE_TYPE_PURE_HOT_COOL,
        DEVICE_TYPE_PURIFIER_HOT_COOL_E,
        DEVICE_TYPE_PURIFIER_HOT_COOL_K,
    ]:
        return DysonPureHotCool(serial, credential, device_type)
    if device_type in [
        DEVICE_TYPE_PURE_HUMIDIFY_COOL,
        DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,
        DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_E,
    ]:
        return DysonPurifierHumidifyCool(serial, credential, device_type)
    if device_type in {
        DEVICE_TYPE_PURIFIER_BIG_QUIET,
    }:
        return DysonBigQuiet(serial, credential, device_type)
    return None

