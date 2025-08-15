"""Config flow for Dyson integration."""

import logging
import threading
from typing import Optional

from libdyson import DEVICE_TYPE_NAMES, get_device, get_mqtt_info_from_wifi_info
from libdyson.cloud import DysonDeviceInfo
from libdyson.discovery import DysonDiscovery
from libdyson.exceptions import (
    DysonException,
    DysonFailedToParseWifiInfo,
    DysonInvalidCredential,
    DysonInvalidAuth,
    DysonNetworkError,
    DysonOTPTooFrequently,
    DysonInvalidAccountStatus,
    DysonLoginFailure,
)
from libdyson.cloud import DysonAccount, DysonAccountCN, REGIONS

# Import device type constants for mapping
from libdyson.const import (
    DEVICE_TYPE_360_EYE,
    DEVICE_TYPE_360_HEURIST,
    DEVICE_TYPE_360_VIS_NAV,
    DEVICE_TYPE_PURE_COOL,
    DEVICE_TYPE_PURIFIER_COOL_E,
    DEVICE_TYPE_PURIFIER_COOL_K,
    DEVICE_TYPE_PURIFIER_COOL_M,
    DEVICE_TYPE_PURE_COOL_DESK,
    DEVICE_TYPE_PURE_COOL_LINK,
    DEVICE_TYPE_PURE_COOL_LINK_DESK,
    DEVICE_TYPE_PURE_HOT_COOL,
    DEVICE_TYPE_PURIFIER_HOT_COOL_E,
    DEVICE_TYPE_PURIFIER_HOT_COOL_K,
    DEVICE_TYPE_PURE_HOT_COOL_LINK,
    DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_E,
    DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,
    DEVICE_TYPE_PURIFIER_BIG_QUIET,
)

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.zeroconf import async_get_instance
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_EMAIL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_CREDENTIAL, CONF_DEVICE_TYPE, CONF_SERIAL, DOMAIN

from .cloud.const import CONF_REGION, CONF_AUTH

_LOGGER = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 10

CONF_METHOD = "method"
CONF_SSID = "ssid"
CONF_MOBILE = "mobile"
CONF_OTP = "otp"

SETUP_METHODS = {
    "wifi": "Setup using your device's Wi-Fi sticker",
    "cloud": "Setup automatically with your MyDyson Account",
    "manual": "Setup manually",
}


# Mapping from cloud API ProductType to internal device type codes
CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE = {
    # 360 Eye robot vacuum
    "360 Eye": DEVICE_TYPE_360_EYE,
    "360EYE": DEVICE_TYPE_360_EYE,
    "N223": DEVICE_TYPE_360_EYE,
    
    # 360 Heurist robot vacuum
    "360 Heurist": DEVICE_TYPE_360_HEURIST,
    "360HEURIST": DEVICE_TYPE_360_HEURIST,
    "276": DEVICE_TYPE_360_HEURIST,
    
    # 360 Vis Nav robot vacuum
    "360 Vis Nav": DEVICE_TYPE_360_VIS_NAV,
    "360VIS": DEVICE_TYPE_360_VIS_NAV,
    "277": DEVICE_TYPE_360_VIS_NAV,
    
    # Pure Cool Link models
    "TP02": DEVICE_TYPE_PURE_COOL_LINK,
    "TP01": DEVICE_TYPE_PURE_COOL_LINK,
    "DP01": DEVICE_TYPE_PURE_COOL_LINK_DESK,
    "DP02": DEVICE_TYPE_PURE_COOL_LINK_DESK,
    "475": DEVICE_TYPE_PURE_COOL_LINK,
    "469": DEVICE_TYPE_PURE_COOL_LINK_DESK,
    
    # Pure Cool models
    "TP04": DEVICE_TYPE_PURE_COOL,
    "AM06": DEVICE_TYPE_PURE_COOL_DESK,
    "438": DEVICE_TYPE_PURE_COOL,        # Older TP04 devices (when no variant field)
    "520": DEVICE_TYPE_PURE_COOL_DESK,
    
    # Purifier Cool models (newer) - specific model mappings for better compatibility
    "TP07": DEVICE_TYPE_PURIFIER_COOL_K, # TP07 typically K series
    "TP09": DEVICE_TYPE_PURIFIER_COOL_K, # TP09 typically K series
    "TP11": DEVICE_TYPE_PURIFIER_COOL_M, # TP11 is M series
    "PC1": DEVICE_TYPE_PURIFIER_COOL_M,  # PC1 is M series
    # Variant combinations for Cool series
    "438K": DEVICE_TYPE_PURIFIER_COOL_K,
    "438E": DEVICE_TYPE_PURIFIER_COOL_E,
    "438M": DEVICE_TYPE_PURIFIER_COOL_M,
    
    # Pure Hot+Cool Link models
    "HP02": DEVICE_TYPE_PURE_HOT_COOL_LINK,
    "455": DEVICE_TYPE_PURE_HOT_COOL_LINK,
    
    # Pure Hot+Cool models
    "HP04": DEVICE_TYPE_PURE_HOT_COOL,
    "527": DEVICE_TYPE_PURE_HOT_COOL,    # Older HP04 devices (when no variant field)
    
    # Purifier Hot+Cool models (newer) - specific model mappings for better compatibility
    "HP07": DEVICE_TYPE_PURIFIER_HOT_COOL_K,  # HP07 typically K series
    "HP09": DEVICE_TYPE_PURIFIER_HOT_COOL_K,  # HP09 typically K series
    # Variant combinations for Hot+Cool series
    "527K": DEVICE_TYPE_PURIFIER_HOT_COOL_K,
    "527E": DEVICE_TYPE_PURIFIER_HOT_COOL_E,
    "527M": DEVICE_TYPE_PURIFIER_HOT_COOL_K,  # HP series doesn't have M variant, map to K
    
    # Pure Humidify+Cool models
    "PH01": DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    "PH02": DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    "358": DEVICE_TYPE_PURE_HUMIDIFY_COOL,   # Older PH01/PH02 devices (when no variant field)
    
    # Purifier Humidify+Cool models (newer) - specific model mappings for better compatibility
    "PH03": DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,  # PH03 typically K series
    "PH04": DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,  # PH04 typically K series
    # Variant combinations for Humidify+Cool series
    "358K": DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,
    "358E": DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_E,
    "358M": DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,  # PH series doesn't have M variant, map to K
    
    # Purifier Big+Quiet models
    "BP02": DEVICE_TYPE_PURIFIER_BIG_QUIET,
    "BP03": DEVICE_TYPE_PURIFIER_BIG_QUIET,
    "BP04": DEVICE_TYPE_PURIFIER_BIG_QUIET,
    "664": DEVICE_TYPE_PURIFIER_BIG_QUIET,
}


# Note: We use the mapping function from device_info.py instead of duplicating it here
# to ensure consistent behavior and proper variant handling

class DysonLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Dyson local config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self._device_info = None

    async def async_step_user(self, info: Optional[dict] = None):
        """Handle step initialized by user."""
        if info is not None:
            if info[CONF_METHOD] == "wifi":
                return await self.async_step_wifi()
            if info[CONF_METHOD] == "cloud":
                return await self.async_step_cloud()
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_METHOD): vol.In(SETUP_METHODS)}),
        )

    async def async_step_wifi(self, info: Optional[dict] = None):
        """Handle step to set up using device Wi-Fi information."""
        errors = {}
        if info is not None:
            try:
                serial, credential, device_type = get_mqtt_info_from_wifi_info(
                    info[CONF_SSID], info[CONF_PASSWORD]
                )
            except DysonFailedToParseWifiInfo:
                errors["base"] = "cannot_parse_wifi_info"
            else:
                device_type_name = DEVICE_TYPE_NAMES[device_type]
                _LOGGER.debug("Successfully parse WiFi information")
                _LOGGER.debug("Serial: %s", serial)
                _LOGGER.debug("Device Type: %s", device_type)
                _LOGGER.debug("Device Type Name: %s", device_type_name)
                try:
                    data = await self._async_get_entry_data(
                        serial,
                        credential,
                        device_type,
                        device_type_name,
                        info.get(CONF_HOST),
                    )
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except CannotFind:
                    errors["base"] = "cannot_find"
                else:
                    return self.async_create_entry(
                        title=device_type_name,
                        data=data,
                    )

        info = info or {}
        return self.async_show_form(
            step_id="wifi",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SSID, default=info.get(CONF_SSID, "")): str,
                    vol.Required(
                        CONF_PASSWORD, default=info.get(CONF_PASSWORD, "")
                    ): str,
                    vol.Optional(CONF_HOST, default=info.get(CONF_HOST, "")): str,
                }
            ),
            errors=errors,
        )

    async def async_step_cloud(self, info: Optional[dict] = None):
        if info is not None:
            self._region = info[CONF_REGION]
            if self._region == "CN":
                return await self.async_step_mobile()
            return await self.async_step_email()

        region_names = {
            code: f"{name} ({code})"
            for code, name in REGIONS.items()
        }
        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({
                vol.Required(CONF_REGION): vol.In(region_names)
            }),
        )

    async def async_step_email(self, info: Optional[dict]=None):
        errors = {}
        if info is not None:
            email = info[CONF_EMAIL]
            unique_id = f"global_{email}"
            for entry in self._async_current_entries():
                if entry.unique_id == unique_id:
                    return self.async_abort(reason="already_configured")
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            account = DysonAccount()
            try:
                self._verify = await self.hass.async_add_executor_job(
                    account.login_email_otp, email, self._region
                )
            except DysonNetworkError:
                errors["base"] = "cannot_connect_cloud"
            except DysonInvalidAccountStatus:
                errors["base"] = "email_not_registered"
            except DysonInvalidAuth:
                errors["base"] = "invalid_auth"
            else:
                self._email = email
                return await self.async_step_email_otp()

        info = info or {}
        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL, default=info.get(CONF_EMAIL, "")): str,
            }),
            errors=errors,
        )

    async def async_step_email_otp(self, info: Optional[dict]=None):
        errors = {}
        if info is not None:
            try:
                auth_info = await self.hass.async_add_executor_job(
                    self._verify, info[CONF_OTP], info[CONF_PASSWORD]
                )
            except DysonLoginFailure:
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title=f"MyDyson: {self._email} ({self._region})",
                    data={
                        CONF_REGION: self._region,
                        CONF_AUTH: auth_info,
                    }
                )

        return self.async_show_form(
            step_id="email_otp",
            data_schema=vol.Schema({
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_OTP): str,
            }),
            errors=errors,
        )

    async def async_step_mobile(self, info: Optional[dict]=None):
        errors = {}
        if info is not None:
            account = DysonAccountCN()
            mobile = info[CONF_MOBILE]
            if not mobile.startswith("+"):
                mobile = f"+86{mobile}"
            try:
                self._verify = await self.hass.async_add_executor_job(
                    account.login_mobile_otp, mobile
                )
            except DysonOTPTooFrequently:
                errors["base"] = "otp_too_frequent"
            else:
                self._mobile = mobile
                return await self.async_step_mobile_otp()

        info = info or {}
        return self.async_show_form(
            step_id="mobile",
            data_schema=vol.Schema({
                vol.Required(CONF_MOBILE, default=info.get(CONF_MOBILE, "")): str,
            }),
            errors=errors,
        )

    async def async_step_mobile_otp(self, info: Optional[dict]=None):
        errors = {}
        if info is not None:
            try:
                auth_info = await self.hass.async_add_executor_job(
                    self._verify, info[CONF_OTP]
                )
            except DysonLoginFailure:
                errors["base"] = "invalid_otp"
            else:
                return self.async_create_entry(
                    title=f"MyDyson: {self._mobile} ({self._region})",
                    data={
                        CONF_REGION: self._region,
                        CONF_AUTH: auth_info,
                    }
                )

        return self.async_show_form(
            step_id="mobile_otp",
            data_schema=vol.Schema({
                vol.Required(CONF_OTP): str,
            }),
            errors=errors,
        )


    async def async_step_manual(self, info: Optional[dict] = None):
        """Handle step to setup manually."""
        errors = {}
        if info is not None:
            serial = info[CONF_SERIAL]
            for entry in self._async_current_entries():
                if entry.unique_id == serial:
                    return self.async_abort(reason="already_configured")
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured()

            device_type = info[CONF_DEVICE_TYPE]
            device_type_name = DEVICE_TYPE_NAMES[device_type]
            try:
                data = await self._async_get_entry_data(
                    serial,
                    info[CONF_CREDENTIAL],
                    device_type,
                    device_type_name,
                    info.get(CONF_HOST),
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except CannotFind:
                errors["base"] = "cannot_find"
            else:
                return self.async_create_entry(
                    title=device_type_name,
                    data=data,
                )

        info = info or {}
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL, default=info.get(CONF_SERIAL, "")): str,
                    vol.Required(
                        CONF_CREDENTIAL, default=info.get(CONF_CREDENTIAL, "")
                    ): str,
                    vol.Required(
                        CONF_DEVICE_TYPE, default=info.get(CONF_DEVICE_TYPE, "")
                    ): vol.In(DEVICE_TYPE_NAMES),
                    vol.Optional(CONF_HOST, default=info.get(CONF_HOST, "")): str,
                }
            ),
            errors=errors,
        )

    async def async_step_host(self, info: Optional[dict] = None):
        """Handle step to set host."""
        errors = {}
        if info is not None:
            # Use the device info's built-in mapping method which handles variants properly
            device_type = self._device_info.get_device_type()
            
            _LOGGER.debug("Cloud ProductType: %s, variant: %s, Mapped to: %s", 
                         self._device_info.product_type, getattr(self._device_info, 'variant', None), device_type)
            _LOGGER.debug("Device info object has variant attribute: %s", hasattr(self._device_info, 'variant'))
            if hasattr(self._device_info, 'variant'):
                _LOGGER.debug("Raw variant value: %r", self._device_info.variant)
            if device_type is None:
                _LOGGER.error("Unknown device type for ProductType: %s, variant: %s", 
                             self._device_info.product_type, getattr(self._device_info, 'variant', None))
                errors["base"] = "unknown_device_type"
            else:
                try:
                    data = await self._async_get_entry_data(
                        self._device_info.serial,
                        self._device_info.credential,
                        device_type,
                        info.get(CONF_NAME),
                        info.get(CONF_HOST),
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except CannotFind:
                    errors["base"] = "cannot_find"
                else:
                    return self.async_create_entry(
                        title=info.get(CONF_NAME),
                        data=data,
                    )

        # NOTE: Sometimes, the device is not named. In these situations,
        # default to using the unique serial number as the name.
        name = self._device_info.name or self._device_info.serial

        info = info or {}
        return self.async_show_form(
            step_id="host",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOST, default=info.get(CONF_HOST, "")): str,
                    vol.Optional(CONF_NAME, default=info.get(CONF_NAME, name)): str,
                }
            ),
            errors=errors,
        )

    async def async_step_discovery(self, info: DysonDeviceInfo):
        """Handle step initialized by MyDyson discovery."""
        _LOGGER.debug("Starting discovery step for device: %s (ProductType: %s)", 
                     info.name, info.product_type)
        
        for entry in self._async_current_entries():
            if entry.unique_id == info.serial:
                _LOGGER.debug("Device %s already configured, aborting", info.serial)
                return self.async_abort(reason="already_configured")
        
        await self.async_set_unique_id(info.serial)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {
            CONF_NAME: info.name,
            CONF_SERIAL: info.serial,
        }
        self._device_info = info
        _LOGGER.debug("Device %s passed initial checks, proceeding to host step", info.serial)
        return await self.async_step_host()

    async def _async_get_entry_data(
        self,
        serial: str,
        credential: str,
        device_type: str,
        name: str,
        host: Optional[str] = None,
    ) -> Optional[str]:
        """Try connect and return config entry data."""
        await self._async_try_connect(serial, credential, device_type, host)
        return {
            CONF_SERIAL: serial,
            CONF_CREDENTIAL: credential,
            CONF_DEVICE_TYPE: device_type,
            CONF_NAME: name,
            CONF_HOST: host,
        }

    async def _async_try_connect(
        self,
        serial: str,
        credential: str,
        device_type: str,
        host: Optional[str] = None,
    ) -> None:
        """Try connect."""
        _LOGGER.debug("Attempting to connect to device: serial=%s, device_type=%s, host=%s", 
                     serial, device_type, host)
        
        device = get_device(serial, credential, device_type)
        
        # Check if device creation failed
        if device is None:
            _LOGGER.error("Failed to create device object for serial=%s, device_type=%s. "
                         "This usually indicates an unknown or unsupported device type.", 
                         serial, device_type)
            raise CannotConnect
        
        _LOGGER.debug("Successfully created device object of type: %s", type(device).__name__)

        # Find device using discovery
        if not host:
            _LOGGER.debug("No host provided, starting device discovery for serial: %s", serial)
            discovered = threading.Event()

            def _callback(address: str) -> None:
                _LOGGER.debug("Found device at %s", address)
                nonlocal host
                host = address
                discovered.set()

            discovery = DysonDiscovery()
            discovery.register_device(device, _callback)
            
            # Log the expected service type for debugging
            expected_service_type = "_360eye_mqtt._tcp.local." if device_type == "N223" else "_dyson_mqtt._tcp.local."
            _LOGGER.debug("Starting discovery for device_type=%s, expecting service type: %s", 
                         device_type, expected_service_type)
            
            discovery.start_discovery(await async_get_instance(self.hass))
            succeed = await self.hass.async_add_executor_job(
                discovered.wait, DISCOVERY_TIMEOUT
            )
            discovery.stop_discovery()
            if not succeed:
                _LOGGER.error("Discovery timed out for device serial=%s, device_type=%s. "
                             "Expected service type: %s", serial, device_type, expected_service_type)
                raise CannotFind
            
            _LOGGER.debug("Discovery successful, device found at: %s", host)

        # Try connect to the device
        _LOGGER.debug("Attempting MQTT connection to device at %s", host)
        try:
            device.connect(host)
            _LOGGER.debug("Successfully connected to device via MQTT")
        except DysonInvalidCredential:
            _LOGGER.error("Invalid credentials for device serial=%s", serial)
            raise InvalidAuth
        except DysonException as err:
            _LOGGER.error("Failed to connect to device serial=%s, device_type=%s, host=%s: %s (%s)", 
                         serial, device_type, host, type(err).__name__, err)
            
            # Add specific logging for MQTT connection refused errors
            if "Connection refused" in str(err) or "result code 7" in str(err):
                _LOGGER.error("MQTT connection refused (result code 7) - this may indicate:")
                _LOGGER.error("  1. Wrong device type mapping (expected: %s)", device_type)
                _LOGGER.error("  2. Device firmware issue or unexpected state")
                _LOGGER.error("  3. MQTT broker unavailable on device")
                _LOGGER.error("  4. Network connectivity problems")
                _LOGGER.error("  5. Device already has too many connections")
            
            raise CannotConnect


class CannotConnect(HomeAssistantError):
    """Represents connection failure."""


class CannotFind(HomeAssistantError):
    """Represents discovery failure."""


class InvalidAuth(HomeAssistantError):
    """Represents invalid authentication."""
