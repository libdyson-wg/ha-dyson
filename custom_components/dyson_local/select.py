"""Select platform for dyson."""

from typing import Callable

from .vendor.libdyson import (
    DysonPureCoolLink,
    DysonPureHotCoolLink,
    DysonPurifierHumidifyCool,
    HumidifyOscillationMode,
    WaterHardness,
)
from .vendor.libdyson.const import AirQualityTarget

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DysonEntity
from .const import DATA_DEVICES, DOMAIN

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

OSCILLATION_MODE_ENUM_TO_STR = {
    HumidifyOscillationMode.DEGREE_45: "45°",
    HumidifyOscillationMode.DEGREE_90: "90°",
    HumidifyOscillationMode.BREEZE: "Breeze",
}

OSCILLATION_MODE_STR_TO_ENUM = {
    value: key for key, value in OSCILLATION_MODE_ENUM_TO_STR.items()
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
    if isinstance(device, DysonPurifierHumidifyCool):
        entities.extend(
            [
                DysonOscillationModeSelect(device, name),
                DysonWaterHardnessSelect(device, name),
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
