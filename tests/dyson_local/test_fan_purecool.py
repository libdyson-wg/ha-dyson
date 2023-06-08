"""Tests for Dyson Pure Cool fan entity."""

from unittest.mock import patch

from .vendor.libdyson import DEVICE_TYPE_PURE_COOL, DysonPureCool
from .vendor.libdyson.const import MessageType
import pytest

from custom_components.dyson_local import DOMAIN
from custom_components.dyson_local.fan import (
    ATTR_ANGLE_HIGH,
    ATTR_ANGLE_LOW,
    SERVICE_SET_ANGLE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from . import MODULE, NAME, get_base_device, update_device

ENTITY_ID = f"fan.{NAME}"


@pytest.fixture
def device() -> DysonPureCool:
    """Return mocked device."""
    device = get_base_device(DysonPureCool, DEVICE_TYPE_PURE_COOL)
    device.is_on = True
    device.speed = 5
    device.auto_mode = False
    device.oscillation = True
    device.oscillation_angle_low = 10
    device.oscillation_angle_high = 100
    with patch(f"{MODULE}._async_get_platforms", return_value=["fan"]):
        yield device


async def test_state(hass: HomeAssistant, device: DysonPureCool):
    """Test entity state and attributes."""
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_ANGLE_LOW] == 10
    assert attributes[ATTR_ANGLE_HIGH] == 100
    device.oscillation_angle_low = 50
    device.oscillation_angle_high = 300
    await update_device(hass, device, MessageType.STATE)
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_ANGLE_LOW] == 50
    assert attributes[ATTR_ANGLE_HIGH] == 300


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        (
            SERVICE_SET_ANGLE,
            {ATTR_ANGLE_LOW: 5, ATTR_ANGLE_HIGH: 300},
            "enable_oscillation",
            [5, 300],
        )
    ],
)
async def test_service(
    hass: HomeAssistant,
    device: DysonPureCool,
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
