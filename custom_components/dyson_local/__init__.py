"""Support for Dyson devices."""

import asyncio
from datetime import timedelta
from functools import partial
import logging
from typing import List, Optional

from homeassistant.components.zeroconf import async_get_instance
from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud.const import CONF_AUTH, CONF_REGION, DATA_ACCOUNT, DATA_DEVICES
from .const import (
    CONF_CREDENTIAL,
    CONF_DEVICE_TYPE,
    CONF_SERIAL,
    DATA_COORDINATORS,
    DATA_DEVICES,
    DATA_DISCOVERY,
    DOMAIN,
)
from libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    Dyson360VisNav,
    DysonPureHotCool,
    DysonPureHotCoolLink,
    DysonPurifierHumidifyCool,
    MessageType,
    get_device,
)
from libdyson.cloud import DysonAccount, DysonAccountCN
from libdyson.discovery import DysonDiscovery
from libdyson.dyson_device import DysonDevice
from libdyson.exceptions import (
    DysonException,
    DysonInvalidAuth,
    DysonLoginFailure,
    DysonNetworkError,
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
        "discovery_count": 0,  # Track how many entries use discovery
        "device_ips": {},  # Cache of device serial -> IP mappings
    }
    return True


async def async_setup_account(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a MyDyson Account."""
    _LOGGER.debug("Setting up MyDyson Account for region: %s", entry.data[CONF_REGION])

    if entry.data[CONF_REGION] == "CN":
        account = DysonAccountCN(entry.data[CONF_AUTH])
    else:
        account = DysonAccount(entry.data[CONF_AUTH])
    try:
        _LOGGER.debug("Calling account.devices() to get device list")
        devices = await hass.async_add_executor_job(account.devices)
        _LOGGER.debug("Retrieved %d devices from cloud", len(devices))
    except DysonNetworkError:
        _LOGGER.error("Cannot connect to Dyson cloud service.")
        raise ConfigEntryNotReady
    except DysonInvalidAuth:
        _LOGGER.error("Invalid authentication credentials for Dyson cloud service.")
        raise ConfigEntryNotReady
    except Exception as e:
        _LOGGER.error("Unexpected error retrieving devices: %s", str(e))
        raise ConfigEntryNotReady

    _LOGGER.debug("Starting device discovery flows for %d devices", len(devices))
    for device in devices:
        _LOGGER.debug("Creating discovery flow for device: %s (ProductType: %s)",
                      device.name, device.product_type)
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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dyson from a config entry."""
    _LOGGER.debug("Setting up entry: %s", entry.entry_id)
    
    if CONF_REGION in entry.data:
        return await async_setup_account(hass, entry)

    device = get_device(
        entry.data[CONF_SERIAL],
        entry.data[CONF_CREDENTIAL],
        entry.data[CONF_DEVICE_TYPE],
    )
    
    # Ensure device is disconnected before attempting to connect
    # This is important for reload scenarios
    try:
        await hass.async_add_executor_job(device.disconnect)
        _LOGGER.debug("Disconnected device %s before setup", device.serial)
        # Give a moment for the disconnection to complete
        await asyncio.sleep(0.2)
    except Exception as e:
        # Device might not have been connected, which is fine
        _LOGGER.debug("Device %s was not connected during setup (expected): %s", device.serial, e)

    if (not isinstance(device, Dyson360Eye)
            and not isinstance(device, Dyson360Heurist)
            and not isinstance(device, Dyson360VisNav)):
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
            name=f"environmental_{device.serial}",
            update_method=async_update_data,
            update_interval=ENVIRONMENTAL_DATA_UPDATE_INTERVAL,
            config_entry=entry,
        )
        _LOGGER.debug("Created coordinator for device %s", device.serial)
    else:
        coordinator = None
        _LOGGER.debug("No coordinator needed for vacuum device %s", device.serial)

    def setup_entry(host: str, is_discovery: bool = True) -> bool:
        _LOGGER.debug("setup_entry called for device %s at %s (discovery: %s)", device.serial, host, is_discovery)
        
        # Check if device is already connected and disconnect if necessary
        try:
            if hasattr(device, 'is_connected') and device.is_connected:
                _LOGGER.debug("Device %s already connected, disconnecting first", device.serial)
                device.disconnect()
        except Exception as e:
            _LOGGER.debug("Error checking/disconnecting device %s: %s", device.serial, e)
        
        try:
            device.connect(host)
            _LOGGER.debug("Successfully connected to device %s at %s", device.serial, host)
            
            # Cache the IP address for this device for future use
            if is_discovery and host:
                if "device_ips" not in hass.data[DOMAIN]:
                    hass.data[DOMAIN]["device_ips"] = {}
                hass.data[DOMAIN]["device_ips"][device.serial] = host
                _LOGGER.debug("Cached IP %s for device %s", host, device.serial)
            
        except DysonException as e:
            if is_discovery:
                _LOGGER.error(
                    "Failed to connect to device %s at %s: %s",
                    device.serial,
                    host,
                    str(e),
                )
                return False
            _LOGGER.error("Failed to connect to device %s at %s during setup: %s", device.serial, host, str(e))
            raise ConfigEntryNotReady from e
        
        # Store device and coordinator data
        hass.data[DOMAIN][DATA_DEVICES][entry.entry_id] = device
        hass.data[DOMAIN][DATA_COORDINATORS][entry.entry_id] = coordinator
        _LOGGER.debug("Stored device %s and coordinator in hass.data", device.serial)
        
        # Set up platforms
        try:
            platforms = _async_get_platforms(device)
            _LOGGER.debug("Setting up platforms for %s: %s", device.serial, platforms)
            asyncio.run_coroutine_threadsafe(
                hass.config_entries.async_forward_entry_setups(entry, platforms), hass.loop
            ).result()
            _LOGGER.debug("Successfully set up platforms for %s", device.serial)
        except Exception as e:
            _LOGGER.error("Failed to set up platforms for %s: %s", device.serial, str(e))
            # Clean up on platform setup failure
            hass.data[DOMAIN][DATA_DEVICES].pop(entry.entry_id, None)
            hass.data[DOMAIN][DATA_COORDINATORS].pop(entry.entry_id, None)
            try:
                device.disconnect()
            except Exception:
                pass
            if not is_discovery:
                raise ConfigEntryNotReady from e
            return False
        
        _LOGGER.debug("setup_entry completed successfully for device %s", device.serial)
        return True

    host = entry.data.get(CONF_HOST)
    if host:
        _LOGGER.debug("Setting up device %s with static host: %s", device.serial, host)
        result = await hass.async_add_executor_job(
            partial(setup_entry, host, is_discovery=False)
        )
        if not result:
            _LOGGER.error("Failed to set up device %s with static host", device.serial)
            raise ConfigEntryNotReady
    else:
        _LOGGER.debug("Setting up device %s with discovery", device.serial)
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
        
        # Always check for and restore preserved discovered devices (for reload scenarios)
        # This should happen whether discovery is new or existing
        preserved_discovered = hass.data[DOMAIN].pop("preserved_discovered", {})
        if preserved_discovered:
            _LOGGER.debug("Restoring preserved discovered devices: %s", list(preserved_discovered.keys()))
            with discovery._lock:
                # Merge preserved devices with any currently discovered devices
                discovery._discovered.update(preserved_discovered)
        else:
            _LOGGER.debug("No preserved discovered devices found to restore")
        
        # Increment discovery usage count
        if "discovery_count" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["discovery_count"] = 0
        hass.data[DOMAIN]["discovery_count"] += 1
        _LOGGER.debug("Discovery count is now: %d", hass.data[DOMAIN]["discovery_count"])

        # Register device with discovery service with enhanced handling
        await _async_register_device_with_discovery(hass, discovery, device, setup_entry, entry)
        _LOGGER.debug("Device %s registration with discovery completed", device.serial)

    _LOGGER.debug("Successfully completed setup for entry: %s", entry.entry_id)
    
    # For discovery-based devices, we might not have immediate connection
    # The device will connect when discovered, so don't fail here
    if entry.data.get(CONF_HOST) and entry.entry_id not in hass.data[DOMAIN][DATA_DEVICES]:
        # Only fail for static host devices that should have connected immediately
        _LOGGER.error("Device setup verification failed - device %s not found in data after setup", device.serial)
        raise ConfigEntryNotReady
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Dyson local."""
    _LOGGER.debug("Unloading entry: %s", entry.entry_id)
    
    # Ensure domain data exists
    if DOMAIN not in hass.data:
        _LOGGER.warning("Domain data not found during unload - integration may have already been removed")
        return True
    
    # Handle cloud account entries (MyDyson accounts)
    if CONF_REGION in entry.data:
        _LOGGER.debug("Unloading cloud account entry: %s", entry.entry_id)
        # Unload camera platform for cloud accounts
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
        return unload_ok
    
    # Ensure sub-dictionaries exist for device entries
    if DATA_DEVICES not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_DEVICES] = {}
    if DATA_COORDINATORS not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_COORDINATORS] = {}
    if "discovery_count" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["discovery_count"] = 0
    
    # Check if the entry exists in our data
    if entry.entry_id not in hass.data[DOMAIN][DATA_DEVICES]:
        _LOGGER.debug("Entry %s not found in devices data during unload - this is normal during reload operations", entry.entry_id)
        # For missing entries, just return True since there's nothing to unload
        # Don't try to unload platforms as they may not have been properly loaded
        return True
    
    device: DysonDevice = hass.data[DOMAIN][DATA_DEVICES][entry.entry_id]
    
    # Get the platforms that should be unloaded based on device type
    expected_platforms = _async_get_platforms(device)
    _LOGGER.debug("Expected platforms for %s: %s", entry.entry_id, expected_platforms)
    
    # Instead of trying to unload platforms that may not have been loaded,
    # let's be more conservative and only unload if we're confident they exist
    unload_ok = True
    
    try:
        # Try to unload all expected platforms at once
        platforms_unload_result = await hass.config_entries.async_unload_platforms(entry, expected_platforms)
        _LOGGER.debug("Platforms unload result for %s: %s", entry.entry_id, platforms_unload_result)
        unload_ok = platforms_unload_result
        
        # If platforms were successfully unloaded, give extra time for entity cleanup
        if platforms_unload_result:
            _LOGGER.debug("Allowing time for entity cleanup after platform unload")
            await asyncio.sleep(0.5)
        
    except ValueError as e:
        if "never loaded" in str(e).lower():
            _LOGGER.debug("Platforms were never loaded for entry %s - considering unload successful", entry.entry_id)
            # This is actually a successful scenario during reload - the platforms weren't loaded
            unload_ok = True
        else:
            _LOGGER.warning("ValueError during platform unload for entry %s: %s", entry.entry_id, e)
            # For other ValueErrors, we'll still consider it successful to avoid blocking the unload
            unload_ok = True
    except Exception as e:
        _LOGGER.warning("Error unloading platforms for entry %s (continuing with cleanup): %s", entry.entry_id, e)
        # Even if platform unload fails, continue with the rest of the cleanup
        unload_ok = True

    # Always proceed with cleanup, even if platform unload had issues
    
    # Handle discovery cleanup BEFORE removing device from DATA_DEVICES
    # This ensures the preservation logic can properly check for other devices
    _LOGGER.debug("Checking if entry uses discovery - CONF_HOST: %s", entry.data.get(CONF_HOST))
    if entry.data.get(CONF_HOST) is None:  # Only if using discovery
        _LOGGER.debug("Entry uses discovery, handling discovery cleanup")
        hass.data[DOMAIN]["discovery_count"] = max(0, hass.data[DOMAIN]["discovery_count"] - 1)
        _LOGGER.debug("Discovery count after decrement: %d", hass.data[DOMAIN]["discovery_count"])
        
        # Always preserve discovered devices during reload, even if discovery service continues running
        discovery = hass.data[DOMAIN][DATA_DISCOVERY]
        _LOGGER.debug("Discovery service exists: %s", discovery is not None)
        if discovery:
            try:
                # Save discovered devices before any cleanup
                # This prevents losing device IP addresses during reload
                saved_discovered = {}
                with discovery._lock:
                    saved_discovered = discovery._discovered.copy()
                    _LOGGER.debug("Discovery service _discovered contents: %s", dict(discovery._discovered))
                    _LOGGER.debug("Discovery service _registered contents: %s", dict(discovery._registered))
                
                _LOGGER.debug("Saved discovered devices during unload: %s", list(saved_discovered.keys()))
                
                # Always preserve discovered devices for potential reload
                # This ensures that devices can reconnect immediately after reload
                if saved_discovered:
                    _LOGGER.debug("Preserving discovered devices for potential reload: %s", list(saved_discovered.keys()))
                    # Store the discovered devices in hass.data for potential reuse
                    hass.data[DOMAIN]["preserved_discovered"] = saved_discovered
                else:
                    _LOGGER.debug("No discovered devices to preserve")
                
            except Exception as e:
                _LOGGER.warning("Error preserving discovery data: %s", e)
        
        # Only stop discovery service if no other devices are using it
        if hass.data[DOMAIN]["discovery_count"] <= 0:
            _LOGGER.debug("Stopping dyson discovery - no more devices using it")
            if discovery:
                try:
                    await hass.async_add_executor_job(discovery.stop_discovery)
                    _LOGGER.debug("Successfully stopped discovery service")
                except Exception as e:
                    _LOGGER.warning("Error stopping discovery: %s", e)
                hass.data[DOMAIN][DATA_DISCOVERY] = None
            hass.data[DOMAIN]["discovery_count"] = 0
        else:
            _LOGGER.debug("Discovery service continues running - %d devices still using it", hass.data[DOMAIN]["discovery_count"])
    else:
        _LOGGER.debug("Entry uses static host, skipping discovery cleanup")
    
    # Clean up coordinator
    coordinator = hass.data[DOMAIN][DATA_COORDINATORS].pop(entry.entry_id, None)
    if coordinator:
        try:
            # Stop the coordinator if it's running
            if hasattr(coordinator, 'async_shutdown'):
                await coordinator.async_shutdown()
            _LOGGER.debug("Successfully shut down coordinator for %s", device.serial)
        except Exception as e:
            _LOGGER.warning("Error shutting down coordinator for %s: %s", device.serial, e)
    
    # Remove from data dictionaries
    hass.data[DOMAIN][DATA_DEVICES].pop(entry.entry_id, None)
    
    # Disconnect device
    try:
        await hass.async_add_executor_job(device.disconnect)
        _LOGGER.debug("Successfully disconnected device %s", device.serial)
    except Exception as e:
        _LOGGER.warning("Error disconnecting device %s: %s", device.serial, e)
    
    # Give the device a moment to fully disconnect before returning
    # This helps prevent connection issues during immediate reload
    await asyncio.sleep(0.1)
    
    # Ensure entity registry has time to process the unload
    # This is critical for proper entity lifecycle during reload
    await asyncio.sleep(0.4)
    
    _LOGGER.debug("Completed unload for entry %s (device: %s)", entry.entry_id, device.serial if 'device' in locals() else 'unknown')
    return True  # Always return True since we completed cleanup


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload Dyson entry."""
    _LOGGER.debug("Reloading entry: %s", entry.entry_id)
    
    # Unload the entry first
    unload_result = await async_unload_entry(hass, entry)
    if not unload_result:
        _LOGGER.error("Failed to unload entry %s during reload", entry.entry_id)
        return False
    
    # Add a longer delay to ensure complete cleanup and entity registry processing
    # This is critical for proper entity lifecycle management during reload
    await asyncio.sleep(1.5)
    
    # Set up the entry again
    try:
        setup_result = await async_setup_entry(hass, entry)
        if not setup_result:
            _LOGGER.error("Failed to set up entry %s during reload", entry.entry_id)
            return False
    except Exception as e:
        _LOGGER.error("Exception during setup of entry %s during reload: %s", entry.entry_id, e)
        return False
    
    _LOGGER.debug("Successfully reloaded entry: %s", entry.entry_id)
    return True


@callback
def _async_get_platforms(device: DysonDevice) -> List[str]:
    if (isinstance(device, Dyson360Eye)
            or isinstance(device, Dyson360Heurist)
            or isinstance(device, Dyson360VisNav)):
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

    async def async_will_remove_from_hass(self) -> None:
        """Call when entity will be removed from hass."""
        try:
            self._device.remove_message_listener(self._on_message)
        except Exception as e:
            _LOGGER.debug("Error removing message listener for %s: %s", self.unique_id, e)

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

async def _async_register_device_with_discovery(
    hass: HomeAssistant, discovery: DysonDiscovery, device: DysonDevice, setup_entry, entry: ConfigEntry
) -> None:
    """Register device with discovery service with enhanced handling."""
    _LOGGER.debug("Registering device %s with discovery service", device.serial)
    
    # Check what devices are currently discovered
    with discovery._lock:
        discovered_devices = list(discovery._discovered.keys())
        _LOGGER.debug("Currently discovered devices: %s", discovered_devices)
        
        if device.serial in discovery._discovered:
            discovered_ip = discovery._discovered[device.serial]
            _LOGGER.debug("Device %s already discovered at %s, should trigger immediate callback", device.serial, discovered_ip)
    
    # Register the device with discovery
    await hass.async_add_executor_job(
        discovery.register_device, device, setup_entry
    )
    _LOGGER.debug("Registered device %s with discovery", device.serial)
    
    # Give discovery a moment to potentially call the setup callback
    # In case the device was already discovered
    await asyncio.sleep(0.5)
    
    # Check if the device was actually connected
    if entry.entry_id not in hass.data[DOMAIN][DATA_DEVICES]:
        # Check if we have a cached IP for this device
        device_ips = hass.data[DOMAIN].get("device_ips", {})
        if device.serial in device_ips:
            cached_ip = device_ips[device.serial]
            _LOGGER.debug("Found cached IP %s for device %s, attempting connection", cached_ip, device.serial)
            try:
                # Call setup_entry directly with the cached IP
                result = await hass.async_add_executor_job(
                    partial(setup_entry, cached_ip, is_discovery=True)
                )
                if result:
                    _LOGGER.debug("Successfully connected device %s via cached IP", device.serial)
                else:
                    _LOGGER.warning("Failed to connect device %s via cached IP", device.serial)
            except Exception as e:
                _LOGGER.error("Error attempting cached IP connection for device %s: %s", device.serial, e)
        else:
            # Check if we have preserved discovered data as fallback
            preserved_discovered = hass.data[DOMAIN].get("preserved_discovered", {})
            if device.serial in preserved_discovered:
                discovered_ip = preserved_discovered[device.serial]
                _LOGGER.debug("Found device %s at IP %s in preserved discovery data, attempting connection", device.serial, discovered_ip)
                try:
                    # Call setup_entry directly with the preserved IP
                    result = await hass.async_add_executor_job(
                        partial(setup_entry, discovered_ip, is_discovery=True)
                    )
                    if result:
                        _LOGGER.debug("Successfully connected device %s via preserved discovery IP", device.serial)
                    else:
                        _LOGGER.warning("Failed to connect device %s via preserved discovery IP", device.serial)
                except Exception as e:
                    _LOGGER.error("Error attempting preserved discovery connection for device %s: %s", device.serial, e)
            else:
                _LOGGER.info("Device %s will connect when discovered by the discovery service", device.serial)
                # For discovery-based devices, this is normal - they connect when discovered
                # Don't treat this as an error, the device will connect when found
