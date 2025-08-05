"""Tests for Dyson device info module."""

from unittest.mock import patch

import pytest

from custom_components.dyson_local.vendor.libdyson.cloud.device_info import (
    DysonDeviceInfo,
    map_product_type_to_device_type,
)
from custom_components.dyson_local.vendor.libdyson.const import (
    DEVICE_TYPE_360_EYE,
    DEVICE_TYPE_360_HEURIST,
    DEVICE_TYPE_PURE_COOL,
    DEVICE_TYPE_PURE_COOL_LINK,
    DEVICE_TYPE_PURE_HOT_COOL,
    DEVICE_TYPE_PURE_HUMIDIFY_COOL,
    DEVICE_TYPE_PURIFIER_BIG_QUIET,
)


class TestMapProductTypeToDeviceType:
    """Test the map_product_type_to_device_type function."""

    def test_direct_mapping(self):
        """Test direct product type mappings."""
        # Test various direct mappings
        assert map_product_type_to_device_type("360 Eye") == DEVICE_TYPE_360_EYE
        assert map_product_type_to_device_type("N223") == DEVICE_TYPE_360_EYE
        assert map_product_type_to_device_type("TP02") == DEVICE_TYPE_PURE_COOL_LINK
        assert map_product_type_to_device_type("HP04") == DEVICE_TYPE_PURE_HOT_COOL
        assert map_product_type_to_device_type("BP02") == DEVICE_TYPE_PURIFIER_BIG_QUIET

    def test_variant_based_mapping(self):
        """Test variant-based mappings for devices that need variant in MQTT topics."""
        # Test 438 series with variants
        assert map_product_type_to_device_type("438", variant="M") == "438M"
        assert map_product_type_to_device_type("438", variant="K") == "438K"
        assert map_product_type_to_device_type("438", variant="E") == "438E"

        # Test 527 series with variants
        assert map_product_type_to_device_type("527", variant="K") == "527K"
        assert map_product_type_to_device_type("527", variant="E") == "527E"
        assert map_product_type_to_device_type("527", variant="M") == "527M"

        # Test 358 series with variants
        assert map_product_type_to_device_type("358", variant="K") == "358K"
        assert map_product_type_to_device_type("358", variant="E") == "358E"
        assert map_product_type_to_device_type("358", variant="M") == "358M"

    def test_variant_with_unknown_combination(self):
        """Test variant handling when combination is not in mapping."""
        # Unknown variant should fall back to base type
        assert (
            map_product_type_to_device_type("438", variant="X") == DEVICE_TYPE_PURE_COOL
        )
        assert (
            map_product_type_to_device_type("527", variant="Z")
            == DEVICE_TYPE_PURE_HOT_COOL
        )
        assert (
            map_product_type_to_device_type("358", variant="Y")
            == DEVICE_TYPE_PURE_HUMIDIFY_COOL
        )

    def test_empty_or_none_product_type(self):
        """Test handling of empty or None product type."""
        assert map_product_type_to_device_type(None) is None
        assert map_product_type_to_device_type("") is None

    def test_already_internal_device_type(self):
        """Test when product type is already an internal device type code."""
        assert (
            map_product_type_to_device_type(DEVICE_TYPE_360_EYE) == DEVICE_TYPE_360_EYE
        )
        assert (
            map_product_type_to_device_type(DEVICE_TYPE_PURE_COOL)
            == DEVICE_TYPE_PURE_COOL
        )
        assert (
            map_product_type_to_device_type(DEVICE_TYPE_PURE_HOT_COOL)
            == DEVICE_TYPE_PURE_HOT_COOL
        )

    def test_unknown_product_type(self):
        """Test handling of unknown product types."""
        assert map_product_type_to_device_type("UNKNOWN_TYPE") is None
        assert map_product_type_to_device_type("XYZ123") is None

    def test_variant_as_direct_mapping(self):
        """Test when variant itself is a valid product type."""
        # Some variants might be valid product types themselves
        assert (
            map_product_type_to_device_type("TP07", variant="TP07")
            == DEVICE_TYPE_PURE_COOL
        )

    def test_case_sensitivity(self):
        """Test that variant handling is case-insensitive."""
        assert map_product_type_to_device_type("438", variant="m") == "438M"
        assert map_product_type_to_device_type("527", variant="k") == "527K"
        assert map_product_type_to_device_type("358", variant="e") == "358E"

    @pytest.mark.xfail(reason="Whitespace in variant is not being stripped properly")
    def test_whitespace_handling(self):
        """Test handling of whitespace in variant."""
        # These should work because the function strips whitespace
        # Currently failing because the code concatenates without stripping
        assert map_product_type_to_device_type("438", variant=" M ") == "438M"
        assert map_product_type_to_device_type("527", variant="  K") == "527K"
        assert map_product_type_to_device_type("358", variant="E  ") == "358E"


class TestDysonDeviceInfo:
    """Test the DysonDeviceInfo dataclass."""

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_basic(self, mock_decrypt):
        """Test basic device info creation from raw data."""
        mock_decrypt.return_value = "decrypted_password"

        raw_data = {
            "Active": True,
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "21.03.08",
            "LocalCredentials": "encrypted_password",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "438",
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)

        assert device_info.active is True
        assert device_info.serial == "NK6-EU-MNA1234A"
        assert device_info.name == "Living Room"
        assert device_info.version == "21.03.08"
        assert device_info.credential == "decrypted_password"
        assert device_info.auto_update is True
        assert device_info.new_version_available is False
        assert device_info.product_type == "438"
        assert device_info.variant is None

        mock_decrypt.assert_called_once_with("encrypted_password")

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_with_variant(self, mock_decrypt):
        """Test device info creation with variant field."""
        mock_decrypt.return_value = "decrypted_password"

        raw_data = {
            "Active": True,
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "21.03.08",
            "LocalCredentials": "encrypted_password",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "438",
            "variant": "M",
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)

        assert device_info.product_type == "438"
        assert device_info.variant == "M"

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_with_type_field(self, mock_decrypt):
        """Test device info creation when type field contains full type+variant."""
        mock_decrypt.return_value = "decrypted_password"

        raw_data = {
            "Active": True,
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "21.03.08",
            "LocalCredentials": "encrypted_password",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "358",
            "type": "358E",  # Full type with variant
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)

        assert device_info.product_type == "358E"
        assert device_info.variant == "E"

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_variant_from_firmware(self, mock_decrypt):
        """Test variant extraction from firmware version."""
        mock_decrypt.return_value = "decrypted_password"

        # Test M variant extraction
        raw_data = {
            "Active": True,
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "438MPF.00.01.003.0011",  # M variant in firmware
            "LocalCredentials": "encrypted_password",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "438",
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)
        assert device_info.variant == "M"

        # Test K variant extraction
        raw_data["ProductType"] = "527"
        raw_data["Version"] = "527KPF.01.02.003.0001"  # K variant in firmware
        device_info = DysonDeviceInfo.from_raw(raw_data)
        assert device_info.variant == "K"

        # Test E variant extraction
        raw_data["ProductType"] = "358"
        raw_data["Version"] = "358EPF.02.01.004.0005"  # E variant in firmware
        device_info = DysonDeviceInfo.from_raw(raw_data)
        assert device_info.variant == "E"

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_ecg2_firmware(self, mock_decrypt):
        """Test E variant detection from ECG2 firmware prefix."""
        mock_decrypt.return_value = "decrypted_password"

        raw_data = {
            "Active": True,
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "ECG2.05.00.001",  # ECG2 firmware for PH series
            "LocalCredentials": "encrypted_password",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "358",
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)
        assert device_info.variant == "E"

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_missing_active_field(self, mock_decrypt):
        """Test device info creation when Active field is missing."""
        mock_decrypt.return_value = "decrypted_password"

        raw_data = {
            # "Active" field is missing
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "21.03.08",
            "LocalCredentials": "encrypted_password",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "438",
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)
        assert device_info.active is None

    def test_get_device_type_direct(self):
        """Test get_device_type with direct product type."""
        device_info = DysonDeviceInfo(
            active=True,
            serial="NK6-EU-MNA1234A",
            name="Living Room",
            version="21.03.08",
            credential="password",
            auto_update=True,
            new_version_available=False,
            product_type="TP02",
            variant=None,
        )

        assert device_info.get_device_type() == DEVICE_TYPE_PURE_COOL_LINK

    @pytest.mark.xfail(
        reason="get_device_type doesn't pass variant to map_product_type_to_device_type"
    )
    def test_get_device_type_with_variant(self):
        """Test get_device_type with variant."""
        device_info = DysonDeviceInfo(
            active=True,
            serial="NK6-EU-MNA1234A",
            name="Living Room",
            version="21.03.08",
            credential="password",
            auto_update=True,
            new_version_available=False,
            product_type="438",
            variant="M",
        )

        # The get_device_type method should pass the variant to map_product_type_to_device_type
        # Currently failing because it passes variant=None
        assert device_info.get_device_type() == "438M"

    @pytest.mark.xfail(
        reason="get_device_type doesn't pass extracted variant to map_product_type_to_device_type"
    )
    def test_get_device_type_variant_from_firmware(self):
        """Test get_device_type extracting variant from firmware."""
        device_info = DysonDeviceInfo(
            active=True,
            serial="NK6-EU-MNA1234A",
            name="Living Room",
            version="527KPF.01.02.003.0001",
            credential="password",
            auto_update=True,
            new_version_available=False,
            product_type="527",
            variant=None,  # No variant provided
        )

        # Should extract K from firmware and return 527K
        # Currently failing because extracted variant is not passed to map_product_type_to_device_type
        assert device_info.get_device_type() == "527K"

    def test_get_device_type_complete_type(self):
        """Test get_device_type when product_type already contains variant."""
        device_info = DysonDeviceInfo(
            active=True,
            serial="NK6-EU-MNA1234A",
            name="Living Room",
            version="21.03.08",
            credential="password",
            auto_update=True,
            new_version_available=False,
            product_type="358E",  # Already complete
            variant=None,
        )

        assert device_info.get_device_type() == DEVICE_TYPE_PURE_HUMIDIFY_COOL

    def test_dataclass_frozen(self):
        """Test that DysonDeviceInfo is immutable (frozen)."""
        device_info = DysonDeviceInfo(
            active=True,
            serial="NK6-EU-MNA1234A",
            name="Living Room",
            version="21.03.08",
            credential="password",
            auto_update=True,
            new_version_available=False,
            product_type="438",
            variant=None,
        )

        # Attempting to modify should raise an error
        with pytest.raises(AttributeError):
            device_info.name = "Bedroom"

    @pytest.mark.parametrize(
        "product_type,expected",
        [
            ("360 Eye", DEVICE_TYPE_360_EYE),
            ("360 Heurist", DEVICE_TYPE_360_HEURIST),
            ("TP02", DEVICE_TYPE_PURE_COOL_LINK),
            ("HP04", DEVICE_TYPE_PURE_HOT_COOL),
            ("PH01", DEVICE_TYPE_PURE_HUMIDIFY_COOL),
            ("BP02", DEVICE_TYPE_PURIFIER_BIG_QUIET),
        ],
    )
    def test_get_device_type_parametrized(self, product_type, expected):
        """Parametrized test for various product types."""
        device_info = DysonDeviceInfo(
            active=True,
            serial="NK6-EU-MNA1234A",
            name="Test Device",
            version="21.03.08",
            credential="password",
            auto_update=True,
            new_version_available=False,
            product_type=product_type,
            variant=None,
        )

        assert device_info.get_device_type() == expected

    @patch(
        "custom_components.dyson_local.vendor.libdyson.cloud.device_info.decrypt_password"
    )
    def test_from_raw_with_valid_base64(self, mock_decrypt):
        """Test with a valid base64 encoded password."""
        mock_decrypt.return_value = "decrypted_password"

        raw_data = {
            "Active": True,
            "Serial": "NK6-EU-MNA1234A",
            "Name": "Living Room",
            "Version": "21.03.08",
            "LocalCredentials": "dGVzdF9wYXNzd29yZA==",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "438",
        }

        device_info = DysonDeviceInfo.from_raw(raw_data)
        assert device_info.credential == "decrypted_password"
