"""Utilities for Dyson Local."""

from typing import Any, Optional

from libdyson.const import ENVIRONMENTAL_FAIL, ENVIRONMENTAL_INIT, ENVIRONMENTAL_OFF

from homeassistant.const import STATE_OFF

STATE_INIT = "init"
STATE_FAIL = "fail"


class environmental_property(property):
    """Environmental status property."""

    def __get__(self, obj: Any, type: Optional[type] = ...) -> Any:
        """Get environmental property value."""
        value = super().__get__(obj, type)
        if value == ENVIRONMENTAL_OFF:
            return STATE_OFF
        elif value == ENVIRONMENTAL_INIT:
            return STATE_INIT
        elif value == ENVIRONMENTAL_FAIL:
            return STATE_FAIL
        return value
