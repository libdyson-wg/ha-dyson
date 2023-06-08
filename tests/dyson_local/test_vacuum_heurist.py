"""Tests for Dyson 360 Heurist vacuum platform."""

from unittest.mock import patch

from .vendor.libdyson import (
    DEVICE_TYPE_360_HEURIST,
    Dyson360Heurist,
    MessageType,
    VacuumHeuristPowerMode,
    VacuumState,
)
import pytest

from homeassistant.components.vacuum import (
    ATTR_FAN_SPEED,
    ATTR_FAN_SPEED_LIST,
    DOMAIN as VACUUM_DOMAIN,
    SERVICE_SET_FAN_SPEED,
    SERVICE_START,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from . import MODULE, NAME, get_base_device, update_device

ENTITY_ID = f"vacuum.{NAME}"


@pytest.fixture
def device(request: pytest.FixtureRequest) -> Dyson360Heurist:
    """Return mocked device."""
    device = get_base_device(Dyson360Heurist, DEVICE_TYPE_360_HEURIST)
    device.state = VacuumState.INACTIVE_CHARGING
    device.battery_level = 50
    device.position = (10, 20)
    device.current_power_mode = VacuumHeuristPowerMode.QUIET
    with patch(f"{MODULE}._async_get_platforms", return_value=["vacuum"]):
        yield device


async def test_state(hass: HomeAssistant, device: Dyson360Heurist):
    """Test entity state and attributes."""
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_FAN_SPEED_LIST] == ["Quiet", "High", "Max"]
    assert attributes[ATTR_FAN_SPEED] == "Quiet"

    device.current_power_mode = VacuumHeuristPowerMode.HIGH
    await update_device(hass, device, MessageType.STATE)
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_FAN_SPEED] == "High"

    device.current_power_mode = VacuumHeuristPowerMode.MAX
    await update_device(hass, device, MessageType.STATE)
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_FAN_SPEED] == "Max"


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        (SERVICE_START, {}, "start_all_zones", []),
        (
            SERVICE_SET_FAN_SPEED,
            {ATTR_FAN_SPEED: "Quiet"},
            "set_default_power_mode",
            [VacuumHeuristPowerMode.QUIET],
        ),
        (
            SERVICE_SET_FAN_SPEED,
            {ATTR_FAN_SPEED: "High"},
            "set_default_power_mode",
            [VacuumHeuristPowerMode.HIGH],
        ),
        (
            SERVICE_SET_FAN_SPEED,
            {ATTR_FAN_SPEED: "Max"},
            "set_default_power_mode",
            [VacuumHeuristPowerMode.MAX],
        ),
    ],
)
async def test_command(
    hass: HomeAssistant,
    device: Dyson360Heurist,
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
