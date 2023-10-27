"""Support for Dyson devices."""

import asyncio
from datetime import timedelta
from functools import partial
import logging
from typing import List, Optional

from .vendor.libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    DysonPureHotCool,
    DysonPureHotCoolLink,
    DysonPurifierHumidifyCool,
    MessageType,
    get_device,
)
from .vendor.libdyson.cloud import (
    DysonAccountCN,
    DysonAccount,
)
from .vendor.libdyson.discovery import DysonDiscovery
from .vendor.libdyson.dyson_device import DysonDevice
from .vendor.libdyson.exceptions import (
    DysonException,
    DysonNetworkError,
    DysonLoginFailure,
)

from homeassistant.components.zeroconf import async_get_instance
from homeassistant.config_entries import ConfigEntry, SOURCE_DISCOVERY
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CREDENTIAL,
    CONF_DEVICE_TYPE,
    CONF_SERIAL,
    DATA_COORDINATORS,
    DATA_DEVICES,
    DATA_DISCOVERY,
    DOMAIN,
)

from .cloud.const import (
    CONF_REGION,
    CONF_AUTH,
    DATA_ACCOUNT,
    DATA_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

ENVIRONMENTAL_DATA_UPDATE_INTERVAL = timedelta(seconds=30)

PLATFORMS = ["camera"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Dyson integration."""
    hass.data[DOMAIN] = {
        DATA_DEVICES: {},
        DATA_COORDINATORS: {},
        DATA_DISCOVERY: None,
    }
    return True


async def async_setup_account(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a MyDyson Account."""
    if entry.data[CONF_REGION] == "CN":
        account = DysonAccountCN(entry.data[CONF_AUTH])
    else:
        account = DysonAccount(entry.data[CONF_AUTH])
    try:
        devices = await hass.async_add_executor_job(account.devices)
    except DysonNetworkError:
        _LOGGER.error("Cannot connect to Dyson cloud service.")
        raise ConfigEntryNotReady

    for device in devices:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_DISCOVERY},
                data=device,
            )
        )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ACCOUNT: account,
        DATA_DEVICES: devices,
    }
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dyson from a config entry."""
    if CONF_REGION in entry.data:
        return await async_setup_account(hass, entry)

    device = get_device(
        entry.data[CONF_SERIAL],
        entry.data[CONF_CREDENTIAL],
        entry.data[CONF_DEVICE_TYPE],
    )

    if not isinstance(device, Dyson360Eye) and not isinstance(device, Dyson360Heurist):
        # Set up coordinator
        async def async_update_data():
            """Poll environmental data from the device."""
            try:
                await hass.async_add_executor_job(device.request_environmental_data)
            except DysonException as err:
                raise UpdateFailed("Failed to request environmental data") from err

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="environmental",
            update_method=async_update_data,
            update_interval=ENVIRONMENTAL_DATA_UPDATE_INTERVAL,
        )
    else:
        coordinator = None

    async def _async_forward_entry_setup():
        for component in _async_get_platforms(device):
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
            )

    def setup_entry(host: str, is_discovery: bool = True) -> bool:
        try:
            device.connect(host)
        except DysonException:
            if is_discovery:
                _LOGGER.error(
                    "Failed to connect to device %s at %s",
                    device.serial,
                    host,
                )
                return
            raise ConfigEntryNotReady
        hass.data[DOMAIN][DATA_DEVICES][entry.entry_id] = device
        hass.data[DOMAIN][DATA_COORDINATORS][entry.entry_id] = coordinator
        asyncio.run_coroutine_threadsafe(
            _async_forward_entry_setup(), hass.loop
        ).result()

    host = entry.data.get(CONF_HOST)
    if host:
        await hass.async_add_executor_job(
            partial(setup_entry, host, is_discovery=False)
        )
    else:
        discovery = hass.data[DOMAIN][DATA_DISCOVERY]
        if discovery is None:
            discovery = DysonDiscovery()
            hass.data[DOMAIN][DATA_DISCOVERY] = discovery
            _LOGGER.debug("Starting dyson discovery")
            discovery.start_discovery(await async_get_instance(hass))

            def stop_discovery(_):
                _LOGGER.debug("Stopping dyson discovery")
                discovery.stop_discovery()

            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_discovery)

        await hass.async_add_executor_job(
            discovery.register_device, device, setup_entry
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Dyson local."""
    device = hass.data[DOMAIN][DATA_DEVICES][entry.entry_id]
    ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in _async_get_platforms(device)
            ]
        )
    )
    if ok:
        hass.data[DOMAIN][DATA_DEVICES].pop(entry.entry_id)
        hass.data[DOMAIN][DATA_COORDINATORS].pop(entry.entry_id)
        await hass.async_add_executor_job(device.disconnect)
        # TODO: stop discovery
    return ok


@callback
def _async_get_platforms(device: DysonDevice) -> List[str]:
    if isinstance(device, Dyson360Eye) or isinstance(device, Dyson360Heurist):
        return ["binary_sensor", "sensor", "vacuum"]
    platforms = ["fan", "select", "sensor", "switch"]
    if isinstance(device, DysonPureHotCool):
        platforms.append("climate")
    if isinstance(device, DysonPureHotCoolLink):
        platforms.extend(["binary_sensor", "climate"])
    if isinstance(device, DysonPurifierHumidifyCool):
        platforms.append("humidifier")
    if hasattr(device, "filter_life") or hasattr(device, "carbon_filter_life") or hasattr(device, "hepa_filter_life"):
        platforms.append("button")
    return platforms


class DysonEntity(Entity):
    """Dyson entity base class."""

    _MESSAGE_TYPE = MessageType.STATE

    def __init__(self, device: DysonDevice, name: str):
        """Initialize the entity."""
        self._device = device
        self._name = name

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        self._device.add_message_listener(self._on_message)

    def _on_message(self, message_type: MessageType) -> None:
        if self._MESSAGE_TYPE is None or message_type == self._MESSAGE_TYPE:
            self.schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        if self.sub_name is None:
            return self._name
        return f"{self._name} {self.sub_name}"

    @property
    def sub_name(self) -> Optional[str]:
        """Return sub name of the entity."""
        return None

    @property
    def unique_id(self) -> str:
        """Return the entity unique id."""
        if self.sub_unique_id is None:
            return self._device.serial
        return f"{self._device.serial}-{self.sub_unique_id}"

    @property
    def sub_unique_id(self) -> str:
        """Return the entity sub unique id."""
        return None

    @property
    def device_info(self) -> dict:
        """Return device info of the entity."""
        return {
            "identifiers": {(DOMAIN, self._device.serial)},
            "name": self._name,
            "manufacturer": "Dyson",
            "model": self._device.device_type,
        }
