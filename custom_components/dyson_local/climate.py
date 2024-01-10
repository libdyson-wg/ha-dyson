"""Dyson climate platform."""

import logging
from typing import List, Optional

from .const import DATA_DEVICES, DOMAIN
from .utils import environmental_property
from .vendor.libdyson import DysonPureHotCoolLink

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACAction,
    FAN_DIFFUSE,
    FAN_FOCUS,
    HVACMode,
    ClimateEntityFeature
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_NAME, UnitOfTemperature
from homeassistant.core import Callable, HomeAssistant

from . import DysonEntity

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
FAN_MODES = [FAN_FOCUS, FAN_DIFFUSE]
SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE
SUPPORT_FLAGS_LINK = SUPPORT_FLAGS | ClimateEntityFeature.FAN_MODE


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson climate from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    if isinstance(device, DysonPureHotCoolLink):
        entity = DysonPureHotCoolLinkEntity(device, name)
    else:  # DysonPureHotCool
        entity = DysonPureHotCoolEntity(device, name)
    async_add_entities([entity])


class DysonClimateEntity(DysonEntity, ClimateEntity):
    """Dyson climate entity base class."""

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation."""
        if not self._device.is_on:
            return HVACMode.OFF
        if self._device.heat_mode_is_on:
            return HVACMode.HEAT
        return HVACMode.COOL

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return HVAC_MODES

    @property
    def hvac_action(self) -> str:
        """Return the current running hvac operation."""
        if not self._device.is_on:
            return HVACAction.OFF
        if self._device.heat_mode_is_on:
            if self._device.heat_status_is_on:
                return HVACAction.HEATING
            return HVACAction.IDLE
        return HVACAction.COOLING

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature(self) -> int:
        """Return the target temperature."""
        return self._device.heat_target - 273

    @environmental_property
    def _current_temperature_kelvin(self) -> int:
        """Return the current temperature in kelvin."""
        return self._device.temperature

    @property
    def current_temperature(self) -> Optional[int]:
        """Return the current temperature."""
        temperature_kelvin = self._current_temperature_kelvin
        if isinstance(temperature_kelvin, str):
            return None
        return float(f"{(temperature_kelvin - 273.15):.1f}")

    @environmental_property
    def current_humidity(self) -> int:
        """Return the current humidity."""
        return self._device.humidity

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 1

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 37

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        # Check if a temperature was sent
        if target_temp is None:
            _LOGGER.error("Missing target temperature %s", kwargs)
            return
        # Limit the target temperature into acceptable range
        if target_temp < self.min_temp or target_temp > self.max_temp:
            _LOGGER.warning('Temperature requested is outside min/max range, adjusting')
            target_temp = min(self.max_temp, target_temp)
            target_temp = max(self.min_temp, target_temp)
        _LOGGER.debug("Set %s temperature %s", self.name, target_temp)
        self._device.set_heat_target(target_temp + 273)

    def set_hvac_mode(self, hvac_mode: str):
        """Set new hvac mode."""
        _LOGGER.debug("Set %s heat mode %s", self.name, hvac_mode)
        if hvac_mode == HVACMode.OFF:
            self._device.turn_off()
        elif not self._device.is_on:
            self._device.turn_on()
        if hvac_mode == HVACMode.HEAT:
            self._device.enable_heat_mode()
        elif hvac_mode == HVACMode.COOL:
            self._device.disable_heat_mode()


class DysonPureHotCoolLinkEntity(DysonClimateEntity):
    """Dyson Pure Hot+Cool Link entity."""

    @property
    def fan_mode(self) -> str:
        """Return the fan setting."""
        if self._device.focus_mode:
            return FAN_FOCUS
        return FAN_DIFFUSE

    @property
    def fan_modes(self) -> List[str]:
        """Return the list of available fan modes."""
        return FAN_MODES

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FLAGS_LINK

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode of the device."""
        _LOGGER.debug("Set %s focus mode %s", self.name, fan_mode)
        if fan_mode == FAN_FOCUS:
            self._device.enable_focus_mode()
        elif fan_mode == FAN_DIFFUSE:
            self._device.disable_focus_mode()


class DysonPureHotCoolEntity(DysonClimateEntity):
    """Dyson Pure Hot+Cool entity."""
