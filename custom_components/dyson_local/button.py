
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass

from typing import Callable, Optional

from .const import DATA_COORDINATORS, DATA_DEVICES, DOMAIN

from . import DysonEntity, DysonDevice

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson button from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]


    entities = []

    if hasattr(device, "filter_life"):
        entities.append(DysonFilterResetButton(device, name))

    async_add_entities(entities)


class DysonFilterResetButton(DysonEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def sub_name(self) -> Optional[str]:
        """Return the name of the Dyson button."""
        return "Reset Filter Life"

    @property
    def sub_unique_id(self) -> str:
        """Return the button's unique id."""
        return "reset-filter"

    def press(self) -> None:
        self._device.reset_filter()
