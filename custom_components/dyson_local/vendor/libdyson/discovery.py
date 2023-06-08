"""Dyson device discovery."""

import socket
import threading
from typing import Callable, Optional

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf

from .dyson_device import DysonDevice

TYPE_DYSON_360_EYE = "_360eye_mqtt._tcp.local."
TYPE_DYSON_FAN = "_dyson_mqtt._tcp.local."


class DysonDiscovery:
    """Dyson device discovery."""

    def __init__(self):
        """Initialize the instance."""
        self._registered = {}
        self._discovered = {}
        self._lock = threading.Lock()
        self._browser = None

    def register_device(
        self, device: DysonDevice, callback: Callable[[str], None]
    ) -> None:
        """Register a device."""
        with self._lock:
            if device.serial in self._discovered:
                callback(self._discovered[device.serial])
            else:
                self._registered[device.serial] = callback

    def device_discovered(self, info: ServiceInfo) -> None:
        """Call when a device is discovered."""
        if info.type == TYPE_DYSON_360_EYE:
            serial = (info.name.split(".")[0]).split("-", 1)[1]
        else:  # TYPE_DYSON_FAN
            serial = (info.name.split(".")[0]).split("_")[1]
        address = socket.inet_ntoa(info.addresses[0])
        with self._lock:
            if serial in self._registered:
                callback = self._registered.pop(serial)
                callback(address)
            else:
                self._discovered[serial] = address

    def start_discovery(self, zeroconf_instance: Optional[Zeroconf] = None) -> None:
        """Start discovery."""
        listener = DysonListener(self)
        zeroconf = zeroconf_instance or Zeroconf()
        self._browser = ServiceBrowser(
            zeroconf,
            [TYPE_DYSON_360_EYE, TYPE_DYSON_FAN],
            listener,
        )

    def stop_discovery(self) -> None:
        """Stop discovery."""
        try:
            self._browser.cancel()
        except RuntimeError:
            # Throws when called from callback
            # cannot join current thread
            pass
        self._browser.zc.close()
        self._browser = None


class DysonListener:
    """Listener for zeroconf events."""

    def __init__(self, dyson_discovery: DysonDiscovery):
        """Initialize the listener."""
        self._dyson_discovery = dyson_discovery

    def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        """Add a new service."""
        info = zeroconf.get_service_info(type, name)
        self._dyson_discovery.device_discovered(info)

    def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        """Update a service."""
        # Currently not doing anything

    def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        """Remove a service."""
        # Currently not doing anything
