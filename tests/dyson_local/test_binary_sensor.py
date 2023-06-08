"""Tests for Dyson binary_sensor platform."""

from unittest.mock import patch

from .vendor.libdyson import (
    DEVICE_TYPE_360_EYE,
    DEVICE_TYPE_360_HEURIST,
    Dyson360Eye,
    Dyson360Heurist,
)
from .vendor.libdyson.const import MessageType
from .vendor.libdyson.dyson_vacuum_device import DysonVacuumDevice
import pytest

from custom_components.dyson_local.binary_sensor import ICON_BIN_FULL
from homeassistant.components.binary_sensor import DEVICE_CLASS_BATTERY_CHARGING
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ICON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from . import MODULE, NAME, SERIAL, get_base_device, update_device


@pytest.fixture
def device(request: pytest.FixtureRequest) -> DysonVacuumDevice:
    """Return mocked device."""
    with patch(f"{MODULE}._async_get_platforms", return_value=["binary_sensor"]):
        yield request.param()


def _get_360_eye() -> Dyson360Eye:
    device = get_base_device(Dyson360Eye, DEVICE_TYPE_360_EYE)
    device.is_charging = False
    return device


def _get_360_heurist() -> Dyson360Heurist:
    device = get_base_device(Dyson360Heurist, DEVICE_TYPE_360_HEURIST)
    device.is_charging = False
    device.is_bin_full = False
    return device


@pytest.mark.parametrize(
    "device",
    [_get_360_eye, _get_360_heurist],
    indirect=["device"],
)
async def test_is_charging_sensor(
    hass: HomeAssistant,
    device: DysonVacuumDevice,
):
    """Test is charging sensor."""
    er = await entity_registry.async_get_registry(hass)
    entity_id = f"binary_sensor.{NAME}_battery_charging"
    state = hass.states.get(entity_id)
    assert state.name == f"{NAME} Battery Charging"
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_DEVICE_CLASS] == DEVICE_CLASS_BATTERY_CHARGING
    assert er.async_get(entity_id).unique_id == f"{SERIAL}-battery_charging"

    device.is_charging = True
    await update_device(hass, device, MessageType.STATE)
    assert hass.states.get(entity_id).state == STATE_ON


@pytest.mark.parametrize(
    "device",
    [_get_360_heurist],
    indirect=["device"],
)
async def test_bin_full_sensor(
    hass: HomeAssistant,
    device: Dyson360Heurist,
):
    """Test bin full sensor."""
    er = await entity_registry.async_get_registry(hass)
    entity_id = f"binary_sensor.{NAME}_bin_full"
    state = hass.states.get(entity_id)
    assert state.name == f"{NAME} Bin Full"
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_ICON] == ICON_BIN_FULL
    assert er.async_get(entity_id).unique_id == f"{SERIAL}-bin_full"

    device.is_bin_full = True
    await update_device(hass, device, MessageType.STATE)
    assert hass.states.get(entity_id).state == STATE_ON
