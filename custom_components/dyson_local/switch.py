"""Switch platform for dyson."""

from typing import Callable

from libdyson import DysonPureHotCoolLink

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DysonEntity
from .const import DATA_DEVICES, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson switch from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    entities = [
        DysonNightModeSwitchEntity(device, name),
        DysonContinuousMonitoringSwitchEntity(device, name),
    ]
    if isinstance(device, DysonPureHotCoolLink):
        entities.append(DysonFocusModeSwitchEntity(device, name))
    async_add_entities(entities)


class DysonNightModeSwitchEntity(DysonEntity, SwitchEntity):
    """Dyson fan night mode switch."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def sub_name(self):
        """Return the name of the entity."""
        return "Night Mode"

    @property
    def sub_unique_id(self):
        """Return the unique id of the entity."""
        return "night_mode"

    @property
    def icon(self):
        """Return the icon of the entity."""
        return "mdi:power-sleep"

    @property
    def is_on(self):
        """Return if night mode is on."""
        return self._device.night_mode

    def turn_on(self):
        """Turn on night mode."""
        return self._device.enable_night_mode()

    def turn_off(self):
        """Turn off night mode."""
        return self._device.disable_night_mode()


class DysonContinuousMonitoringSwitchEntity(DysonEntity, SwitchEntity):
    """Dyson fan continuous monitoring."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def sub_name(self):
        """Return the name of the entity."""
        return "Continuous Monitoring"

    @property
    def sub_unique_id(self):
        """Return the unique id of the entity."""
        return "continuous_monitoring"

    @property
    def icon(self):
        """Return the icon of the entity."""
        return "mdi:eye" if self.is_on else "mdi:eye-off"

    @property
    def is_on(self):
        """Return if continuous monitoring is on."""
        return self._device.continuous_monitoring

    def turn_on(self):
        """Turn on continuous monitoring."""
        return self._device.enable_continuous_monitoring()

    def turn_off(self):
        """Turn off continuous monitoring."""
        return self._device.disable_continuous_monitoring()


class DysonFocusModeSwitchEntity(DysonEntity, SwitchEntity):
    """Dyson Pure Hot+Cool Link focus mode switch."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:image-filter-center-focus"

    @property
    def sub_name(self):
        """Return the name of the entity."""
        return "Focus Mode"

    @property
    def sub_unique_id(self):
        """Return the unique id of the entity."""
        return "focus_mode"

    @property
    def is_on(self):
        """Return if switch is on."""
        return self._device.focus_mode

    def turn_on(self):
        """Turn on switch."""
        return self._device.enable_focus_mode()

    def turn_off(self):
        """Turn off switch."""
        return self._device.disable_focus_mode()
