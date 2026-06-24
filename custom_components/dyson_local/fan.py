"""Fan platform for dyson."""

import logging
import math
from typing import Any, Callable, List, Mapping, Optional

from .vendor.libdyson import DysonPureCool, DysonPureCoolLink, MessageType
import voluptuous as vol

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntityFeature,
    FanEntity,
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

# Oscillation angle constraints, matching what the Dyson app enforces.
# Individual angles must be within MIN-MAX. When sweeping (angle_low != angle_high),
# the sweep width must be within MIN_SWEEP-MAX_SWEEP.
MIN_OSCILLATION_ANGLE = 5
MAX_OSCILLATION_ANGLE = 355
MIN_OSCILLATION_SWEEP = 45
MAX_OSCILLATION_SWEEP = 350

# Default angle range used when oscillation is enabled via the standard
# fan.oscillate service but the stored angles are invalid (e.g. equal,
# or outside the valid sweep window). 90 degree sweep centered ahead.
DEFAULT_OSCILLATION_ANGLE_LOW = 135
DEFAULT_OSCILLATION_ANGLE_HIGH = 225

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

    @property
    def is_on(self) -> bool:
        """Return if the fan is on."""
        return self._device.is_on

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
        if preset_mode == PRESET_MODE_AUTO:
            self._device.enable_auto_mode()
        elif preset_mode == PRESET_MODE_NORMAL:
            self._device.disable_auto_mode()
        else:
            raise NotValidPresetModeError(f"Invalid preset mode: {preset_mode}")

    @property
    def oscillating(self):
        """Return the oscillation state."""
        return self._device.oscillation

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
        if preset_mode:
            self.set_preset_mode(preset_mode)
        if percentage:
            self.set_percentage(percentage)

        self._device.turn_on()

    def turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        _LOGGER.debug("Turn off fan %s", self.name)
        return self._device.turn_off()

    def oscillate(self, oscillating: bool) -> None:
        """Turn on/off oscillation."""
        _LOGGER.debug("Turn oscillation %s for device %s", oscillating, self.name)
        if oscillating:
            angle_low = getattr(self._device, "oscillation_angle_low", None)
            angle_high = getattr(self._device, "oscillation_angle_high", None)

            # Angle-capable fans need oson + ancp + osal + osau sent together.
            # Sending oson alone causes the fan to start oscillating then bail.
            if angle_low is not None and angle_high is not None:
                sweep = angle_high - angle_low
                if sweep < MIN_OSCILLATION_SWEEP or sweep > MAX_OSCILLATION_SWEEP:
                    _LOGGER.debug(
                        "Stored oscillation range (%s-%s, %s degree sweep) is "
                        "outside the %s-%s degree valid range; using default %s degree sweep",
                        angle_low,
                        angle_high,
                        sweep,
                        MIN_OSCILLATION_SWEEP,
                        MAX_OSCILLATION_SWEEP,
                        DEFAULT_OSCILLATION_ANGLE_HIGH - DEFAULT_OSCILLATION_ANGLE_LOW,
                    )
                    angle_low = DEFAULT_OSCILLATION_ANGLE_LOW
                    angle_high = DEFAULT_OSCILLATION_ANGLE_HIGH
                self._device.enable_oscillation(angle_low, angle_high)
            else:
                # Pure Cool Link models do not support angle bounds
                self._device.enable_oscillation()
        else:
            self._device.disable_oscillation()

    def set_timer(self, timer: int) -> None:
        """Set sleep timer."""
        if timer == 0:
            self._device.disable_sleep_timer()
        else:
            self._device.set_sleep_timer(timer)


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
        return {
            ATTR_ANGLE_LOW: self.angle_low,
            ATTR_ANGLE_HIGH: self.angle_high,
        }

    def set_angle(self, angle_low: int, angle_high: int) -> None:
        """Set oscillation angle."""
        _LOGGER.debug(
            "set low %s and high angle %s for device %s",
            angle_low,
            angle_high,
            self.name,
        )

        # Position bounds apply to both angles regardless of mode
        if not MIN_OSCILLATION_ANGLE <= angle_low <= MAX_OSCILLATION_ANGLE:
            raise ValueError(
                f"angle_low must be between {MIN_OSCILLATION_ANGLE} and "
                f"{MAX_OSCILLATION_ANGLE} (got {angle_low})"
            )
        if not MIN_OSCILLATION_ANGLE <= angle_high <= MAX_OSCILLATION_ANGLE:
            raise ValueError(
                f"angle_high must be between {MIN_OSCILLATION_ANGLE} and "
                f"{MAX_OSCILLATION_ANGLE} (got {angle_high})"
            )

        # Sweep width only applies when actually sweeping (low != high).
        # Equal angles set the fan to a fixed position with oscillation off.
        if angle_low != angle_high:
            sweep = angle_high - angle_low
            if sweep < MIN_OSCILLATION_SWEEP:
                raise ValueError(
                    f"Oscillation sweep too narrow ({sweep} degrees). Minimum "
                    f"is {MIN_OSCILLATION_SWEEP} degrees, or set "
                    f"angle_low == angle_high to point the fan at a fixed "
                    f"position without oscillating."
                )
            if sweep > MAX_OSCILLATION_SWEEP:
                raise ValueError(
                    f"Oscillation sweep too wide ({sweep} degrees). Maximum "
                    f"is {MAX_OSCILLATION_SWEEP} degrees."
                )

        self._device.enable_oscillation(angle_low, angle_high)


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
