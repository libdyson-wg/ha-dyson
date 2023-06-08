"""Tests for Dyson Pure Hot+Cool Link climate entity."""

from unittest.mock import patch

from .vendor.libdyson import DEVICE_TYPE_PURE_HOT_COOL_LINK, DysonPureHotCoolLink, MessageType
import pytest

from custom_components.dyson_local.climate import FAN_MODES, SUPPORT_FLAGS_LINK
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import (
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    FAN_DIFFUSE,
    FAN_FOCUS,
    SERVICE_SET_FAN_MODE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant

from . import MODULE, NAME, get_base_device, update_device

ENTITY_ID = f"climate.{NAME}"


@pytest.fixture(
    params=[
        (DysonPureHotCoolLink, DEVICE_TYPE_PURE_HOT_COOL_LINK),
    ]
)
def device(request: pytest.FixtureRequest) -> DysonPureHotCoolLink:
    """Return mocked device."""
    device = get_base_device(request.param[0], request.param[1])
    device.is_on = True
    device.heat_mode_is_on = True
    device.heat_status_is_on = True
    device.heat_target = 280
    device.temperature = 275
    device.humidity = 30
    device.focus_mode = False
    with patch(f"{MODULE}._async_get_platforms", return_value=["climate"]):
        yield device


async def test_state(hass: HomeAssistant, device: DysonPureHotCoolLink):
    """Test entity state and attributes."""
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_FAN_MODE] == FAN_DIFFUSE
    assert attributes[ATTR_FAN_MODES] == FAN_MODES
    assert attributes[ATTR_SUPPORTED_FEATURES] == SUPPORT_FLAGS_LINK

    device.focus_mode = True
    await update_device(hass, device, MessageType.STATE)
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_FAN_MODE] == FAN_FOCUS


@pytest.mark.parametrize(
    "service,service_data,command",
    [
        (SERVICE_SET_FAN_MODE, {ATTR_FAN_MODE: FAN_FOCUS}, "enable_focus_mode"),
        (SERVICE_SET_FAN_MODE, {ATTR_FAN_MODE: FAN_DIFFUSE}, "disable_focus_mode"),
    ],
)
async def test_command(
    hass: HomeAssistant,
    device: DysonPureHotCoolLink,
    service: str,
    service_data: dict,
    command: str,
):
    """Test platform services."""
    service_data[ATTR_ENTITY_ID] = ENTITY_ID
    await hass.services.async_call(CLIMATE_DOMAIN, service, service_data, blocking=True)
    func = getattr(device, command)
    func.assert_called_once_with()
