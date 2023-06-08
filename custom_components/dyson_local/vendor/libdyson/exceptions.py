"""Dyson Python library exceptions."""


class DysonException(Exception):
    """Base class for exceptions."""


class DysonNetworkError(DysonException):
    """Represents network error."""


class DysonServerError(DysonException):
    """Represents Dyson server error."""


class DysonInvalidAccountStatus(DysonException):
    """Represents invalid account status."""


class DysonLoginFailure(DysonException):
    """Represents failure during logging in."""


class DysonAPIProvisionFailure(DysonException):
    """Represents failure during logging in."""


class DysonOTPTooFrequently(DysonException):
    """Represents requesting OTP code too frequently."""


class DysonAuthRequired(DysonException):
    """Represents not logged into could."""


class DysonInvalidAuth(DysonException):
    """Represents invalid authentication."""


class DysonConnectTimeout(DysonException):
    """Represents mqtt connection timeout."""


class DysonNotConnected(DysonException):
    """Represents mqtt not connected."""


class DysonInvalidCredential(DysonException):
    """Represents invalid mqtt credential."""


class DysonConnectionRefused(DysonException):
    """Represents mqtt connection refused by the server."""


class DysonFailedToParseWifiInfo(DysonException):
    """Represents failed to parse WiFi information."""


class DysonNoEnvironmentalData(DysonException):
    """Represents mqtt not connected."""
