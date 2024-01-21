"""Humidifier platform for Dyson."""

from typing import Callable, Optional

from .vendor.libdyson import MessageType

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntityFeature,
    HumidifierEntity,
)
from homeassistant.components.humidifier.const import MODE_AUTO, MODE_NORMAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from . import DysonEntity
from .const import DATA_DEVICES, DOMAIN

AVAILABLE_MODES = [MODE_NORMAL, MODE_AUTO]

SUPPORTED_FEATURES = HumidifierEntityFeature.MODES


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson humidifier from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    async_add_entities([DysonHumidifierEntity(device, name)])


class DysonHumidifierEntity(DysonEntity, HumidifierEntity):
    """Dyson humidifier entity."""

    _MESSAGE_TYPE = MessageType.STATE

    _attr_device_class = HumidifierDeviceClass.HUMIDIFIER
    _attr_available_modes = AVAILABLE_MODES
    _attr_max_humidity = 70
    _attr_min_humidity = 30
    _attr_supported_features = HumidifierEntityFeature.MODES

    @property
    def is_on(self) -> bool:
        """Return if humidification is on."""
        return self._device.humidification

    @property
    def target_humidity(self) -> Optional[int]:
        """Return the target."""
        if self._device.humidification_auto_mode:
            return None

        return self._device.target_humidity

    @property
    def mode(self) -> str:
        """Return current mode."""
        return MODE_AUTO if self._device.humidification_auto_mode else MODE_NORMAL

    def turn_on(self, **kwargs) -> None:
        """Turn on humidification."""
        self._device.enable_humidification()

    def turn_off(self, **kwargs) -> None:
        """Turn off humidification."""
        self._device.disable_humidification()

    def set_humidity(self, humidity: int) -> None:
        """Set target humidity."""
        self._device.set_target_humidity(humidity)
        self.set_mode(MODE_NORMAL)

    def set_mode(self, mode: str) -> None:
        """Set humidification mode."""
        if mode == MODE_AUTO:
            self._device.enable_humidification_auto_mode()
        elif mode == MODE_NORMAL:
            self._device.disable_humidification_auto_mode()
        else:
            raise ValueError(f"Invalid mode: {mode}")
