"""Number platform for Dyson devices."""

import logging
import time
from typing import Optional

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DysonEntity
from .const import DATA_DEVICES, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Track when status was last requested for each device to avoid duplicate requests
_last_status_request = {}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dyson number entities from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][entry.entry_id]
    name = entry.data[CONF_NAME]
    
    _LOGGER.debug("Setting up number entities for device %s", device.serial)
    
    entities = []
    
    # Only add oscillation angle controls for devices that support oscillation with angle control
    if hasattr(device, 'oscillation_angle_low') and hasattr(device, 'oscillation_angle_high') and hasattr(device, 'enable_oscillation'):
        _LOGGER.debug("Device %s supports oscillation with angle control, adding number entities", device.serial)
        entities.extend([
            DysonOscillationLowAngleNumber(device, name),
            DysonOscillationHighAngleNumber(device, name),
            DysonOscillationCenterAngleNumber(device, name),
        ])
    else:
        _LOGGER.warning("Device %s does not support oscillation with angle control, skipping number entities", device.serial)
        _LOGGER.debug("Device attributes: oscillation_angle_low=%s, oscillation_angle_high=%s, enable_oscillation=%s", 
                    hasattr(device, 'oscillation_angle_low'), 
                    hasattr(device, 'oscillation_angle_high'), 
                    hasattr(device, 'enable_oscillation'))
    
    if entities:
        _LOGGER.debug("Adding %d number entities for device %s", len(entities), device.serial)
        async_add_entities(entities)
    else:
        _LOGGER.warning("No number entities to add for device %s", device.serial)


class DysonOscillationLowAngleNumber(DysonEntity, NumberEntity):
    """Dyson oscillation low angle number entity."""

    def __init__(self, device, name: str):
        """Initialize the number entity."""
        super().__init__(device, name)

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        # Don't request status on entity add to avoid interference with normal data flow
        # The entity will get updated through the normal message listening mechanism

    @property
    def sub_name(self) -> str:
        """Return the name of the entity."""
        return "Oscillation Low Angle"

    @property
    def sub_unique_id(self) -> str:
        """Return the unique id of the entity."""
        return "oscillation_low_angle"

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:rotate-left"

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return 5

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return 355

    @property
    def native_step(self) -> float:
        """Return the step size."""
        return 5

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "°"

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        if hasattr(self._device, 'oscillation_angle_low'):
            return float(self._device.oscillation_angle_low)
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the oscillation low angle."""
        try:
            low_angle = int(value)
            high_angle = self._device.oscillation_angle_high
            
            # Validate according to Dyson device constraints
            if not 5 <= low_angle <= 355:
                _LOGGER.warning("Low angle must be between 5 and 355 degrees")
                return
                
            # Ensure low angle is less than high angle OR equal (for fixed position)
            # and if different, high must be at least 30 degrees larger
            if low_angle != high_angle and low_angle + 30 > high_angle:
                _LOGGER.warning(
                    "High angle (%d) must be either equal to low angle (%d) or at least 30 degrees larger", 
                    high_angle, low_angle
                )
                return
            
            await self.hass.async_add_executor_job(
                self._device.enable_oscillation, low_angle, high_angle
            )
            _LOGGER.debug("Set oscillation low angle to %d°", low_angle)
        except Exception as e:
            _LOGGER.error("Failed to set oscillation low angle: %s", e)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and hasattr(self._device, 'oscillation_angle_low')


class DysonOscillationHighAngleNumber(DysonEntity, NumberEntity):
    """Dyson oscillation high angle number entity."""

    def __init__(self, device, name: str):
        """Initialize the number entity."""
        super().__init__(device, name)

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        # Don't request status on entity add to avoid interference with normal data flow
        # The entity will get updated through the normal message listening mechanism

    @property
    def sub_name(self) -> str:
        """Return the name of the entity."""
        return "Oscillation High Angle"

    @property
    def sub_unique_id(self) -> str:
        """Return the unique id of the entity."""
        return "oscillation_high_angle"

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:rotate-right"

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return 5

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return 355

    @property
    def native_step(self) -> float:
        """Return the step size."""
        return 5

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "°"

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        if hasattr(self._device, 'oscillation_angle_high'):
            return float(self._device.oscillation_angle_high)
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the oscillation high angle."""
        try:
            high_angle = int(value)
            low_angle = self._device.oscillation_angle_low
            
            # Validate according to Dyson device constraints
            if not 5 <= high_angle <= 355:
                _LOGGER.warning("High angle must be between 5 and 355 degrees")
                return
                
            # Ensure high angle is greater than low angle OR equal (for fixed position)
            # and if different, high must be at least 30 degrees larger than low
            if high_angle != low_angle and low_angle + 30 > high_angle:
                _LOGGER.warning(
                    "High angle (%d) must be either equal to low angle (%d) or at least 30 degrees larger", 
                    high_angle, low_angle
                )
                return
            
            await self.hass.async_add_executor_job(
                self._device.enable_oscillation, low_angle, high_angle
            )
            _LOGGER.debug("Set oscillation high angle to %d°", high_angle)
        except Exception as e:
            _LOGGER.error("Failed to set oscillation high angle: %s", e)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and hasattr(self._device, 'oscillation_angle_high')


class DysonOscillationCenterAngleNumber(DysonEntity, NumberEntity):
    """Dyson oscillation center angle number entity."""

    def __init__(self, device, name: str):
        """Initialize the number entity."""
        super().__init__(device, name)
        _LOGGER.debug("DysonOscillationCenterAngleNumber entity created for device %s", device.serial)

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        # Don't request status on entity add to avoid interference with normal data flow
        # The entity will get updated through the normal message listening mechanism

    @property
    def sub_name(self) -> str:
        """Return the name of the entity."""
        return "Oscillation Center Angle"

    @property
    def sub_unique_id(self) -> str:
        """Return the unique id of the entity."""
        return "oscillation_center_angle"

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:crosshairs"

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return 5

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return 355

    @property
    def native_step(self) -> float:
        """Return the step size."""
        return 5

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "°"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        entity_name = super().name
        _LOGGER.debug("CENTER ANGLE ENTITY NAME ACCESSED: %s", entity_name)
        return entity_name

    @property
    def native_value(self) -> Optional[float]:
        """Return the current center angle value."""
        if hasattr(self._device, 'oscillation_angle_low') and hasattr(self._device, 'oscillation_angle_high'):
            low_angle = self._device.oscillation_angle_low
            high_angle = self._device.oscillation_angle_high
            
            # Calculate center point - Dyson hardware only supports high > low (no wrap-around)
            center = (low_angle + high_angle) / 2
            
            _LOGGER.debug("native_value accessed for center angle: low=%s, high=%s, center=%s", low_angle, high_angle, center)
            return float(center)
        _LOGGER.debug("native_value accessed but device lacks oscillation angle attributes")
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the oscillation center angle."""
        _LOGGER.debug("async_set_native_value ENTRY: Setting oscillation center angle to %f for device %s", value, self._device.serial)
        try:
            new_center = int(value)
            
            # Validate center angle
            if not 5 <= new_center <= 355:
                _LOGGER.warning("Center angle must be between 5 and 355 degrees")
                return
            
            # Get current range (difference between high and low)
            current_low = self._device.oscillation_angle_low
            current_high = self._device.oscillation_angle_high
            
            # Calculate current range - Dyson hardware only supports high >= low
            if current_high < current_low:
                _LOGGER.warning("Invalid current oscillation state: high angle (%d) < low angle (%d)", current_high, current_low)
                return
            
            current_range = current_high - current_low
            
            # Calculate new low and high angles based on new center
            half_range = current_range / 2
            new_low_raw = new_center - half_range
            new_high_raw = new_center + half_range
            
            # Apply constraints to keep angles within 5-355 degrees
            new_low = max(5, min(355, int(new_low_raw)))
            new_high = max(5, min(355, int(new_high_raw)))
            
            # Ensure high >= low (no wrap-around allowed)
            if new_high < new_low:
                _LOGGER.warning("Cannot set center - would result in invalid oscillation range (high < low)")
                return
            
            # Validate that the resulting range is acceptable
            calculated_range = new_high - new_low
            
            # Ensure minimum 30-degree range unless it's a fixed position (same angle)
            if calculated_range > 0 and calculated_range < 30:
                _LOGGER.warning(
                    "Cannot set center - resulting oscillation range (%d°) would be less than minimum 30 degrees", 
                    calculated_range
                )
                return
            
            # Check if the range changed too much due to constraints
            range_change = abs(calculated_range - current_range)
            if range_change > 10:
                _LOGGER.warning(
                    "Center adjustment limited by angle constraints (range changed from %d° to %d°)",
                    current_range, calculated_range
                )
            
            await self.hass.async_add_executor_job(
                self._device.enable_oscillation, new_low, new_high
            )
            _LOGGER.debug("Set oscillation center to %d° (range: %d° to %d°)", new_center, new_low, new_high)
        except Exception as e:
            _LOGGER.error("Failed to set oscillation center angle: %s", e)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        is_available = super().available and hasattr(self._device, 'oscillation_angle_low')
        _LOGGER.debug("available property for center angle entity: %s (super().available=%s, has_attr=%s)", 
                    is_available, super().available, hasattr(self._device, 'oscillation_angle_low'))
        return is_available
