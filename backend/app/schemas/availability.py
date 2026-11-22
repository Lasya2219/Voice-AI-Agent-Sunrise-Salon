
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


AvailabilityReason = Literal[
    "business_closed",
    "stylist_not_working",
    "fully_booked",
    "past_date",
]


class AvailableSlot(BaseModel):
    stylist_id: int
    stylist_name: str
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware.")
        return value


class AvailabilityResponse(BaseModel):
    service_id: int
    requested_date: date
    available_slots: list[AvailableSlot]
    reason: AvailabilityReason | None = None
    next_available_date: date | None = None
    next_available_slots: list[AvailableSlot] = Field(
        default_factory=list
    )
