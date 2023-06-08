"""Dyson 360 Eye cloud client."""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

import attr

from .cloud_device import DysonCloudDevice


class CleaningType(Enum):
    """Cleaning type of the task."""

    Immediate = "Immediate"
    Manual = "Manual"
    Scheduled = "Scheduled"


@attr.s(auto_attribs=True, frozen=True)
class CleaningTask:
    """Represent a cleaning task."""

    cleaning_id: str
    start_time: datetime  # Local time without timezone info
    finish_time: datetime  # Local time without timezone info
    area: float  # In square meters
    charges: int
    cleaning_type: str
    is_interim: bool

    @classmethod
    def from_raw(cls, raw: dict):
        """Parse raw data from cloud API."""
        return cls(
            raw["Clean"],
            datetime.fromisoformat(raw["Started"]),
            datetime.fromisoformat(raw["Finished"]),
            raw["Area"],
            raw["Charges"],
            CleaningType(raw["Type"]),
            raw["IsInterim"],
        )

    @property
    def cleaning_time(self) -> timedelta:
        """Return the total cleaning time."""
        return self.finish_time - self.start_time


class DysonCloud360Eye(DysonCloudDevice):
    """Dyson 360 Eye cloud client."""

    def get_cleaning_history(self) -> List[CleaningTask]:
        """Get cleaning history from the cloud."""
        response = self._account.request(
            "GET",
            f"/v1/assets/devices/{self._serial}/cleanhistory",
        )
        return [CleaningTask.from_raw(raw) for raw in response.json()["Entries"]]

    def get_cleaning_map(self, cleaning_id: str) -> Optional[bytes]:
        """Get cleaning map in PNG format."""
        response = self._account.request(
            "GET",
            f"/v1/mapvisualizer/devices/{self._serial}/map/{cleaning_id}",
        )
        if response.status_code == 404:
            return None  # No map associate with the cleaning id
        return response.content
