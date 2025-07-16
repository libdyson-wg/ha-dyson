"""Dyson cloud account client."""

import pathlib
from typing import Callable, List, Optional

import requests
from requests.auth import AuthBase, HTTPBasicAuth

from ..exceptions import (
    DysonAuthRequired,
    DysonInvalidAccountStatus,
    DysonInvalidAuth,
    DysonLoginFailure,
    DysonNetworkError,
    DysonOTPTooFrequently,
    DysonServerError,
    DysonAPIProvisionFailure,
)

from .device_info import DysonDeviceInfo

DYSON_API_HOST = "https://appapi.cp.dyson.com"
DYSON_API_HOST_CN = "https://appapi.cp.dyson.cn"
DYSON_API_HEADERS = {
    "User-Agent": "android client"
}

API_PATH_PROVISION_APP = "/v1/provisioningservice/application/Android/version"
API_PATH_USER_STATUS = "/v3/userregistration/email/userstatus"
API_PATH_EMAIL_REQUEST = "/v3/userregistration/email/auth"
API_PATH_EMAIL_VERIFY = "/v3/userregistration/email/verify"
API_PATH_MOBILE_REQUEST = "/v3/userregistration/mobile/auth"
API_PATH_MOBILE_VERIFY = "/v3/userregistration/mobile/verify"
API_PATH_DEVICES = "/v2/provisioningservice/manifest"

FILE_PATH = pathlib.Path(__file__).parent.absolute()


class HTTPBearerAuth(AuthBase):
    """Attaches HTTP Bearer Authentication to the given Request object."""

    def __init__(self, token):
        """Initialize the auth."""
        self.token = token

    def __eq__(self, other):
        """Return if equal."""
        return self.token == getattr(other, "token", None)

    def __ne__(self, other):
        """Return if not equal."""
        return not self == other

    def __call__(self, r):
        """Attach the authentication."""
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r


class DysonAccount:
    """Dyson account."""

    _HOST = DYSON_API_HOST

    def __init__(
        self,
        auth_info: Optional[dict] = None,
    ):
        """Create a new Dyson account."""
        self._auth_info = auth_info

    @property
    def auth_info(self) -> Optional[dict]:
        """Return the authentication info."""
        return self._auth_info

    @property
    def _auth(self) -> Optional[AuthBase]:
        if self.auth_info is None:
            return None
        # Although basic auth is no longer used by new logins,
        # we still need this for backward capability to already
        # stored auth info.
        if "Password" in self.auth_info:
            return HTTPBasicAuth(
                self.auth_info["Account"],
                self.auth_info["Password"],
            )
        elif self.auth_info.get("tokenType") == "Bearer":
            return HTTPBearerAuth(self.auth_info["token"])
        return None

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        auth: bool = True,
    ) -> requests.Response:
        """Make API request."""
        if auth and self._auth is None:
            raise DysonAuthRequired
        try:
            response = requests.request(
                method,
                self._HOST + path,
                params=params,
                json=data,
                headers=DYSON_API_HEADERS,
                auth=self._auth if auth else None,
                verify=True,
            )
        except requests.RequestException:
            raise DysonNetworkError
        if response.status_code in [401, 403]:
            raise DysonInvalidAuth
        if 500 <= response.status_code < 600:
            raise DysonServerError
        return response

    def _retry_request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        auth: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> requests.Response:
        """Make API request with retry logic."""
        import time
        
        last_exception = None
        for attempt in range(max_retries):
            try:
                return self.request(method, path, params, data, auth)
            except (DysonNetworkError, DysonServerError) as e:
                last_exception = e
                if attempt == max_retries - 1:  # Last attempt
                    raise e
                sleep_time = retry_delay * (backoff_factor ** attempt)
                time.sleep(sleep_time)
            except (DysonInvalidAuth, DysonLoginFailure, DysonOTPTooFrequently):
                # Don't retry these - they're likely permanent or rate-limited
                raise
        
        # This shouldn't be reached, but just in case
        if last_exception:
            raise last_exception

    def provision_api(self) -> None:
        """Provision the client connection to the API

        Calls an app provisioning API. This is expected by the Dyson App API and makes the API server ready to accept
        other API calls from the current IP Address.

        Basically, this unlocks the API - the return value is not needed, and we don't need to save any cookies or
        session tokens. It seems like the API Server sets some internal flag allowing API Calls from a specific address
        based solely on this endpoint being called.

        This isn't likely to be a security measure. It returns a version number in a json-encoded string: `"5.0.21061"`
        and that is likely consumed by an app. Presumably, an official Dyson mobile app could check the version against
        some internal expected value and, for example, prompt a user that it is outdated and direct them to the app
        store to download a new version in order to continue working.
        """

        response = self.request(
            "GET",
            API_PATH_PROVISION_APP,
            params=None,
            data=None,
            auth=False,
        )

        if response.status_code != 200:
            raise DysonAPIProvisionFailure

    def login_email_otp(self, email: str, region: str) -> Callable[[str, str], dict]:
        """Login using email and OTP code."""
        self.provision_api()

        # Check account status. This tells us whether an account is active or not.
        response = self.request(
            "POST",
            API_PATH_USER_STATUS,
            params={"country": region},
            data={"email": email},
            auth=False,
        )

        jsonRes = response.json()

        account_status = jsonRes["accountStatus"]
        if account_status != "ACTIVE":
            raise DysonInvalidAccountStatus(account_status)

        response = self.request(
            "POST",
            API_PATH_EMAIL_REQUEST,
            params={"country": region, "culture": "en-US"},
            data={"email": email},
            auth=False,
        )
        if response.status_code == 429:
            raise DysonOTPTooFrequently

        challenge_id = response.json()["challengeId"]

        def _verify(otp_code: str, password: str):
            import time
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = self.request(
                        "POST",
                        API_PATH_EMAIL_VERIFY,
                        data={
                            "email": email,
                            "password": password,
                            "challengeId": challenge_id,
                            "otpCode": otp_code,
                        },
                        auth=False,
                    )
                    if response.status_code == 400:
                        raise DysonLoginFailure
                    body = response.json()
                    self._auth_info = body
                    return self._auth_info
                except (DysonNetworkError, DysonServerError) as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise e
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                except DysonInvalidAuth:
                    # Don't retry auth failures - they're likely permanent
                    raise

        return _verify

    def devices(self) -> List[DysonDeviceInfo]:
        """Get device info from cloud account."""
        import logging
        import json
        _LOGGER = logging.getLogger(__name__)
        
        self.provision_api()
        devices = []
        response = self._retry_request("GET", API_PATH_DEVICES)
        response_data = response.json()
        
        _LOGGER.debug("Cloud API returned %d devices", len(response_data))
        
        for raw in response_data:
            _LOGGER.debug("Processing device: %s", raw.get("Name", "Unknown"))
            _LOGGER.debug("Device ProductType: %s", raw.get("ProductType", "Unknown"))
            
            # Check for variant field using lowercase "variant" (OpenAPI spec)
            variant_value = raw.get("variant")
            _LOGGER.debug("Device variant: %s", variant_value)
            
            _LOGGER.debug("Device Serial: %s", raw.get("Serial", "Unknown"))
            _LOGGER.debug("Device has LocalCredentials: %s", raw.get("LocalCredentials") is not None)
            
            # Check for alternative field names that might contain variant info
            possible_variant_fields = [
                "variant", "ProductVariant", "productVariant", "ModelVariant", "modelVariant", 
                "DeviceVariant", "deviceVariant", "Type", "type", "Model", "model", "SubType", "subType", 
                "Category", "category", "Region", "region", "Version", "version",
                "ProductCategory", "productCategory", "ProductModel", "productModel", 
                "ProductSubType", "productSubType", "serialNumber", "connectionCategory"
            ]
            
            _LOGGER.debug("Checking for variant information in all possible fields:")
            for field in possible_variant_fields:
                if field in raw:
                    _LOGGER.debug("  %s: %s", field, raw[field])
            
            # Log the complete raw response for this device (truncated for sensitive data)
            raw_copy = raw.copy()
            if "LocalCredentials" in raw_copy:
                raw_copy["LocalCredentials"] = "[REDACTED]"
            _LOGGER.debug("Complete raw device data: %s", json.dumps(raw_copy, indent=2))
            
            if raw.get("LocalCredentials") is None:
                # Lightcycle lights don't have LocalCredentials.
                # They're not supported so just skip.
                # See https://github.com/shenxn/libdyson/issues/2 for more info
                _LOGGER.debug("Skipping device %s - no LocalCredentials", raw.get("Name", "Unknown"))
                continue
            
            try:
                device_info = DysonDeviceInfo.from_raw(raw)
                _LOGGER.debug("Created DysonDeviceInfo - Name: %s, ProductType: %s, Variant: %s, Serial: %s", 
                             device_info.name, device_info.product_type, device_info.variant, device_info.serial)
                
                # Test the device type mapping
                device_type = device_info.get_device_type()
                _LOGGER.debug("Device type mapping: ProductType=%s, Variant=%s -> %s", 
                             device_info.product_type, device_info.variant, device_type)
                
                devices.append(device_info)
                _LOGGER.debug("Successfully added device: %s", device_info.name)
            except Exception as e:
                _LOGGER.error("Error creating device info for %s: %s", raw.get("Name", "Unknown"), str(e))
                import traceback
                _LOGGER.error("Traceback: %s", traceback.format_exc())
        
        _LOGGER.debug("Total devices returned: %d", len(devices))
        return devices


class DysonAccountCN(DysonAccount):
    """Dyson account in Mainland China."""

    _HOST = DYSON_API_HOST_CN

    def login_mobile_otp(self, mobile: str) -> Callable[[str], dict]:
        self.provision_api()

        """Login using phone number and OTP code."""
        response = self.request(
            "POST",
            API_PATH_MOBILE_REQUEST,
            data={"mobile": mobile},
            auth=False,
        )
        if response.status_code == 429:
            raise DysonOTPTooFrequently

        challenge_id = response.json()["challengeId"]

        def _verify(otp_code: str):
            response = self.request(
                "POST",
                API_PATH_MOBILE_VERIFY,
                data={
                    "mobile": mobile,
                    "challengeId": challenge_id,
                    "otpCode": otp_code,
                },
                auth=False,
            )
            if response.status_code == 400:
                raise DysonLoginFailure
            body = response.json()
            self._auth_info = body
            return self._auth_info

        return _verify
