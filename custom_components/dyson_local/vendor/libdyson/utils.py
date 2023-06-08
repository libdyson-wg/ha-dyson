"""Utility functions for Dyson Python library."""

import base64
import hashlib
import re
import time
from typing import Tuple

from .const import DEVICE_TYPE_360_EYE
from .exceptions import DysonFailedToParseWifiInfo

# For some devices, the model in WiFi SSID is not the same as the model for MQTT.
# The model on Dyson Cloud always matches the one used for MQTT.
_DEVICE_TYPE_MAP = {
    "455A": "455",
}


def mqtt_time():
    """Return current time string for mqtt messages."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def get_credential_from_wifi_password(wifi_password: str) -> str:
    """Calculate MQTT credential from WiFi password."""
    hash_ = hashlib.sha512()
    hash_.update(wifi_password.encode("utf-8"))
    return base64.b64encode(hash_.digest()).decode("utf-8")


def get_mqtt_info_from_wifi_info(
    wifi_ssid: str, wifi_password: str
) -> Tuple[str, str, str]:
    """Get MQTT information from WiFi information."""
    result = re.match(r"^(360EYE-)?(?P<serial>[0-9A-Z]{3}-[A-Z]{2}-[0-9A-Z]{8,})$", wifi_ssid)
    if result is not None:
        serial = result.group("serial")
        device_type = DEVICE_TYPE_360_EYE
    else:
        result = re.match(
            r"^DYSON-([0-9A-Z]{3}-[A-Z]{2}-[0-9A-Z]{8,})-([0-9]{3}[A-Z]?)$", wifi_ssid
        )
        if result is not None:
            serial = result.group(1)
            device_type = result.group(2)
            device_type = _DEVICE_TYPE_MAP.get(device_type, device_type)
        else:
            raise DysonFailedToParseWifiInfo

    credential = get_credential_from_wifi_password(wifi_password)
    return serial, credential, device_type
