"""Dyson device info."""

from typing import Optional, Dict
import attr

from .utils import decrypt_password


@attr.s(auto_attribs=True, frozen=True)
class DysonDeviceInfo:
    """Dyson device info."""

    active: Optional[bool]
    serial: str
    name: str
    version: str
    credential: str
    auto_update: bool
    new_version_available: bool
    product_type: str
    iot_details: Optional[Dict] = None

    @classmethod
    def from_raw(cls, raw: dict):
        """Parse raw data."""
        return cls(
            raw["Active"] if "Active" in raw else None,
            raw["Serial"],
            raw["Name"],
            raw["Version"],
            decrypt_password(raw["LocalCredentials"]),
            raw["AutoUpdate"],
            raw["NewVersionAvailable"],
            raw["ProductType"],
        )

    def with_iot_details(self, iot_details: dict) -> "DysonDeviceInfo":
        """Return a new instance of DysonDeviceInfo with IoT details added."""
        return attr.evolve(self, iot_details=iot_details)
