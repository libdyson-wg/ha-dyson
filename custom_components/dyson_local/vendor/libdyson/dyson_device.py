"""Dyson device."""
from abc import abstractmethod
import json
import logging
import threading
from typing import Any, Optional, List, Dict, Union

import paho.mqtt.client as mqtt

from .const import (
    ENVIRONMENTAL_FAIL,
    ENVIRONMENTAL_INIT,
    ENVIRONMENTAL_OFF,
    MessageType,
)
from .exceptions import (
    DysonConnectionRefused,
    DysonConnectTimeout,
    DysonInvalidCredential,
    DysonNotConnected, DysonNoEnvironmentalData,
)
from .utils import mqtt_time

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 10


class DysonDevice:
    """Base class for dyson devices."""

    def __init__(self, serial: str, credential: str):
        """Initialize the device."""
        self._serial = serial
        self._credential = credential
        self._mqtt_client = None
        self._connected = threading.Event()
        self._disconnected = threading.Event()
        self._status = None
        self._status_data_available = threading.Event()
        self._callbacks = []

    @property
    def serial(self) -> str:
        """Return the serial number of the device."""
        return self._serial

    @property
    def is_connected(self) -> bool:
        """Whether MQTT connection is active."""
        return self._connected.is_set()

    @property
    @abstractmethod
    def device_type(self) -> str:
        """Device type."""

    @property
    @abstractmethod
    def _status_topic(self) -> str:
        """MQTT status topic."""

    @property
    def _command_topic(self) -> str:
        """MQTT command topic."""
        return f"{self.device_type}/{self._serial}/command"

    def _request_first_data(self) -> bool:
        """Request and wait for first data."""
        self.request_current_status()
        return self._status_data_available.wait(timeout=TIMEOUT)

    def connect(self, host: str) -> None:
        """Connect to the device MQTT broker."""
        self._disconnected.clear()
        self._mqtt_client = mqtt.Client(protocol=mqtt.MQTTv31)
        self._mqtt_client.username_pw_set(self._serial, self._credential)
        error = None

        def _on_connect(client: mqtt.Client, userdata: Any, flags, rc):
            _LOGGER.debug("Connected with result code %d", rc)
            nonlocal error
            if rc == mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD:
                error = DysonInvalidCredential
            elif rc != mqtt.CONNACK_ACCEPTED:
                error = DysonConnectionRefused
            else:
                client.subscribe(self._status_topic)
            self._connected.set()

        def _on_disconnect(client, userdata, rc):
            _LOGGER.debug(f"Disconnected with result code {str(rc)}")

        self._disconnected.set()

        self._mqtt_client.on_connect = _on_connect
        self._mqtt_client.on_disconnect = _on_disconnect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.connect_async(host)
        self._mqtt_client.loop_start()
        if self._connected.wait(timeout=TIMEOUT):
            if error is not None:
                self.disconnect()
                raise error

            _LOGGER.info("Connected to device %s", self._serial)
            if self._request_first_data():
                self._mqtt_client.on_connect = self._on_connect
                self._mqtt_client.on_disconnect = self._on_disconnect
                return

        # Close connection if timeout or connected but failed to get data
        self.disconnect()

        raise DysonConnectTimeout

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self._connected.clear()
        self._mqtt_client.disconnect()
        if not self._disconnected.wait(timeout=TIMEOUT):
            _LOGGER.warning("Disconnect timed out")
        self._mqtt_client.loop_stop()
        self._mqtt_client = None

    def add_message_listener(self, callback) -> None:
        """Add a callback to receive update notification."""
        self._callbacks.append(callback)

    def remove_message_listener(self, callback) -> None:
        """Remove an existed callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags, rc):
        _LOGGER.debug("Connected with result code %d", rc)
        self._disconnected.clear()
        self._connected.set()
        client.subscribe(self._status_topic)
        for callback in self._callbacks:
            callback(MessageType.STATE)

    def _on_disconnect(self, client, userdata, rc):
        _LOGGER.debug(f"Disconnected with result code {str(rc)}")
        self._connected.clear()
        self._disconnected.set()
        for callback in self._callbacks:
            callback(MessageType.STATE)

    def _on_message(self, client, userdata: Any, msg: mqtt.MQTTMessage):
        payload = json.loads(msg.payload.decode("utf-8"))
        self._handle_message(payload)

    def _handle_message(self, payload: dict) -> None:
        if payload["msg"] in ["CURRENT-STATE", "STATE-CHANGE"]:
            _LOGGER.debug("New state: %s", payload)
            self._update_status(payload)
            if not self._status_data_available.is_set():
                self._status_data_available.set()
            for callback in self._callbacks:
                callback(MessageType.STATE)

    @abstractmethod
    def _update_status(self, payload: dict) -> None:
        """Update the device status."""

    def _send_command(self, command: str, data: Optional[dict] = None) -> None:
        if not self.is_connected:
            raise DysonNotConnected
        if data is None:
            data = {}
        payload = {
            "msg": command,
            "time": mqtt_time(),
        }
        payload.update(data)
        self._mqtt_client.publish(self._command_topic, json.dumps(payload))

    def request_current_status(self) -> None:
        """Request current status."""
        if not self.is_connected:
            raise DysonNotConnected
        payload = {
            "msg": "REQUEST-CURRENT-STATE",
            "time": mqtt_time(),
        }
        self._mqtt_client.publish(self._command_topic, json.dumps(payload))


class DysonFanDevice(DysonDevice):
    """Dyson fan device."""

    def __init__(self, serial: str, credential: str, device_type: str):
        """Initialize the device."""
        super().__init__(serial, credential)
        self._device_type = device_type

        self._environmental_data = {}
        self._environmental_data_available = threading.Event()

    @property
    def device_type(self) -> str:
        """Device type."""
        return self._device_type

    @property
    def _status_topic(self) -> str:
        """MQTT status topic."""
        return f"{self.device_type}/{self._serial}/status/current"

    @property
    def fan_state(self) -> bool:
        """Return if the fan is running."""
        return self._get_field_value(self._status, "fnst") == "FAN"

    @property
    def speed(self) -> Optional[int]:
        """Return fan speed."""
        speed = self._get_field_value(self._status, "fnsp")
        if speed == "AUTO":
            return None
        return int(speed)

    @property
    @abstractmethod
    def is_on(self) -> bool:
        """Return if the device is on."""

    @property
    @abstractmethod
    def auto_mode(self) -> bool:
        """Return auto mode status."""

    @property
    @abstractmethod
    def oscillation(self) -> bool:
        """Return oscillation status."""

    @property
    def night_mode(self) -> bool:
        """Return night mode status."""
        return self._get_field_value(self._status, "nmod") == "ON"

    @property
    def continuous_monitoring(self) -> bool:
        """Return standby monitoring status."""
        return self._get_field_value(self._status, "rhtm") == "ON"

    @property
    def error_code(self) -> str:
        """Return error code."""
        return self._get_field_value(self._status, "ercd")

    @property
    def warning_code(self) -> str:
        """Return warning code."""
        return self._get_field_value(self._status, "wacd")

    @property
    def formaldehyde(self) -> Optional[float]:
        """Return formaldehyde reading."""
        val = self._get_environmental_field_value("hchr", divisor=1000)
        if val is None:
            return None

        return float(val)

    @property
    def humidity(self) -> int:
        """Return humidity in percentage."""
        return self._get_environmental_field_value("hact")

    @property
    def temperature(self) -> int:
        """Return temperature in kelvin."""
        return self._get_environmental_field_value("tact", divisor=10)

    @property
    @abstractmethod
    def volatile_organic_compounds(self) -> int:
        """Return VOCs."""

    @property
    def sleep_timer(self) -> int:
        """Return sleep timer in minutes."""
        return self._get_environmental_field_value("sltm")

    @staticmethod
    def _get_field_value(state: Dict[str, Any], field: str):
        try:
            return  state[field][1] if isinstance(state[field], list) else state[field]
        except:
            return None

    def _get_environmental_field_value(self, field, divisor=1) -> Optional[Union[int, float]]:
        value = self._get_field_value(self._environmental_data, field)
        if value == "OFF" or value == "off":
            return ENVIRONMENTAL_OFF
        if value == "INIT":
            return ENVIRONMENTAL_INIT
        if value == "FAIL":
            return ENVIRONMENTAL_FAIL
        if value == "NONE" or value is None:
            return None
        if divisor == 1:
            return int(value)
        return float(value) / divisor

    def _handle_message(self, payload: dict) -> None:
        super()._handle_message(payload)
        if payload["msg"] == "ENVIRONMENTAL-CURRENT-SENSOR-DATA":
            _LOGGER.debug("New environmental state: %s", payload)
            self._environmental_data = payload["data"]
            if not self._environmental_data_available.is_set():
                self._environmental_data_available.set()
            for callback in self._callbacks:
                callback(MessageType.ENVIRONMENTAL)

    def _update_status(self, payload: dict) -> None:
        self._status = payload["product-state"]

    def _set_configuration(self, **kwargs: dict) -> None:
        if not self.is_connected:
            raise DysonNotConnected
        payload = json.dumps(
            {
                "msg": "STATE-SET",
                "time": mqtt_time(),
                "mode-reason": "LAPP",
                "data": kwargs,
            }
        )
        self._mqtt_client.publish(self._command_topic, payload, 1)

    def _request_first_data(self) -> bool:
        """Request and wait for first data."""
        self.request_current_status()
        self.request_environmental_data()
        status_available = self._status_data_available.wait(timeout=TIMEOUT)
        environmental_available = self._environmental_data_available.wait(
            timeout=TIMEOUT
        )
        return status_available and environmental_available

    def request_environmental_data(self):
        """Request environmental sensor data."""
        if not self.is_connected:
            raise DysonNotConnected
        payload = {
            "msg": "REQUEST-PRODUCT-ENVIRONMENT-CURRENT-SENSOR-DATA",
            "time": mqtt_time(),
        }
        self._mqtt_client.publish(self._command_topic, json.dumps(payload))

    @abstractmethod
    def turn_on(self) -> None:
        """Turn on the device."""

    @abstractmethod
    def turn_off(self) -> None:
        """Turn off the device."""

    def set_speed(self, speed: int) -> None:
        """Set manual speed."""
        if not 1 <= speed <= 10:
            raise ValueError("Invalid speed %s", speed)
        self._set_speed(speed)

    @abstractmethod
    def _set_speed(self, speed: int) -> None:
        """Actually set the speed without range check."""

    @abstractmethod
    def enable_auto_mode(self) -> None:
        """Turn on auto mode."""

    @abstractmethod
    def disable_auto_mode(self) -> None:
        """Turn off auto mode."""

    @abstractmethod
    def enable_oscillation(self) -> None:
        """Turn on oscillation."""

    @abstractmethod
    def disable_oscillation(self) -> None:
        """Turn off oscillation."""

    def enable_night_mode(self) -> None:
        """Turn on auto mode."""
        self._set_configuration(nmod="ON")

    def disable_night_mode(self) -> None:
        """Turn off auto mode."""
        self._set_configuration(nmod="OFF")

    @abstractmethod
    def enable_continuous_monitoring(self) -> None:
        """Turn on continuous monitoring."""

    @abstractmethod
    def disable_continuous_monitoring(self) -> None:
        """Turn off continuous monitoring."""

    def set_sleep_timer(self, duration: int) -> None:
        """Set sleep timer."""
        if not 0 < duration <= 540:
            raise ValueError("Duration must be between 1 and 540")
        self._set_configuration(sltm="%04d" % duration)

    def disable_sleep_timer(self) -> None:
        """Disable sleep timer."""
        self._set_configuration(sltm="OFF")

    def reset_filter(self) -> None:
        """Reset filter life."""
        self._set_configuration(rstf="RSTF")


class DysonHeatingDevice(DysonFanDevice):
    """Dyson heating fan device."""

    @property
    def focus_mode(self) -> bool:
        """Return if fan focus mode is on."""
        return self._get_field_value(self._status, "ffoc") == "ON"

    @property
    def heat_target(self) -> float:
        """Return heat target in kelvin."""
        return int(self._get_field_value(self._status, "hmax")) / 10

    @property
    def heat_mode_is_on(self) -> bool:
        """Return if heat mode is set to on."""
        return self._get_field_value(self._status, "hmod") == "HEAT"

    @property
    def heat_status_is_on(self) -> bool:
        """Return if the device is currently heating."""
        return self._get_field_value(self._status, "hsta") == "HEAT"

    def set_heat_target(self, heat_target: float) -> None:
        """Set heat target in kelvin."""
        if not 274 <= heat_target <= 310:
            raise ValueError("Heat target must be between 274 and 310 kelvin")
        self._set_configuration(
            hmod="HEAT",
            hmax=f"{round(heat_target * 10):04d}",
        )

    def enable_heat_mode(self) -> None:
        """Enable heat mode."""
        self._set_configuration(hmod="HEAT")

    def disable_heat_mode(self) -> None:
        """Disable heat mode."""
        self._set_configuration(hmod="OFF")
