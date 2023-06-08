"""Tests for Dyson humidifier platform."""

from unittest.mock import patch

from .vendor.libdyson import DEVICE_TYPE_PURE_HUMIDIFY_COOL, DysonPurifierHumidifyCool, MessageType
from .vendor.libdyson.const import AirQualityTarget
import pytest

from custom_components.dyson_local.humidifier import (
    AVAILABLE_MODES,
    MAX_HUMIDITY,
    MIN_HUMIDITY,
    SUPPORTED_FEATURES,
)
from homeassistant.components.humidifier import (
    ATTR_AVAILABLE_MODES,
    ATTR_HUMIDITY,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    ATTR_MODE,
    DOMAIN as HUMIDIFIER_DOMAIN,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.components.humidifier.const import MODE_AUTO, MODE_NORMAL
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from . import MODULE, NAME, SERIAL, get_base_device, update_device

ENTITY_ID = f"humidifier.{NAME}"


@pytest.fixture
def device() -> DysonPurifierHumidifyCool:
    """Return mocked device."""
    device = get_base_device(DysonPurifierHumidifyCool, DEVICE_TYPE_PURE_HUMIDIFY_COOL)
    device.is_on = True
    device.speed = 5
    device.auto_mode = False
    device.oscillation = True
    device.air_quality_target = AirQualityTarget.GOOD
    device.humidification = True
    device.humidification_auto_mode = True
    device.target_humidity = 50
    with patch(f"{MODULE}._async_get_platforms", return_value=["humidifier"]):
        yield device


async def test_state(hass: HomeAssistant, device: DysonPurifierHumidifyCool):
    """Test entity state and attributes."""
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    attributes = state.attributes
    assert attributes[ATTR_AVAILABLE_MODES] == AVAILABLE_MODES
    assert attributes[ATTR_MODE] == MODE_AUTO
    assert attributes[ATTR_MIN_HUMIDITY] == MIN_HUMIDITY
    assert attributes[ATTR_MAX_HUMIDITY] == MAX_HUMIDITY
    assert attributes[ATTR_HUMIDITY] == 50
    assert attributes[ATTR_SUPPORTED_FEATURES] == SUPPORTED_FEATURES

    er = await entity_registry.async_get_registry(hass)
    assert er.async_get(ENTITY_ID).unique_id == SERIAL

    device.humidification_auto_mode = False
    device.target_humidity = 30
    await update_device(hass, device, MessageType.STATE)
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes[ATTR_MODE] == MODE_NORMAL
    assert attributes[ATTR_HUMIDITY] == 30

    device.humidification = False
    await update_device(hass, device, MessageType.STATE)
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_OFF


@pytest.mark.parametrize(
    "service,service_data,command,command_args",
    [
        (SERVICE_TURN_ON, {}, "enable_humidification", []),
        (SERVICE_TURN_OFF, {}, "disable_humidification", []),
        (SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: 30}, "set_target_humidity", [30]),
        (
            SERVICE_SET_MODE,
            {ATTR_MODE: MODE_AUTO},
            "enable_humidification_auto_mode",
            [],
        ),
        (
            SERVICE_SET_MODE,
            {ATTR_MODE: MODE_NORMAL},
            "disable_humidification_auto_mode",
            [],
        ),
    ],
)
async def test_command(
    hass: HomeAssistant,
    device: DysonPurifierHumidifyCool,
    service: str,
    service_data: dict,
    command: str,
    command_args: list,
):
    """Test platform services."""
    service_data[ATTR_ENTITY_ID] = ENTITY_ID
    await hass.services.async_call(
        HUMIDIFIER_DOMAIN, service, service_data, blocking=True
    )
    func = getattr(device, command)
    func.assert_called_once_with(*command_args)
