"""Fan platform for dyson."""

import logging
import math
from typing import Any, Callable, List, Mapping, Optional

from libdyson import DysonPureCool, DysonPureCoolLink, MessageType
import voluptuous as vol

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
    NotValidPresetModeError,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import DOMAIN, DysonEntity
from .const import DATA_DEVICES

_LOGGER = logging.getLogger(__name__)

ATTR_ANGLE_LOW = "angle_low"
ATTR_ANGLE_HIGH = "angle_high"
ATTR_TIMER = "timer"

SERVICE_SET_ANGLE = "set_angle"
SERVICE_SET_TIMER = "set_timer"

SET_ANGLE_SCHEMA = {
    vol.Required(ATTR_ANGLE_LOW): cv.positive_int,
    vol.Required(ATTR_ANGLE_HIGH): cv.positive_int,
}

SET_TIMER_SCHEMA = {
    vol.Required(ATTR_TIMER): cv.positive_int,
}

PRESET_MODE_AUTO = "Auto"
PRESET_MODE_NORMAL = "Normal"

SUPPORTED_PRESET_MODES = [PRESET_MODE_AUTO, PRESET_MODE_NORMAL]

SPEED_RANGE = (1, 10)

COMMON_FEATURES = (
    FanEntityFeature.OSCILLATE
    | FanEntityFeature.SET_SPEED
    | FanEntityFeature.PRESET_MODE
    | FanEntityFeature.TURN_ON
    | FanEntityFeature.TURN_OFF
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson fan from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    if isinstance(device, DysonPureCoolLink):
        entity = DysonPureCoolLinkEntity(device, name)
    elif isinstance(device, DysonPureCool):
        entity = DysonPureCoolEntity(device, name)
    else:  # DysonPurifierHumidifyCool
        entity = DysonPurifierHumidifyCoolEntity(device, name)
    async_add_entities([entity])

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_SET_TIMER, SET_TIMER_SCHEMA, "set_timer"
    )
    if isinstance(device, DysonPureCool):
        platform.async_register_entity_service(
            SERVICE_SET_ANGLE, SET_ANGLE_SCHEMA, "set_angle"
        )


class DysonFanEntity(DysonEntity, FanEntity):
    """Dyson fan entity base class."""

    _enable_turn_on_off_backwards_compatibility = False

    _MESSAGE_TYPE = MessageType.STATE

    def __init__(self, device, name: str):
        """Initialize the fan entity."""
        super().__init__(device, name)
        _LOGGER.debug("DysonFanEntity created for device %s", device.serial)

    def __getattribute__(self, name):
        """Override to log method calls."""
        attr = super().__getattribute__(name)
        if (
            callable(attr)
            and not name.startswith("_")
            and name not in ["hass", "entity_id", "name"]
        ):
            # Log ALL method calls to see what Home Assistant is trying to call
            _LOGGER.debug(
                "Method %s accessed on fan entity %s",
                name,
                getattr(self, "entity_id", "unknown"),
            )
        elif name in [
            "oscillating",
            "current_direction",
            "angle_low",
            "angle_high",
            "percentage",
            "preset_mode",
        ]:
            # Log important property access
            _LOGGER.debug(
                "Property %s accessed on fan entity %s",
                name,
                getattr(self, "entity_id", "unknown"),
            )
        return attr

    def __setattr__(self, name, value):
        """Log all attribute setting attempts."""
        if not name.startswith("_"):
            _LOGGER.debug(
                "__setattr__ called: Setting %s = %s for device %s",
                name,
                value,
                getattr(self._device, "serial", "Unknown"),
            )
        super().__setattr__(name, value)

    @property
    def is_on(self) -> bool:
        """Return if the fan is on."""
        state = self._device.is_on
        _LOGGER.debug(
            "is_on property accessed for device %s, returning %s",
            self._device.serial,
            state,
        )
        return state

    @property
    def speed(self) -> None:
        """Return None for compatibility with pre-preset_mode state."""
        return None

    @property
    def speed_count(self) -> int:
        """Return the number of different speeds the fan can be set to."""
        return int_states_in_range(SPEED_RANGE)

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        if self._device.speed is None or self._device.auto_mode:
            return None
        if not self._device.is_on:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, int(self._device.speed))

    def set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        _LOGGER.debug(
            "set_percentage() called with %s for device %s",
            percentage,
            self._device.serial,
        )
        if percentage == 0:
            self._device.turn_off()
            return

        dyson_speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        self._device.set_speed(dyson_speed)
        self._device.disable_auto_mode()

    @property
    def preset_modes(self) -> List[str]:
        """Return the preset modes supported."""
        return SUPPORTED_PRESET_MODES

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current selected preset mode."""
        if self._device.auto_mode:
            return PRESET_MODE_AUTO
        else:
            return PRESET_MODE_NORMAL

    def set_preset_mode(self, preset_mode: str) -> None:
        """Configure the preset mode."""
        _LOGGER.debug(
            "set_preset_mode() called with %s for device %s",
            preset_mode,
            self._device.serial,
        )
        if preset_mode == PRESET_MODE_AUTO:
            self._device.enable_auto_mode()
        elif preset_mode == PRESET_MODE_NORMAL:
            self._device.disable_auto_mode()
        else:
            raise NotValidPresetModeError(f"Invalid preset mode: {preset_mode}")

    @property
    def oscillating(self):
        """Return the oscillation state."""
        state = self._device.oscillation
        _LOGGER.debug(
            "oscillating property accessed for device %s, returning %s",
            self._device.serial,
            state,
        )
        return state

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return COMMON_FEATURES

    def turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        _LOGGER.debug("Turn on fan %s with percentage %s", self.name, percentage)
        if kwargs:
            _LOGGER.debug("Additional parameters received: %s", kwargs)

        # Handle ALL possible kwargs that might be passed from scenes
        for key, value in kwargs.items():
            _LOGGER.debug("Processing kwarg: %s = %s", key, value)

        # Handle oscillating parameter for scenes
        oscillating = kwargs.get("oscillating")
        if oscillating is not None:
            _LOGGER.debug(
                "Setting oscillation to %s for device %s",
                oscillating,
                self._device.serial,
            )
            self.oscillate(oscillating)

        # Handle angle parameters that might be passed from scenes
        angle_low = kwargs.get("angle_low")
        angle_high = kwargs.get("angle_high")
        if angle_low is not None and angle_high is not None:
            _LOGGER.debug(
                "Setting oscillation angles to %s-%s for device %s",
                angle_low,
                angle_high,
                self._device.serial,
            )
            if hasattr(self, "set_angle"):
                self.set_angle(int(angle_low), int(angle_high))

        # Handle center point parameter that might be passed from scenes
        oscillation_center = kwargs.get("oscillation_center")
        if oscillation_center is not None:
            _LOGGER.debug(
                "Setting oscillation center to %s for device %s",
                oscillation_center,
                self._device.serial,
            )
            # Convert center to angles using current range
            current_low = self._device.oscillation_angle_low
            current_high = self._device.oscillation_angle_high
            current_range = current_high - current_low
            center = float(oscillation_center)
            new_low = int(center - (current_range / 2))
            new_high = int(center + (current_range / 2))
            if hasattr(self, "set_angle"):
                self.set_angle(new_low, new_high)

        # Handle direction parameter for scenes (if supported)
        direction = kwargs.get("direction")
        if direction is not None and hasattr(self, "set_direction"):
            _LOGGER.debug(
                "Setting direction to %s for device %s", direction, self._device.serial
            )
            self.set_direction(direction)

        if preset_mode:
            self.set_preset_mode(preset_mode)
        if percentage:
            self.set_percentage(percentage)

        _LOGGER.debug("Calling turn_on() for device %s", self._device.serial)
        self._device.turn_on()

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Turn on the fan asynchronously."""
        _LOGGER.debug(
            "async_turn_on() called: Turn on fan %s with percentage %s",
            self.name,
            percentage,
        )
        if kwargs:
            _LOGGER.debug("async_turn_on() Additional parameters received: %s", kwargs)

        # Handle ALL possible kwargs that might be passed from scenes
        for key, value in kwargs.items():
            _LOGGER.debug("async_turn_on() Processing kwarg: %s = %s", key, value)

        # Handle oscillating parameter for scenes
        oscillating = kwargs.get("oscillating")
        if oscillating is not None:
            _LOGGER.debug(
                "async_turn_on() Setting oscillation to %s for device %s",
                oscillating,
                self._device.serial,
            )
            await self.hass.async_add_executor_job(self.oscillate, oscillating)

        # Handle angle parameters that might be passed from scenes
        angle_low = kwargs.get("angle_low")
        angle_high = kwargs.get("angle_high")
        if angle_low is not None and angle_high is not None:
            _LOGGER.debug(
                "async_turn_on() Setting oscillation angles to %s-%s for device %s",
                angle_low,
                angle_high,
                self._device.serial,
            )
            if hasattr(self, "set_angle"):
                await self.hass.async_add_executor_job(
                    self.set_angle, int(angle_low), int(angle_high)
                )

        # Handle center point parameter that might be passed from scenes
        oscillation_center = kwargs.get("oscillation_center")
        if oscillation_center is not None:
            _LOGGER.debug(
                "async_turn_on() Setting oscillation center to %s for device %s",
                oscillation_center,
                self._device.serial,
            )
            # Convert center to angles using current range
            current_low = self._device.oscillation_angle_low
            current_high = self._device.oscillation_angle_high
            current_range = current_high - current_low
            center = float(oscillation_center)
            new_low = int(center - (current_range / 2))
            new_high = int(center + (current_range / 2))
            if hasattr(self, "set_angle"):
                await self.hass.async_add_executor_job(
                    self.set_angle, new_low, new_high
                )

        # Handle direction parameter for scenes (if supported)
        direction = kwargs.get("direction")
        if direction is not None and hasattr(self, "set_direction"):
            _LOGGER.debug(
                "async_turn_on() Setting direction to %s for device %s",
                direction,
                self._device.serial,
            )
            await self.hass.async_add_executor_job(self.set_direction, direction)

        if preset_mode:
            await self.hass.async_add_executor_job(self.set_preset_mode, preset_mode)
        if percentage:
            await self.hass.async_add_executor_job(self.set_percentage, percentage)

        _LOGGER.debug(
            "async_turn_on() Calling turn_on() for device %s", self._device.serial
        )
        await self.hass.async_add_executor_job(self._device.turn_on)

    def turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        _LOGGER.debug("turn_off() called for fan %s", self.name)
        if kwargs:
            _LOGGER.debug("turn_off() Additional parameters received: %s", kwargs)
        _LOGGER.debug("Calling turn_off() for device %s", self._device.serial)
        return self._device.turn_off()

    def oscillate(self, oscillating: bool) -> None:
        """Turn on/of oscillation."""
        _LOGGER.debug(
            "oscillate() called: Turn oscillation %s for device %s",
            oscillating,
            self.name,
        )
        _LOGGER.debug(
            "Device %s connected: %s", self._device.serial, self._device.is_connected
        )

        # Log current oscillation state
        current_state = self._device.oscillation
        _LOGGER.debug(
            "Current oscillation state: %s, requested: %s", current_state, oscillating
        )

        if oscillating:
            _LOGGER.debug(
                "Calling enable_oscillation() for device %s", self._device.serial
            )
            self._device.enable_oscillation()
        else:
            _LOGGER.debug(
                "Calling disable_oscillation() for device %s", self._device.serial
            )
            self._device.disable_oscillation()

        # Log result
        new_state = self._device.oscillation
        _LOGGER.debug("Oscillation state after change: %s", new_state)

    async def async_oscillate(self, oscillating: bool) -> None:
        """Turn on/of oscillation asynchronously."""
        _LOGGER.debug(
            "async_oscillate() called: Turn oscillation %s for device %s",
            oscillating,
            self.name,
        )
        await self.hass.async_add_executor_job(self.oscillate, oscillating)

    def set_timer(self, timer: int) -> None:
        """Set sleep timer."""
        if timer == 0:
            self._device.disable_sleep_timer()
        else:
            self._device.set_sleep_timer(timer)

    async def async_set_state(self, **kwargs):
        """Handle setting fan state from Home Assistant."""
        _LOGGER.debug(
            "async_set_state called with kwargs: %s for device %s",
            kwargs,
            self._device.serial,
        )

        # Handle oscillation settings
        if "oscillating" in kwargs:
            oscillating = kwargs["oscillating"]
            _LOGGER.debug("Setting oscillating to %s via async_set_state", oscillating)
            await self.async_add_executor_job(self.oscillate, oscillating)

        # Handle center point / angles
        if "oscillation_center" in kwargs:
            center = kwargs["oscillation_center"]
            _LOGGER.debug(
                "Setting oscillation center to %s via async_set_state", center
            )
            # Convert center back to angles (assuming current range)
            current_low = self._device.oscillation_angle_low
            current_high = self._device.oscillation_angle_high
            current_range = current_high - current_low
            new_low = center - (current_range / 2)
            new_high = center + (current_range / 2)
            await self.async_add_executor_job(
                self.set_angle, int(new_low), int(new_high)
            )

        # Handle angle settings
        if "angle_low" in kwargs and "angle_high" in kwargs:
            low = kwargs["angle_low"]
            high = kwargs["angle_high"]
            _LOGGER.debug("Setting angles to %s-%s via async_set_state", low, high)
            await self.async_add_executor_job(self.set_angle, low, high)

        # Handle other standard fan properties
        if "percentage" in kwargs:
            percentage = kwargs["percentage"]
            _LOGGER.debug("Setting percentage to %s via async_set_state", percentage)
            await self.async_add_executor_job(self.set_percentage, percentage)

        if "preset_mode" in kwargs:
            preset_mode = kwargs["preset_mode"]
            _LOGGER.debug("Setting preset_mode to %s via async_set_state", preset_mode)
            await self.async_add_executor_job(self.set_preset_mode, preset_mode)

        if "direction" in kwargs:
            direction = kwargs["direction"]
            _LOGGER.debug("Setting direction to %s via async_set_state", direction)
            await self.async_add_executor_job(self.set_direction, direction)

    async def async_handle_service_call(self, service_name: str, **kwargs):
        """Handle service calls that might be made to the fan entity."""
        _LOGGER.debug(
            "async_handle_service_call called: %s with kwargs: %s for device %s",
            service_name,
            kwargs,
            self._device.serial,
        )

        if service_name == "set_fan_state":
            await self.async_set_state(**kwargs)
        elif service_name == "turn_on":
            await self.async_turn_on(**kwargs)
        elif service_name == "set_oscillating":
            oscillating = kwargs.get("oscillating", False)
            await self.async_oscillate(oscillating)
        elif service_name == "set_angle":
            low = kwargs.get("angle_low", 0)
            high = kwargs.get("angle_high", 0)
            await self.async_add_executor_job(self.set_angle, low, high)


class DysonPureCoolLinkEntity(DysonFanEntity):
    """Dyson Pure Cool Link entity."""


class DysonPureCoolEntity(DysonFanEntity):
    """Dyson Pure Cool entity."""

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return COMMON_FEATURES | FanEntityFeature.DIRECTION

    @property
    def current_direction(self) -> str:
        """Return the current airflow direction."""
        if self._device.front_airflow:
            return DIRECTION_FORWARD
        else:
            return DIRECTION_REVERSE

    def set_direction(self, direction: str) -> None:
        """Configure the airflow direction."""
        _LOGGER.debug(
            "set_direction() called with %s for device %s",
            direction,
            self._device.serial,
        )
        if direction == DIRECTION_FORWARD:
            self._device.enable_front_airflow()
        elif direction == DIRECTION_REVERSE:
            self._device.disable_front_airflow()
        else:
            raise ValueError(f"Invalid direction {direction}")

    @property
    def angle_low(self) -> int:
        """Return oscillation angle low."""
        return self._device.oscillation_angle_low

    @property
    def angle_high(self) -> int:
        """Return oscillation angle high."""
        return self._device.oscillation_angle_high

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return fan-specific state attributes."""
        attributes = {
            ATTR_ANGLE_LOW: self.angle_low,
            ATTR_ANGLE_HIGH: self.angle_high,
        }

        # Add oscillation range information if supported
        if hasattr(self._device, "oscillation_angle_low") and hasattr(
            self._device, "oscillation_angle_high"
        ):
            low_angle = self._device.oscillation_angle_low
            high_angle = self._device.oscillation_angle_high

            # Calculate range and center
            angle_range = high_angle - low_angle if high_angle >= low_angle else 0
            center_angle = (
                (low_angle + high_angle) / 2 if high_angle >= low_angle else 0
            )

            # Determine oscillation range preset
            oscillation_range_preset = "off"
            if self._device.oscillation:
                if angle_range == 45:
                    oscillation_range_preset = "45"
                elif angle_range == 90:
                    oscillation_range_preset = "90"
                elif angle_range == 180:
                    oscillation_range_preset = "180"
                elif angle_range == 350:
                    oscillation_range_preset = "350"
                else:
                    oscillation_range_preset = "custom"

            attributes.update(
                {
                    "oscillation_range": angle_range,
                    "oscillation_center": round(center_angle, 1),
                    "oscillation_range_preset": oscillation_range_preset,
                }
            )

        return attributes

    def set_angle(self, angle_low: int, angle_high: int) -> None:
        """Set oscillation angle."""
        _LOGGER.debug(
            "set_angle() called: set low %s and high angle %s for device %s",
            angle_low,
            angle_high,
            self.name,
        )

        # Log current angles
        current_low = self._device.oscillation_angle_low
        current_high = self._device.oscillation_angle_high
        _LOGGER.debug("Current angles: low=%s, high=%s", current_low, current_high)

        self._device.enable_oscillation(angle_low, angle_high)

        # Log result
        new_low = self._device.oscillation_angle_low
        new_high = self._device.oscillation_angle_high
        _LOGGER.debug("Angles after change: low=%s, high=%s", new_low, new_high)


class DysonPurifierHumidifyCoolEntity(DysonFanEntity):
    """Dyson Pure Humidify+Cool entity."""

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return COMMON_FEATURES | FanEntityFeature.DIRECTION

    @property
    def current_direction(self) -> str:
        """Return the current airflow direction."""
        if self._device.front_airflow:
            return DIRECTION_FORWARD
        else:
            return DIRECTION_REVERSE

    def set_direction(self, direction: str) -> None:
        """Configure the airflow direction."""
        if direction == DIRECTION_FORWARD:
            self._device.enable_front_airflow()
        elif direction == DIRECTION_REVERSE:
            self._device.disable_front_airflow()
        else:
            raise ValueError(f"Invalid direction {direction}")
