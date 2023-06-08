"""Dyson device cloud client."""


from . import DysonAccount


class DysonCloudDevice:
    """Dyson device cloud client."""

    def __init__(self, account: DysonAccount, serial: str):
        """Initialize the client."""
        self._account = account
        self._serial = serial
