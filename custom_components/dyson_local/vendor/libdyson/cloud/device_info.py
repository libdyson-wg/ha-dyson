"""Dyson device info."""

from typing import Optional

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
