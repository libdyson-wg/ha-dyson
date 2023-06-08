"""Tests for Dyson fan platform."""

from unittest.mock import patch

from .vendor.libdyson import DEVICE_TYPE_PURE_COOL, DysonPureCool, DysonPureCoolLink
from .vendor.libdyson.const import DEVICE_TYPE_PURE_COOL_LINK, AirQualityTarget, MessageType
from .vendor.libdyson.dyson_device import DysonFanDevice
import pytest

from custom_components.dyson_local import DOMAIN
from custom_components.dyson_local.fan import (
    ATTR_TIMER,
    COMMON_FEATURES,
    SERVICE_SET_TIMER,
)
from homeassistant.components.fan import (
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    DOMAIN as FAN_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from . import MODULE, NAME, SERIAL, get_base_device, update_device

ENTITY_ID = f"fan.{NAME}"


@pytest.fixture(
    params=[
        (DysonPureCool, DEVICE_TYPE_PURE_COOL),
        (DysonPureCoolLink, DEVICE_TYPE_PURE_COOL_LINK),
    ]
)
def device(request: pytest.FixtureRequest) -> DysonFanDevice:
    """Return mocked device."""
    device = get_base_device(request.param[0], request.param[1])
    device.is_on = True
    device.speed = 5
    device.auto_mode = False
    device.oscillation = True
    device.air_quality_target = AirQualityTarget.GOOD
    with patch(f"{MODULE}._async_get_platforms", return_value=["fan"]):
        yield device


async def test_state(hass: HomeAssistant, device: DysonFanDevice):
    """Test entity state and attributes."""
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    attributes = state.attributes
    assert attributes[ATTR_PERCENTAGE] == 50
    assert attributes[ATTR_PERCENTAGE_STEP] == 10
    assert attributes[ATTR_OSCILLATING] is True
    assert attributes[ATTR_SUPPORTED_FEATURES] == COMMON_FEATURES

    er = await entity_registry.async_get_registry(hass)
    assert er.async_get(ENTITY_ID).unique_id == SERIAL

    device.is_on = False
    device.speed = None
    device.oscillation = False
    await update_device(hass, device, MessageType.STATE)
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    attributes = state.attributes
    assert attributes[ATTR_PERCENTAGE] is None
    assert attributes[ATTR_OSCILLATING] is False


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        ("turn_on", {}, "turn_on", []),
        ("turn_on", {ATTR_PERCENTAGE: 10}, "set_speed", [1]),
        ("turn_off", {}, "turn_off", []),
        ("set_percentage", {ATTR_PERCENTAGE: 80}, "set_speed", [8]),
        ("set_percentage", {ATTR_PERCENTAGE: 0}, "turn_off", []),
        ("oscillate", {ATTR_OSCILLATING: True}, "enable_oscillation", []),
        ("oscillate", {ATTR_OSCILLATING: False}, "disable_oscillation", []),
    ],
)
async def test_command(
    hass: HomeAssistant,
    device: DysonFanDevice,
    service: str,
    service_data: dict,
    command: str,
    command_args: list,
):
    """Test platform services."""
    service_data[ATTR_ENTITY_ID] = ENTITY_ID
    await hass.services.async_call(FAN_DOMAIN, service, service_data, blocking=True)
    func = getattr(device, command)
    func.assert_called_once_with(*command_args)


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        (SERVICE_SET_TIMER, {ATTR_TIMER: 0}, "disable_sleep_timer", []),
        (SERVICE_SET_TIMER, {ATTR_TIMER: 50}, "set_sleep_timer", [50]),
    ],
)
async def test_service(
    hass: HomeAssistant,
    device: DysonFanDevice,
    service: str,
    service_data: dict,
    command: str,
    command_args: list,
):
    """Test custom services."""
    service_data[ATTR_ENTITY_ID] = ENTITY_ID
    await hass.services.async_call(DOMAIN, service, service_data, blocking=True)
    func = getattr(device, command)
    func.assert_called_once_with(*command_args)
