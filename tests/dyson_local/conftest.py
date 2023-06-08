"""Configure Dyson Local tests."""

from unittest.mock import patch

from .vendor.libdyson import DysonDevice
import pytest

from custom_components.dyson_local import DOMAIN
from custom_components.dyson_local.const import (
    CONF_CREDENTIAL,
    CONF_DEVICE_TYPE,
    CONF_SERIAL,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from . import CREDENTIAL, HOST, MODULE, NAME, SERIAL

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
async def setup_entry(hass: HomeAssistant, device: DysonDevice):
    """Set up mocked config entry."""
    with patch(f"{MODULE}.get_device", return_value=device):
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_SERIAL: SERIAL,
                CONF_CREDENTIAL: CREDENTIAL,
                CONF_HOST: HOST,
                CONF_DEVICE_TYPE: device.device_type,
                CONF_NAME: NAME,
            },
        )
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
