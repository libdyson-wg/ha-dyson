"""Tests for Dyson vacuum platform."""

from unittest.mock import patch

from .vendor.libdyson import (
    DEVICE_TYPE_360_EYE,
    DEVICE_TYPE_360_HEURIST,
    Dyson360Eye,
    Dyson360Heurist,
    MessageType,
    VacuumEyePowerMode,
    VacuumHeuristPowerMode,
    VacuumState,
)
from .vendor.libdyson.dyson_vacuum_device import DysonVacuumDevice
import pytest

from custom_components.dyson_local.vacuum import ATTR_POSITION, SUPPORTED_FEATURES
from homeassistant.components.vacuum import (
    ATTR_BATTERY_LEVEL,
    ATTR_STATUS,
    DOMAIN as VACUUM_DOMAIN,
    SERVICE_PAUSE,
    SERVICE_RETURN_TO_BASE,
    SERVICE_START,
    STATE_CLEANING,
    STATE_PAUSED,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from . import MODULE, NAME, SERIAL, get_base_device, update_device

ENTITY_ID = f"vacuum.{NAME}"


@pytest.fixture(
    params=[
        (Dyson360Eye, DEVICE_TYPE_360_EYE),
        (Dyson360Heurist, DEVICE_TYPE_360_HEURIST),
    ]
)
def device(request: pytest.FixtureRequest) -> DysonVacuumDevice:
    """Return mocked device."""
    device = get_base_device(request.param[0], request.param[1])
    device.state = VacuumState.FULL_CLEAN_PAUSED
    device.battery_level = 50
    device.position = (10, 20)
    device.power_mode = VacuumEyePowerMode.QUIET
    device.current_power_mode = VacuumHeuristPowerMode.QUIET
    with patch(f"{MODULE}._async_get_platforms", return_value=["vacuum"]):
        yield device


async def test_state(hass: HomeAssistant, device: DysonVacuumDevice):
    """Test entity state and attributes."""
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_PAUSED
    attributes = state.attributes
    assert attributes[ATTR_STATUS] == "Paused"
    assert attributes[ATTR_BATTERY_LEVEL] == 50
    assert attributes[ATTR_POSITION] == "(10, 20)"
    assert attributes[ATTR_SUPPORTED_FEATURES] == SUPPORTED_FEATURES

    er = await entity_registry.async_get_registry(hass)
    assert er.async_get(ENTITY_ID).unique_id == SERIAL

    device.state = VacuumState.FULL_CLEAN_RUNNING
    device.battery_level = 30
    device.position = (15, 5)
    await update_device(hass, device, MessageType.STATE)
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_CLEANING
    attributes = state.attributes
    assert attributes[ATTR_STATUS] == "Cleaning"
    assert attributes[ATTR_BATTERY_LEVEL] == 30
    assert attributes[ATTR_POSITION] == "(15, 5)"


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        (SERVICE_START, {}, "resume", []),
        (SERVICE_PAUSE, {}, "pause", []),
        (SERVICE_RETURN_TO_BASE, {}, "abort", []),
    ],
)
async def test_command(
    hass: HomeAssistant,
    device: DysonVacuumDevice,
    service: str,
    service_data: dict,
    command: str,
    command_args: list,
):
    """Test platform services."""
    service_data[ATTR_ENTITY_ID] = ENTITY_ID
    await hass.services.async_call(VACUUM_DOMAIN, service, service_data, blocking=True)
    func = getattr(device, command)
    func.assert_called_once_with(*command_args)
