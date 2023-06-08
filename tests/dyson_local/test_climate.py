"""Tests for Dyson climate platform."""

from unittest.mock import patch

from .vendor.libdyson import (
    DEVICE_TYPE_PURE_HOT_COOL,
    DEVICE_TYPE_PURE_HOT_COOL_LINK,
    DysonPureHotCool,
    DysonPureHotCoolLink,
    MessageType,
)
from .vendor.libdyson.const import ENVIRONMENTAL_INIT
from .vendor.libdyson.dyson_device import DysonHeatingDevice
import pytest

from custom_components.dyson_local.climate import HVAC_MODES, SUPPORT_FLAGS
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from . import MODULE, NAME, SERIAL, get_base_device, update_device

ENTITY_ID = f"climate.{NAME}"


@pytest.fixture(
    params=[
        (DysonPureHotCool, DEVICE_TYPE_PURE_HOT_COOL),
        (DysonPureHotCoolLink, DEVICE_TYPE_PURE_HOT_COOL_LINK),
    ]
)
def device(request: pytest.FixtureRequest) -> DysonHeatingDevice:
    """Return mocked device."""
    device = get_base_device(request.param[0], request.param[1])
    device.is_on = True
    device.heat_mode_is_on = True
    device.heat_status_is_on = True
    device.heat_target = 280
    device.temperature = 275
    device.humidity = 30
    with patch(f"{MODULE}._async_get_platforms", return_value=["climate"]):
        yield device


async def test_state(hass: HomeAssistant, device: DysonHeatingDevice):
    """Test entity state and attributes."""
    state = hass.states.get(ENTITY_ID)
    state.state == HVAC_MODE_HEAT
    attributes = state.attributes
    assert attributes[ATTR_HVAC_MODES] == HVAC_MODES
    assert attributes[ATTR_HVAC_ACTION] == CURRENT_HVAC_HEAT
    assert attributes[ATTR_SUPPORTED_FEATURES] & SUPPORT_FLAGS == SUPPORT_FLAGS
    assert attributes[ATTR_TEMPERATURE] == 7
    assert attributes[ATTR_MIN_TEMP] == 1
    assert attributes[ATTR_MAX_TEMP] == 37
    assert attributes[ATTR_CURRENT_TEMPERATURE] == 1.9
    assert attributes[ATTR_CURRENT_HUMIDITY] == 30

    er = await entity_registry.async_get_registry(hass)
    assert er.async_get(ENTITY_ID).unique_id == SERIAL

    device.heat_status_is_on = False
    device.heat_target = 285
    device.temperature = ENVIRONMENTAL_INIT
    device.humidity = 40
    await update_device(hass, device, MessageType.STATE)
    state = hass.states.get(ENTITY_ID)
    attributes = state.attributes
    assert attributes[ATTR_HVAC_ACTION] == CURRENT_HVAC_IDLE
    assert attributes[ATTR_TEMPERATURE] == 12
    assert attributes[ATTR_CURRENT_TEMPERATURE] is None
    assert attributes[ATTR_CURRENT_HUMIDITY] == 40

    device.heat_mode_is_on = False
    await update_device(hass, device, MessageType.STATE)
    state = hass.states.get(ENTITY_ID)
    state.state == HVAC_MODE_COOL
    attributes = state.attributes
    assert attributes[ATTR_HVAC_ACTION] == CURRENT_HVAC_COOL

    device.is_on = False
    await update_device(hass, device, MessageType.STATE)
    state = hass.states.get(ENTITY_ID)
    state.state == HVAC_MODE_OFF
    attributes = state.attributes
    assert attributes[ATTR_HVAC_ACTION] == CURRENT_HVAC_OFF


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        (SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: 5}, "set_heat_target", [278]),
        (SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: 0}, "set_heat_target", [274]),
        (SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: 312}, "set_heat_target", [310]),
        (SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: HVAC_MODE_OFF}, "turn_off", []),
        (
            SERVICE_SET_HVAC_MODE,
            {ATTR_HVAC_MODE: HVAC_MODE_HEAT},
            "enable_heat_mode",
            [],
        ),
        (
            SERVICE_SET_HVAC_MODE,
            {ATTR_HVAC_MODE: HVAC_MODE_COOL},
            "disable_heat_mode",
            [],
        ),
    ],
)
async def test_command(
    hass: HomeAssistant,
    device: DysonHeatingDevice,
    service: str,
    service_data: dict,
    command: str,
    command_args: list,
):
    """Test platform services."""
    service_data[ATTR_ENTITY_ID] = ENTITY_ID
    await hass.services.async_call(CLIMATE_DOMAIN, service, service_data, blocking=True)
    func = getattr(device, command)
    func.assert_called_once_with(*command_args)


async def test_set_hvac_mode_off(hass: HomeAssistant, device: DysonHeatingDevice):
    """Test setting HVAC mode to OFF."""
    device.is_on = False
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVAC_MODE_HEAT},
        blocking=True,
    )
    device.turn_on.assert_called_once_with()
    device.enable_heat_mode.assert_called_once_with()


async def test_set_temperature_invalid_data(
    hass: HomeAssistant, device: DysonHeatingDevice
):
    """Test setting temperature with invalid data."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_TARGET_TEMP_LOW: 5,
            ATTR_TARGET_TEMP_HIGH: 8,
        },
        blocking=True,
    )
    device.set_heat_target.assert_not_called()
