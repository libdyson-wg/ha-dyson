"""Dyson device info."""

from typing import Optional

import attr

from ..const import (  # noqa: F401
    DEVICE_TYPE_360_EYE,
    DEVICE_TYPE_360_HEURIST,
    DEVICE_TYPE_360_VIS_NAV,
    DEVICE_TYPE_PURE_COOL,
    DEVICE_TYPE_PURE_COOL_DESK,
    DEVICE_TYPE_PURE_COOL_LINK,
    DEVICE_TYPE_PURE_COOL_LINK_DESK,
    DEVICE_TYPE_PURE_HOT_COOL,
    DEVICE_TYPE_PURE_HOT_COOL_LINK,
    DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    DEVICE_TYPE_PURIFIER_BIG_QUIET,
    DEVICE_TYPE_PURIFIER_COOL_E,
    DEVICE_TYPE_PURIFIER_COOL_K,
    DEVICE_TYPE_PURIFIER_COOL_M,
    DEVICE_TYPE_PURIFIER_HOT_COOL_E,
    DEVICE_TYPE_PURIFIER_HOT_COOL_K,
    DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_E,
    DEVICE_TYPE_PURIFIER_HUMIDIFY_COOL_K,
)
from .utils import decrypt_password

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
    # Pure Cool models - all variants use the same DysonPureCool class
    "TP04": DEVICE_TYPE_PURE_COOL,
    "AM06": DEVICE_TYPE_PURE_COOL_DESK,
    "438": DEVICE_TYPE_PURE_COOL,  # Default for ProductType "438" - backward compatible
    "520": DEVICE_TYPE_PURE_COOL_DESK,
    # Purifier Cool models (newer) - all merged to use the same device type
    "TP07": DEVICE_TYPE_PURE_COOL,  # All TP07 variants use DysonPureCool class
    "TP09": DEVICE_TYPE_PURE_COOL,  # All TP09 variants use DysonPureCool class
    "TP11": DEVICE_TYPE_PURE_COOL,  # All TP11 variants use DysonPureCool class
    "PC1": DEVICE_TYPE_PURE_COOL,  # All PC1 variants use DysonPureCool class
    # Variant combinations for Cool series - all merged to use the same device type
    "438K": DEVICE_TYPE_PURE_COOL,  # Merged: all 438 variants use same class
    "438E": DEVICE_TYPE_PURE_COOL,  # Merged: all 438 variants use same class
    "438M": DEVICE_TYPE_PURE_COOL,  # Merged: all 438 variants use same class
    # Pure Hot+Cool Link models
    "HP02": DEVICE_TYPE_PURE_HOT_COOL_LINK,
    "455": DEVICE_TYPE_PURE_HOT_COOL_LINK,
    # Pure Hot+Cool models - all variants use the same DysonPureHotCool class
    "HP04": DEVICE_TYPE_PURE_HOT_COOL,
    "527": DEVICE_TYPE_PURE_HOT_COOL,  # Default for ProductType "527" - backward compatible
    # Purifier Hot+Cool models (newer) - all merged to use the same device type
    "HP07": DEVICE_TYPE_PURE_HOT_COOL,  # All HP07 variants use DysonPureHotCool class
    "HP09": DEVICE_TYPE_PURE_HOT_COOL,  # All HP09 variants use DysonPureHotCool class
    # Variant combinations for Hot+Cool series - all merged to use the same device type
    "527K": DEVICE_TYPE_PURE_HOT_COOL,  # Merged: all 527 variants use same class
    "527E": DEVICE_TYPE_PURE_HOT_COOL,  # Merged: all 527 variants use same class
    "527M": DEVICE_TYPE_PURE_HOT_COOL,  # Merged: all 527 variants use same class
    # Pure Humidify+Cool models - all variants use the same DysonPurifierHumidifyCool class
    "PH01": DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    "PH02": DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    "358": DEVICE_TYPE_PURE_HUMIDIFY_COOL,  # Default for ProductType "358" - backward compatible
    # Purifier Humidify+Cool models (newer) - all merged to use the same device type
    "PH03": DEVICE_TYPE_PURE_HUMIDIFY_COOL,  # All PH03 variants use DysonPurifierHumidifyCool class
    "PH04": DEVICE_TYPE_PURE_HUMIDIFY_COOL,  # All PH04 variants use DysonPurifierHumidifyCool class
    # Variant combinations for Humidify+Cool series - all merged to use the same device type
    "358K": DEVICE_TYPE_PURE_HUMIDIFY_COOL,  # Merged: all 358 variants use same class
    "358E": DEVICE_TYPE_PURE_HUMIDIFY_COOL,  # Merged: all 358 variants use same class
    "358M": DEVICE_TYPE_PURE_HUMIDIFY_COOL,  # Merged: all 358 variants use same class
    # Purifier Big+Quiet models
    "BP02": DEVICE_TYPE_PURIFIER_BIG_QUIET,
    "BP03": DEVICE_TYPE_PURIFIER_BIG_QUIET,
    "BP04": DEVICE_TYPE_PURIFIER_BIG_QUIET,
    "664": DEVICE_TYPE_PURIFIER_BIG_QUIET,
}


def map_product_type_to_device_type(
    product_type: str,
    serial: Optional[str] = None,
    variant: Optional[str] = None,
    name: Optional[str] = None,
) -> Optional[str]:
    """Map cloud API ProductType to internal device type code.

    Args:
        product_type: The ProductType from the cloud API
        serial: Device serial number (optional, for compatibility)
        variant: The variant field from the cloud API (optional, for compatibility)
        name: Device name (optional, for compatibility)

    Returns:
        Internal device type code or None if unknown

    Note:
        For devices that require variant-specific MQTT topics (like 438M, 527K, etc.),
        this function now returns the combined ProductType+Variant (e.g., "438M")
        instead of just the base type ("438"). This ensures the correct MQTT topic
        is used for communication with the device.

        Variant extraction is performed automatically from firmware versions when
        the variant is not provided by the cloud API, ensuring compatibility with
        devices that encode variant information in their firmware version string.
    """
    import logging

    _LOGGER = logging.getLogger(__name__)

    _LOGGER.debug(
        "Mapping ProductType: '%s' (variant: %s, serial: %s)",
        product_type,
        variant,
        serial,
    )

    if not product_type:
        _LOGGER.debug("Empty product_type, returning None")
        return None

    # Note: Variant extraction from firmware is now handled in get_device_type() method
    # No special case handling needed here as firmware-based detection is more reliable

    # For devices with explicit variants that affect MQTT topics, prefer variant-specific mapping
    if variant is not None and variant.strip():
        variant_upper = variant.upper()
        _LOGGER.debug(
            "Attempting variant-based mapping with variant: %s", variant_upper
        )

        # Check for variant combinations first (like 438M, 527K, etc.)
        # These devices need the variant in their MQTT topics
        if product_type in ["438", "527", "358"]:
            combined_type = product_type + variant_upper
            _LOGGER.debug(
                "Checking variant combination: %s + %s = %s",
                product_type,
                variant_upper,
                combined_type,
            )

            # Only return the combined type if it's a known variant
            if combined_type in CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE:
                _LOGGER.debug(
                    "Using variant-specific device type for MQTT: %s", combined_type
                )
                return combined_type
            else:
                _LOGGER.debug(
                    "Unknown variant combination %s, falling back to base type",
                    combined_type,
                )

        # Try direct variant mapping
        if variant_upper in CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE:
            mapped_type = CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE[variant_upper]
            _LOGGER.debug("Found variant mapping: %s -> %s", variant_upper, mapped_type)
            return mapped_type
        else:
            _LOGGER.debug("No direct variant mapping found for: %s", variant_upper)
    else:
        _LOGGER.debug("No variant provided or variant is empty")

    # Direct mapping for most product types (when no variant or variant not needed)
    if product_type in CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE:
        mapped_type = CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE[product_type]
        _LOGGER.debug("Found direct mapping: %s -> %s", product_type, mapped_type)
        return mapped_type

    # Check if product_type is already an internal device type code
    if product_type in [
        DEVICE_TYPE_360_EYE,
        DEVICE_TYPE_360_HEURIST,
        DEVICE_TYPE_360_VIS_NAV,
        DEVICE_TYPE_PURE_COOL,
        DEVICE_TYPE_PURE_COOL_DESK,
        DEVICE_TYPE_PURE_COOL_LINK,
        DEVICE_TYPE_PURE_COOL_LINK_DESK,
        DEVICE_TYPE_PURE_HOT_COOL,
        DEVICE_TYPE_PURE_HOT_COOL_LINK,
        DEVICE_TYPE_PURE_HUMIDIFY_COOL,
        DEVICE_TYPE_PURIFIER_BIG_QUIET,
    ]:
        _LOGGER.debug(
            "ProductType is already an internal device type code: %s", product_type
        )
        return product_type

    # If no mapping found, return None to indicate unknown device type
    _LOGGER.warning(
        "No mapping found for ProductType: %s, variant: %s. Available mappings: %s",
        product_type,
        variant,
        list(CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE.keys())[:10],
    )
    return None


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
    variant: Optional[str] = None  # Add variant field for better device type detection

    @classmethod
    def from_raw(cls, raw: dict):
        """Parse raw data."""
        import logging

        _LOGGER = logging.getLogger(__name__)

        # Get the product type - this might already include the variant
        product_type = raw.get("ProductType", "")

        # Check if we have a "type" field that might contain the full type+variant
        type_field = raw.get("type", "")

        # Handle variant field - use only lowercase "variant" per OpenAPI spec
        variant = raw.get("variant")
        version = raw.get("Version", "")

        _LOGGER.debug(
            "DysonDeviceInfo.from_raw: ProductType='%s', type='%s', variant='%s', Serial='%s'",
            product_type,
            type_field,
            variant,
            raw.get("Serial", ""),
        )

        # Log all available fields for debugging
        _LOGGER.debug("Raw device data fields: %s", list(raw.keys()))

        # If type field contains a known device type (like "358E"), use it as the product type
        if type_field and type_field in CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE:
            _LOGGER.debug("Using 'type' field as product_type: %s", type_field)
            product_type = type_field
            # Extract variant from type field if it ends with a letter
            if len(type_field) > 3 and type_field[-1] in ["E", "K", "M"]:
                variant = type_field[-1]
                _LOGGER.debug("Extracted variant '%s' from type field", variant)

        # Additional debugging for variant detection from firmware version
        if product_type in ["438", "527", "358"] and (
            variant is None or not variant.strip()
        ):
            _LOGGER.debug(
                "ProductType=%s with no variant - checking firmware version for variant info",
                product_type,
            )
            if version and len(version) >= 4:
                # Firmware format: {ProductType}{Variant}{ProductCategory}.{VersionInfo}
                # Examples:
                # - 438MPF.00.01.003.0011 where M=variant, PF=Purifier Fan
                # - 527KPF.01.02.003.0001 where K=variant, PF=Purifier Fan
                # - 358EPF.02.01.004.0005 where E=variant, PF=Purifier Fan
                firmware_prefix = version[:4]
                _LOGGER.debug(
                    "Firmware version: %s, prefix: %s", version, firmware_prefix
                )
                if (
                    firmware_prefix.startswith(product_type)
                    and len(firmware_prefix) == 4
                ):
                    potential_variant = firmware_prefix[3]
                    if potential_variant == "M":
                        _LOGGER.debug(
                            "Firmware indicates M variant - this is likely a %sM device",
                            product_type,
                        )
                        variant = "M"
                    elif potential_variant == "K":
                        _LOGGER.debug(
                            "Firmware indicates K variant - this is likely a %sK device",
                            product_type,
                        )
                        variant = "K"
                    elif potential_variant == "E":
                        _LOGGER.debug(
                            "Firmware indicates E variant - this is likely a %sE device",
                            product_type,
                        )
                        variant = "E"
                elif firmware_prefix == "ECG2":
                    if product_type == "358":  # PH series
                        variant = "E"
                        _LOGGER.debug(
                            "Detected E variant from ECG2 firmware prefix for PH series"
                        )

        return cls(
            raw["Active"] if "Active" in raw else None,
            raw["Serial"],
            raw["Name"],
            version,
            decrypt_password(raw["LocalCredentials"]),
            raw["AutoUpdate"],
            raw["NewVersionAvailable"],
            product_type,
            variant,
        )

    def get_device_type(self) -> Optional[str]:
        """Get the internal device type code from the cloud product type."""
        # If product_type already contains the variant (like "358E"), use it directly
        if self.product_type in CLOUD_PRODUCT_TYPE_TO_DEVICE_TYPE:
            import logging

            _LOGGER = logging.getLogger(__name__)
            _LOGGER.debug(
                "Product type '%s' is already a complete type, using directly",
                self.product_type,
            )
            return map_product_type_to_device_type(
                self.product_type, self.serial, None, self.name
            )

        # For devices with variants (438, 527, 358), try to extract variant from firmware version if not provided
        variant_to_use = self.variant

        if (
            self.product_type in ["438", "527", "358"]
            and (variant_to_use is None or not variant_to_use.strip())
            and self.version
            and len(self.version) >= 4
        ):

            # Extract variant from firmware version
            # Format: {ProductType}{Variant}{ProductCategory}.{VersionInfo}
            # Examples:
            # - 438MPF.00.01.003.0011 -> "M" (Pure Cool M variant)
            # - 527KPF.01.02.003.0001 -> "K" (Pure Hot+Cool K variant)
            # - 358EPF.02.01.004.0005 -> "E" (Pure Humidify+Cool E variant)
            firmware_prefix = self.version[:4]
            if (
                firmware_prefix.startswith(self.product_type)
                and len(firmware_prefix) == 4
            ):
                potential_variant = firmware_prefix[3]  # Extract the 4th character
                if potential_variant in ["M", "K", "E"]:
                    variant_to_use = potential_variant
                    import logging

                    _LOGGER = logging.getLogger(__name__)
                    _LOGGER.debug(
                        "Extracted variant '%s' from firmware version: %s (ProductType: %s)",
                        potential_variant,
                        self.version,
                        self.product_type,
                    )
            elif firmware_prefix == "ECG2" and self.product_type == "358":
                variant_to_use = "E"
                import logging

                _LOGGER = logging.getLogger(__name__)
                _LOGGER.debug(
                    "Detected E variant from ECG2 firmware prefix for PH series"
                )

        return map_product_type_to_device_type(
            self.product_type, self.serial, variant_to_use, self.name
        )
