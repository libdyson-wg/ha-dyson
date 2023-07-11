"""Support for Dyson cloud account."""

import asyncio
import logging
from functools import partial

from homeassistant.exceptions import ConfigEntryNotReady
from ..vendor.libdyson.cloud.account import DysonAccountCN
from ..vendor.libdyson.cloud.device_info import DysonDeviceInfo
from ..vendor.libdyson.const import DEVICE_TYPE_360_EYE
from ..vendor.libdyson.discovery import DysonDiscovery
from ..vendor.libdyson.dyson_device import DysonDevice
from ..vendor.libdyson.exceptions import DysonException, DysonNetworkError
from homeassistant.config_entries import ConfigEntry, SOURCE_DISCOVERY
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.components.zeroconf import async_get_instance
from ..vendor.libdyson.cloud import DysonAccount
from custom_components.dyson_local import DOMAIN as DYSON_LOCAL_DOMAIN

from .const import CONF_AUTH, CONF_REGION, DATA_ACCOUNT, DATA_DEVICES, DOMAIN

_LOGGER = logging.getLogger(__name__)
