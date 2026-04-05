"""Tests for HushJet Purifier Compact (HJ10 / 897) device support.

These tests mock homeassistant so they can run without the full HA install.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# Stub out homeassistant modules so the integration can be imported.
_HA_STUBS = {}
for mod_name in [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.zeroconf",
    "homeassistant.components.mqtt",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.update_coordinator",
]:
    stub = ModuleType(mod_name)
    # Provide common names so from-imports succeed.
    stub.__dict__.setdefault("async_get_instance", MagicMock())
    stub.__dict__.setdefault("ConfigEntry", MagicMock())
    stub.__dict__.setdefault("SOURCE_DISCOVERY", "discovery")
    stub.__dict__.setdefault("CONN_CLASS_LOCAL_PUSH", "local_push")
    stub.__dict__.setdefault("CONF_HOST", "host")
    stub.__dict__.setdefault("CONF_NAME", "name")
    stub.__dict__.setdefault("CONF_EMAIL", "email")
    stub.__dict__.setdefault("CONF_PASSWORD", "password")
    stub.__dict__.setdefault("CONF_USERNAME", "username")
    stub.__dict__.setdefault("EVENT_HOMEASSISTANT_STOP", "stop")
    stub.__dict__.setdefault("HomeAssistant", MagicMock())
    stub.__dict__.setdefault("callback", lambda f: f)
    stub.__dict__.setdefault("HomeAssistantError", Exception)
    stub.__dict__.setdefault("ConfigEntryNotReady", Exception)
    stub.__dict__.setdefault("Entity", type("Entity", (), {}))
    stub.__dict__.setdefault(
        "DataUpdateCoordinator", type("DataUpdateCoordinator", (), {})
    )
    stub.__dict__.setdefault("UpdateFailed", Exception)
    stub.__dict__.setdefault("config_entries", MagicMock())
    _HA_STUBS[mod_name] = stub

# Also need voluptuous
try:
    import voluptuous  # noqa: F401
except ImportError:
    vol_stub = ModuleType("voluptuous")
    vol_stub.Schema = MagicMock()
    vol_stub.Required = MagicMock()
    vol_stub.Optional = MagicMock()
    vol_stub.In = MagicMock()
    _HA_STUBS["voluptuous"] = vol_stub

for name, mod in _HA_STUBS.items():
    sys.modules.setdefault(name, mod)


# ---- actual tests ----

from custom_components.dyson_local.const import DEVICE_TYPE_HUSHJET  # noqa: E402


class TestHushJetConstants:
    """Test device type constant value."""

    def test_device_type_is_897(self):
        assert DEVICE_TYPE_HUSHJET == "897"


class TestHushJetCloudMapping:
    """Test that 897 / HJ10 / M4P product types resolve correctly."""

    def test_897_in_cloud_mapping(self):
        from custom_components.dyson_local.config_flow import (
            CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE,
        )

        assert CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE["897"] == DEVICE_TYPE_HUSHJET

    def test_m4p_in_cloud_mapping(self):
        from custom_components.dyson_local.config_flow import (
            CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE,
        )

        assert CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE["M4P"] == DEVICE_TYPE_HUSHJET

    def test_hj10_in_cloud_mapping(self):
        from custom_components.dyson_local.config_flow import (
            CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE,
        )

        assert CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE["HJ10"] == DEVICE_TYPE_HUSHJET

    def test_hushjet_in_device_type_names(self):
        from custom_components.dyson_local.config_flow import DEVICE_TYPE_NAMES

        assert DEVICE_TYPE_HUSHJET in DEVICE_TYPE_NAMES
        assert "HushJet" in DEVICE_TYPE_NAMES[DEVICE_TYPE_HUSHJET]


class TestHushJetGetDevice:
    """Test that the local get_device wrapper creates a DysonPureCool for 897."""

    @patch("custom_components.dyson_local._libdyson_get_device", return_value=None)
    def test_get_device_creates_pure_cool_for_hushjet(self, mock_get):
        from libdyson import DysonPureCool

        from custom_components.dyson_local import get_device

        device = get_device("SERIAL", "CRED", DEVICE_TYPE_HUSHJET)
        assert isinstance(device, DysonPureCool)
        assert device.serial == "SERIAL"

    @patch("custom_components.dyson_local._libdyson_get_device")
    def test_get_device_delegates_known_types(self, mock_get):
        sentinel = MagicMock()
        mock_get.return_value = sentinel

        from custom_components.dyson_local import get_device

        device = get_device("SERIAL", "CRED", "438")
        assert device is sentinel

    @patch("custom_components.dyson_local._libdyson_get_device", return_value=None)
    def test_get_device_returns_none_for_unknown(self, mock_get):
        from custom_components.dyson_local import get_device

        assert get_device("SERIAL", "CRED", "UNKNOWN") is None
