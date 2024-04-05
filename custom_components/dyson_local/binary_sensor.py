"""Binary sensor platform for dyson."""

from typing import Callable

from .vendor.libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    Dyson360VisNav,
    DysonPureHotCoolLink,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DysonEntity
from .const import DATA_DEVICES, DOMAIN

ICON_BIN_FULL = "mdi:delete-variant"


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson binary sensor from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    entities = []
    if isinstance(device, Dyson360Eye):
        entities.append(DysonVacuumBatteryChargingSensor(device, name))
    if isinstance(device, Dyson360Heurist):
        entities.extend(
            [
                DysonVacuumBatteryChargingSensor(device, name),
                Dyson360VisNavBinFullSensor(device, name),
            ]
        )
    if isinstance(device, Dyson360VisNav):
        entities.extend(
            [
                DysonVacuumBatteryChargingSensor(device, name),
                Dyson360HeuristBinFullSensor(device, name),
            ]
        )
    if isinstance(device, DysonPureHotCoolLink):
        entities.extend([DysonPureHotCoolLinkTiltSensor(device, name)])
    async_add_entities(entities)


class DysonVacuumBatteryChargingSensor(DysonEntity, BinarySensorEntity):
    """Dyson vacuum battery charging sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.is_charging

    @property
    def device_class(self) -> str:
        """Return the device class of the sensor."""
        return BinarySensorDeviceClass.BATTERY_CHARGING

    @property
    def sub_name(self) -> str:
        """Return the name of the sensor."""
        return "Battery Charging"

    @property
    def sub_unique_id(self):
        """Return the sensor's unique id."""
        return "battery_charging"


class Dyson360HeuristBinFullSensor(DysonEntity, BinarySensorEntity):
    """Dyson 360 Heurist bin full sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.is_bin_full

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return ICON_BIN_FULL

    @property
    def sub_name(self) -> str:
        """Return the name of the sensor."""
        return "Bin Full"

    @property
    def sub_unique_id(self):
        """Return the sensor's unique id."""
        return "bin_full"


class Dyson360VisNavBinFullSensor(DysonEntity, BinarySensorEntity):
    """Dyson 360 VisNav bin full sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.is_bin_full

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return ICON_BIN_FULL

    @property
    def sub_name(self) -> str:
        """Return the name of the sensor."""
        return "Bin Full"

    @property
    def sub_unique_id(self):
        """Return the sensor's unique id."""
        return "bin_full"


class DysonPureHotCoolLinkTiltSensor(DysonEntity, BinarySensorEntity):
    """Dyson Pure Hot+Cool Link tilt sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:angle-acute"

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.tilt

    @property
    def sub_name(self) -> str:
        """Return the name of the sensor."""
        return "Tilt"

    @property
    def sub_unique_id(self):
        """Return the sensor's unique id."""
        return "tilt"
