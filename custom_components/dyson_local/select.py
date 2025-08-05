"""Select platform for dyson."""

import logging
from typing import Callable

from .vendor.libdyson import (
    DysonPureCool,
    DysonPureCoolLink,
    DysonPureHotCoolLink,
    DysonPurifierHumidifyCool,
    HumidifyOscillationMode,
    Tilt,
    WaterHardness,
    DysonBigQuiet,
)
from .vendor.libdyson.const import AirQualityTarget

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DysonEntity
from .const import DATA_DEVICES, DOMAIN

_LOGGER = logging.getLogger(__name__)

AIR_QUALITY_TARGET_ENUM_TO_STR = {
    AirQualityTarget.OFF: "Off",
    AirQualityTarget.GOOD: "Good",
    AirQualityTarget.DEFAULT: "Default",
    AirQualityTarget.SENSITIVE: "Sensitive",
    AirQualityTarget.VERY_SENSITIVE: "Very Sensitive",
}

AIR_QUALITY_TARGET_STR_TO_ENUM = {
    value: key for key, value in AIR_QUALITY_TARGET_ENUM_TO_STR.items()
}

# Oscillation range select options
OSCILLATION_RANGE_OPTIONS = ["off", "45", "90", "180", "350", "custom"]

# Mapping for display names
OSCILLATION_RANGE_DISPLAY_NAMES = {
    "off": "Off",
    "45°": "45°",
    "90°": "90°", 
    "180°": "180°",
    "350°": "350°",
    "custom": "Custom"
}

OSCILLATION_MODE_ENUM_TO_STR = {
    HumidifyOscillationMode.DEGREE_45: "45°",
    HumidifyOscillationMode.DEGREE_90: "90°",
    HumidifyOscillationMode.BREEZE: "Breeze",
    HumidifyOscillationMode.CUST: "Custom",
}

OSCILLATION_MODE_STR_TO_ENUM = {
    value: key for key, value in OSCILLATION_MODE_ENUM_TO_STR.items()
}

TILT_ENUM_TO_STR = {
    0: "0°",
    25: "25°",
    50: "50°",
    359: "Breeze",
}

TILT_STR_TO_ENUM = {
    value: key for key, value in TILT_ENUM_TO_STR.items()
}


WATER_HARDNESS_STR_TO_ENUM = {
    "Soft": WaterHardness.SOFT,
    "Medium": WaterHardness.MEDIUM,
    "Hard": WaterHardness.HARD,
}

WATER_HARDNESS_ENUM_TO_STR = {
    value: key for key, value in WATER_HARDNESS_STR_TO_ENUM.items()
}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson sensor from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    entities = []
    if isinstance(device, DysonPureHotCoolLink) or isinstance(
        device, DysonPureCoolLink
    ):
        entities.append(DysonAirQualitySelect(device, name))
    if isinstance(device, DysonPureCool):
        entities.append(DysonOscillationRangeSelect(device, name))
    if isinstance(device, DysonPurifierHumidifyCool):
        entities.extend(
            [
                DysonOscillationModeSelect(device, name),
                DysonWaterHardnessSelect(device, name),
            ]
        )
    if isinstance(device, DysonBigQuiet):
        entities.extend(
            [
                DysonTiltSelect(device, name),
            ]
        )
    async_add_entities(entities)


class DysonAirQualitySelect(DysonEntity, SelectEntity):
    """Air quality target for supported models."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(AIR_QUALITY_TARGET_STR_TO_ENUM.keys())

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return AIR_QUALITY_TARGET_ENUM_TO_STR[self._device.air_quality_target]

    def select_option(self, option: str) -> None:
        """Configure the new selected option."""
        self._device.set_air_quality_target(AIR_QUALITY_TARGET_STR_TO_ENUM[option])

    @property
    def sub_name(self) -> str:
        """Return the name of the select."""
        return "Air Quality"

    @property
    def sub_unique_id(self):
        """Return the select's unique id."""
        return "air_quality"


class DysonOscillationModeSelect(DysonEntity, SelectEntity):
    """Oscillation mode for supported models."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:sync"
    _attr_options = list(OSCILLATION_MODE_STR_TO_ENUM.keys())

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return OSCILLATION_MODE_ENUM_TO_STR[self._device.oscillation_mode]

    def select_option(self, option: str) -> None:
        """Configure the new selected option."""
        self._device.enable_oscillation(OSCILLATION_MODE_STR_TO_ENUM[option])

    @property
    def sub_name(self) -> str:
        """Return the name of the select."""
        return "Oscillation Mode"

    @property
    def sub_unique_id(self):
        """Return the select's unique id."""
        return "oscillation_mode"


class DysonTiltSelect(DysonEntity, SelectEntity):
    """Tilt for supported models."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:acute-angle"
    _attr_options = list(TILT_STR_TO_ENUM.keys())

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return TILT_ENUM_TO_STR[self._device.tilt]

    def select_option(self, option: str) -> None:
        """Configure the new selected option."""
        self._device.set_tilt(TILT_STR_TO_ENUM[option])

    @property
    def sub_name(self) -> str:
        """Return the name of the select."""
        return "Tilt"

    @property
    def sub_unique_id(self):
        """Return the select's unique id."""
        return "tilt"


class DysonWaterHardnessSelect(DysonEntity, SelectEntity):
    """Dyson Pure Humidify+Cool Water Hardness Select."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:water-opacity"
    _attr_options = list(WATER_HARDNESS_STR_TO_ENUM.keys())

    @property
    def current_option(self) -> str:
        """Configure the new selected option."""
        return WATER_HARDNESS_ENUM_TO_STR[self._device.water_hardness]

    def select_option(self, option: str) -> None:
        """Configure the new selected option."""
        self._device.set_water_hardness(WATER_HARDNESS_STR_TO_ENUM[option])

    @property
    def sub_name(self) -> str:
        """Return the name of the select."""
        return "Water Hardness"

    @property
    def sub_unique_id(self):
        """Return the select's unique id."""
        return "water_hardness"


class DysonOscillationRangeSelect(DysonEntity, SelectEntity):
    """Oscillation range select for supported models."""

    _attr_options = OSCILLATION_RANGE_OPTIONS
    
    def __init__(self, device, name: str):
        """Initialize the select entity."""
        super().__init__(device, name)
        # Track user's preferred center point (ignoring 350° range)
        self._user_preferred_center = None

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return self._attr_options

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        if not self._device.oscillation:
            return "off"

        # Calculate the difference between high and low angles
        low_angle = self._device.oscillation_angle_low
        high_angle = self._device.oscillation_angle_high

        # Dyson hardware only supports high >= low (no wrap-around)
        if high_angle < low_angle:
            _LOGGER.warning("Invalid oscillation state: high angle (%d) < low angle (%d)", high_angle, low_angle)
            return "custom"  # Return custom for invalid states
        
        angle_diff = high_angle - low_angle
        current_center = (low_angle + high_angle) / 2

        # Track user's preferred center for non-350° ranges
        if angle_diff != 350:
            self._user_preferred_center = current_center

        # Map angle differences to preset options
        if angle_diff == 45:
            return "45"
        elif angle_diff == 90:
            return "90"
        elif angle_diff == 180:
            return "180"
        elif angle_diff == 350:
            return "350"
        else:
            return "custom"

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        if option == "off":
            # Turn off oscillation
            await self.hass.async_add_executor_job(self._device.disable_oscillation)
        else:
            # Turn on oscillation with the selected range
            # For 350, always use full range. For others, preserve user's preferred center
            if option == "350":
                # 350 is special - always use the full available range
                new_low = 5
                new_high = 355
                await self.hass.async_add_executor_job(
                    self._device.enable_oscillation, new_low, new_high
                )
                _LOGGER.debug("Set oscillation to maximum range: %d° to %d° (350° range)", new_low, new_high)
                
                return
            
            # For non-350° ranges, use preferred center or current center
            if self._user_preferred_center is not None:
                # Use the user's preferred center from previous non-350° selections
                target_center = self._user_preferred_center
                _LOGGER.debug("Using stored preferred center: %.1f°", target_center)
            elif self._device.oscillation and hasattr(self._device, 'oscillation_angle_low') and hasattr(self._device, 'oscillation_angle_high'):
                # Calculate current center point
                current_low = self._device.oscillation_angle_low
                current_high = self._device.oscillation_angle_high
                if current_high >= current_low:
                    target_center = (current_low + current_high) / 2
                    # Store this as preferred center if it's not from a 350° range
                    current_range = current_high - current_low
                    if current_range != 350:
                        self._user_preferred_center = target_center
                else:
                    # Invalid state, use default center
                    target_center = 180
            else:
                # No current oscillation, use default center (front)
                target_center = 180
                self._user_preferred_center = target_center
            
            # Calculate new low and high angles based on desired range and current center
            if option == "45":
                range_degrees = 45
            elif option == "90":
                range_degrees = 90
            elif option == "180":
                range_degrees = 180
            elif option == "350":
                # 350 is special - always use the full available range
                # This gives the maximum possible oscillation range
                new_low = 5
                new_high = 355
                await self.hass.async_add_executor_job(
                    self._device.enable_oscillation, new_low, new_high
                )
                _LOGGER.debug("Set oscillation to maximum range: %d° to %d° (350° range)", new_low, new_high)
                
                return
            elif option == "custom":
                # Don't change angles for custom - user should use number entities
                return
            else:
                return

            # Calculate new angles centered around target center
            half_range = range_degrees / 2
            new_low_raw = target_center - half_range
            new_high_raw = target_center + half_range
            
            # Apply constraints to keep angles within 5-355 degrees
            new_low = max(5, min(355, int(new_low_raw)))
            new_high = max(5, min(355, int(new_high_raw)))
            
            # Ensure high >= low (no wrap-around allowed)
            if new_high < new_low:
                _LOGGER.warning("Cannot set range - would result in invalid oscillation range (high < low)")
                # Fall back to default center if target center causes issues
                fallback_center = 180
                new_low_raw = fallback_center - half_range
                new_high_raw = fallback_center + half_range
                new_low = max(5, min(355, int(new_low_raw)))
                new_high = max(5, min(355, int(new_high_raw)))
                
                if new_high < new_low:
                    _LOGGER.error("Cannot set range - even with fallback center")
                    return
                else:
                    # Update preferred center to the fallback that worked
                    self._user_preferred_center = fallback_center
            
            # Validate that the resulting range is acceptable
            calculated_range = new_high - new_low
            if calculated_range < range_degrees - 10:  # Allow some tolerance for constraints
                _LOGGER.warning(
                    "Range adjustment limited by angle constraints (requested %d°, got %d°)",
                    range_degrees, calculated_range
                )
            
            await self.hass.async_add_executor_job(
                self._device.enable_oscillation, new_low, new_high
            )
            _LOGGER.debug("Set oscillation range to %d° centered at %.1f° (range: %d° to %d°)", 
                         range_degrees, target_center, new_low, new_high)

    @property
    def sub_name(self) -> str:
        """Return the name of the select."""
        return "Oscillation Range"

    @property
    def sub_unique_id(self):
        """Return the select's unique id."""
        return "oscillation_range"

    @property
    def translation_key(self) -> str:
        """Return the translation key for this entity."""
        return "oscillation_range"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and hasattr(self._device, 'oscillation_angle_low')

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:rotate-orbit"
